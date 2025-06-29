from pathlib import Path

import yaml

from holunder.hugo.header import HugoHeader


def write_hugo_md_file(header: HugoHeader, markdown: str | bytes, path: Path) -> None:
    delimiter = b"---\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(delimiter)
        yaml.safe_dump(header.model_dump(), f, encoding="utf-8", default_flow_style=False)
        f.write(delimiter)
        if isinstance(markdown, str):
            f.write(markdown.encode("utf-8"))
        else:
            f.write(markdown)
