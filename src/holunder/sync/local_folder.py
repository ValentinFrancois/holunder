import re
import subprocess
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from tqdm import tqdm

from holunder.gdrive.client import GDriveClient
from holunder.gdrive.models import FileNode
from holunder.path_sanitizer import default_sanitize_path


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

    doc_ids_to_paths = {}
    for doc in docs:
        local_path = Path('')
        if doc.parents:
            for parent_name in doc.parents:
                local_path = local_path / path_sanitize_func(parent_name)
        local_path = local_path / (path_sanitize_func(doc.name) + '.md')
        doc_ids_to_paths[doc.id] = local_path

    for doc, download in tqdm(zip(docs, downloads)):
        local_path = local_dir / doc_ids_to_paths[doc.id]
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open('wb') as f:
            markdown = download.result()
            markdown = _replace_gdoc_links(markdown, doc_ids_to_paths)
            f.write(markdown)


markdown_link_regex = re.compile(rb'\[[^]\[()]+]\(([^]\[()]+)\)')


def _replace_gdoc_links(markdown: bytes, doc_ids_to_paths: dict[str, Path]) -> bytes:
    urls = markdown_link_regex.findall(markdown)
    for url in urls:
        for doc_id, path in doc_ids_to_paths.items():
            if re.search(f'/{doc_id}([/?].*)?$'.encode(), url):
                markdown = markdown.replace(url, str(path).encode())
    return markdown


def sync_local_dir(
    local_dir: Path,
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
) -> None:
    with TemporaryDirectory() as temp_dir:
        _download_gdocs(
            local_dir=temp_dir, client=client, docs=docs, path_sanitize_func=path_sanitize_func
        )
        cmd = ['rsync', '--recursive', '--checksum', '--include=*.md']
        if client._config.delete_non_synced_pages:
            cmd.append('--delete')
        cmd.extend([temp_dir + '/', str(local_dir)])
        subprocess.run(cmd, check=True)
