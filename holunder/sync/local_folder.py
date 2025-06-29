import json
import re
import subprocess
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from tqdm import tqdm

from holunder.gdrive.client import GDriveClient
from holunder.gdrive.models import FileNode
from holunder.logger import logger
from holunder.path_sanitizer import default_sanitize_path


def check_for_duplicates(
    docs: list[FileNode], path_sanitize_func: Callable = default_sanitize_path
) -> None:
    duplicate_checks = defaultdict(list)
    for doc in docs:
        key = (*doc.parents, doc.get_local_path(sanitize_func=path_sanitize_func))
        duplicate_checks[key].append(doc)
    duplicates = []
    for group in duplicate_checks.values():
        if len(group) > 1:
            duplicates.append(tuple(doc.id for doc in group))
    if duplicates:
        raise ValueError(
            f"Duplicate file paths for following Docs were found after path sanitizing: {duplicates}"
        )


def _download_gdocs(
    local_dir: Path,
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
    n_threads: int = 4,
) -> None:
    if not docs:
        docs = client.list_google_docs()
    pool = ThreadPoolExecutor(max_workers=n_threads)
    downloads: list[Future] = [pool.submit(lambda: client.get_doc_markdown(doc.id)) for doc in docs]

    for doc, download in tqdm(zip(docs, downloads)):
        local_path = local_dir / doc.get_local_path(sanitize_func=path_sanitize_func)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb") as f:
            markdown = download.result()
            markdown = _replace_gdoc_links(markdown, docs)
            f.write(markdown)


markdown_link_regex = re.compile(rb"\[[^]\[()]+]\(([^]\[()]+)\)")


def _replace_gdoc_links(
    markdown: bytes, all_docs: list[FileNode], path_sanitize_func: Callable = default_sanitize_path
) -> bytes:
    urls = markdown_link_regex.findall(markdown)
    for url in urls:
        for doc in all_docs:
            if re.search(f"/{doc.id}([/?].*)?$".encode(), url):
                markdown = markdown.replace(
                    url, str(doc.get_local_path(sanitize_func=path_sanitize_func)).encode()
                )
    return markdown


def _build_checksums_index(
    docs: list[FileNode],
    download_only_ids: set[str] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
) -> dict[str, tuple[Path, str]]:
    res = {}
    for doc in docs:
        if download_only_ids is not None and doc.id not in download_only_ids:
            continue
        path = doc.get_local_path(sanitize_func=path_sanitize_func)
        # Note: Google Drive does not compute checksums for Docs, Sheets etc.
        # For now, we use the last modification time as a 'checksum'. This logic might change later.
        res[doc.id] = (str(path), doc.modifiedTime)
    return res


def _get_index_path(local_dir: Path) -> Path:
    return Path(local_dir) / "checksums.json"


def _load_checksums_index(local_dir: Path) -> dict[str, str]:
    index_path = _get_index_path(local_dir)
    if not index_path.is_file():
        return {}
    with index_path.open("r") as f:
        content = json.load(f)
    return content


def sync_local_dir(
    local_dir: Path,
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    download_only_ids: set[str] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
) -> list[FileNode]:
    local_dir = Path(local_dir)
    new_index = _build_checksums_index(
        docs=docs, download_only_ids=download_only_ids, path_sanitize_func=path_sanitize_func
    )
    old_index = _load_checksums_index(local_dir)

    paths_to_delete = set(old_index.keys()).difference(path for path, _ in new_index.values())
    if paths_to_delete:
        logger.info(
            f"Deleting {len(paths_to_delete)} local Markdown files no longer present/approved in Google Drive: {paths_to_delete}"
        )
        for relative_path in paths_to_delete:
            path = local_dir / relative_path
            if path.is_file():
                path.unlink()

    doc_ids_to_update = {
        doc_id
        for doc_id, (path, checksum) in new_index.items()
        if old_index.get(path) != checksum or not (local_dir / path).is_file()
    }
    logger.info(
        f"Skipped {len(new_index) - len(doc_ids_to_update)} docs out of {len(new_index)} because local Markdown files are identical."
    )
    if not doc_ids_to_update:
        return []
    new_or_updated_docs = [doc for doc in docs if doc.id in doc_ids_to_update]
    with TemporaryDirectory() as temp_dir:
        _download_gdocs(
            local_dir=Path(temp_dir),
            client=client,
            docs=new_or_updated_docs,
            path_sanitize_func=path_sanitize_func,
        )
        cmd = ["rsync", "--recursive", "--checksum", "--include=*.md", "--include=*.checksum"]
        cmd.extend([temp_dir + "/", str(local_dir)])
        subprocess.run(cmd, check=True)
    with _get_index_path(local_dir).open("w") as f:
        json.dump({path: checksum for path, checksum in new_index.values()}, f, indent=2)
    return new_or_updated_docs
