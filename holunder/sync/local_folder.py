import re
import sys
from collections import defaultdict
from collections.abc import Callable, Generator
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from holunder.gdrive.client import GDriveClient
from holunder.gdrive.models import FileNode
from holunder.hugo.header import create_header
from holunder.hugo.md_parser import list_hugo_md_files
from holunder.hugo.md_writer import write_hugo_md_file
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


def download_gdocs(
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    n_threads: int = 4,
) -> Generator[bytes, None, None]:
    if not docs:
        docs = client.list_google_docs()
    pool = ThreadPoolExecutor(max_workers=n_threads)
    downloads: list[Future] = [pool.submit(lambda: client.get_doc_markdown(doc.id)) for doc in docs]
    with tqdm(downloads, file=sys.stdout, desc="Downloading & converting Google Docs...") as it:
        for download in it:
            markdown = download.result()
            markdown = _replace_gdoc_links(markdown, docs)
            yield markdown


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


def sync_local_dir(
    local_dir: Path,
    client: GDriveClient,
    docs: list[FileNode] | None = None,
    approved_ids: set[str] | None = None,
    path_sanitize_func: Callable = default_sanitize_path,
) -> None:
    if approved_ids is None:
        approved_ids = set()
    local_dir = Path(local_dir)
    local_hugo_pages = list_hugo_md_files(local_dir) if local_dir.is_dir() else {}

    remote_hugo_pages = {
        doc.get_local_path(sanitize_func=path_sanitize_func): (
            doc,
            create_header(doc, approved=doc.id in approved_ids),
        )
        for doc in docs
    }

    marked_to_draft: set[Path] = set()
    marked_to_approved: set[Path] = set()
    created: set[Path] = set()
    content_updated: set[Path] = set()

    for path, (header, markdown) in local_hugo_pages.items():
        if path not in remote_hugo_pages and not header.draft:
            header.draft = True
            marked_to_draft.add(path)
            write_hugo_md_file(header, markdown, local_dir / path)

    for path, (doc, header) in remote_hugo_pages.items():
        if path not in local_hugo_pages:
            created.add(path)
        else:
            local_header, local_markdown = local_hugo_pages[path]
            if local_header.date != header.date:
                content_updated.add(path)
                local_header.date = header.date
            if local_header.draft != header.draft:
                local_header.draft = header.draft
                if header.draft:
                    marked_to_draft.add(path)
                else:
                    marked_to_approved.add(path)

    total_updates = marked_to_draft.union(marked_to_approved, created, content_updated)
    paths_to_download = list(created.union(content_updated))
    paths_to_update_header = total_updates.intersection(remote_hugo_pages.keys()).difference(
        paths_to_download
    )
    docs_to_download = [remote_hugo_pages[path][0] for path in paths_to_download]
    downloads = download_gdocs(client, docs_to_download)

    if docs_to_download:
        for path, downloaded_bytes in zip(paths_to_download, downloads):
            header = (
                local_hugo_pages[path][0] if path in content_updated else remote_hugo_pages[path][1]
            )
            write_hugo_md_file(header, downloaded_bytes, local_dir / path)
        next(downloads, "ignore")

    for path in paths_to_update_header:
        header, markdown = local_hugo_pages[path]
        write_hugo_md_file(header, markdown, local_dir / path)

    def paths_str(paths: set[Path]) -> list[str]:
        return sorted(str(p) for p in paths)

    logger.info(
        f"Total files updated: {len(total_updates)}\n"
        f"Marked to draft (not found remotely/not approved in the Spreadsheet): {len(marked_to_draft)}\n{paths_str(marked_to_draft)}\n"
        f"Marked to approved: {len(marked_to_approved)}\n{paths_str(marked_to_approved)}\n"
        f"Created: {len(created)}\n{paths_str(created)}\n"
        f"Markdown content updated: {len(content_updated)}\n{paths_str(content_updated)}"
    )
