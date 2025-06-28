import re
import subprocess
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from tqdm import tqdm

from holunder.gdrive.client import GDriveClient
from holunder.gdrive.models import FileNode, SyncedDocs
from holunder.logger import logger
from holunder.path_sanitizer import default_sanitize_path


def _download_gdocs(
    local_dir: Path,
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
    n_threads: int = 4,
) -> list[FileNode]:
    if not docs:
        docs = client.list_google_docs()

    pool = ThreadPoolExecutor(max_workers=n_threads)
    downloads: list[Future] = [pool.submit(lambda: client.get_doc_markdown(doc.id)) for doc in docs]

    docs_and_paths: SyncedDocs = [
        (doc, doc.get_local_path(sanitize_func=path_sanitize_func)) for doc in docs
    ]

    for (doc, relative_path), download in tqdm(zip(docs_and_paths, downloads)):
        local_path = local_dir / relative_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb") as f:
            markdown = download.result()
            markdown = _replace_gdoc_links(markdown, docs_and_paths)
            f.write(markdown)
        local_checksum_path = _checksum_path(local_path)
        with local_checksum_path.open("w") as f:
            # Note: Google Drive does not compute checksums for Docs, Sheets etc.
            # For now, we use the last modification time as a 'checksum'. This logic might change later.
            f.write(doc.modifiedTime)

    return docs


def _checksum_path(markdown_path: Path) -> Path:
    return markdown_path.parent / (markdown_path.stem + ".checksum")


def _filter_identical_checksums(
    local_dir: Path,
    docs: list[FileNode],
    path_sanitize_func: Callable = default_sanitize_path,
) -> list[FileNode]:
    filtered = []
    for doc in docs:
        local_markdown_path = local_dir / doc.get_local_path(sanitize_func=path_sanitize_func)
        if local_markdown_path.is_file():
            checksum_path = _checksum_path(local_markdown_path)
            if checksum_path.is_file():
                with checksum_path.open("r") as f:
                    # Note: Google Drive does not compute checksums for Docs, Sheets etc.
                    # For now, we use the last modification time as a 'checksum'. This logic might change later.
                    checksum = f.read()
                    if checksum == doc.modifiedTime:
                        continue
        filtered.append(doc)
    n_skipped = len(docs) - len(filtered)
    logger.info(
        f"Skipped {n_skipped} docs out of {len(docs)} because they were identical to the local version."
    )
    return filtered


markdown_link_regex = re.compile(rb"\[[^]\[()]+]\(([^]\[()]+)\)")


def _replace_gdoc_links(markdown: bytes, downloaded_docs: SyncedDocs) -> bytes:
    urls = markdown_link_regex.findall(markdown)
    for url in urls:
        for doc, path in downloaded_docs:
            if re.search(f"/{doc.id}([/?].*)?$".encode(), url):
                markdown = markdown.replace(url, str(path).encode())
    return markdown


def sync_local_dir(
    local_dir: Path,
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
) -> list[FileNode]:
    new_or_updated_docs = _filter_identical_checksums(
        local_dir=local_dir, docs=docs, path_sanitize_func=path_sanitize_func
    )
    if not new_or_updated_docs:
        return []
    with TemporaryDirectory() as temp_dir:
        _download_gdocs(
            local_dir=temp_dir,
            client=client,
            docs=new_or_updated_docs,
            path_sanitize_func=path_sanitize_func,
        )
        cmd = ["rsync", "--recursive", "--checksum", "--include=*.md", "--include=*.checksum"]
        cmd.extend([temp_dir + "/", str(local_dir)])
        subprocess.run(cmd, check=True)
    return new_or_updated_docs
