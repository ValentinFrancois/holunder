from io import StringIO
from pathlib import Path

import yaml
from yaml.loader import SafeLoader

from holunder.hugo.header import HugoHeader


def parse_hugo_md_file(path: Path) -> tuple[dict, str] | None:
    delimiter = "---"
    with path.open("r") as f:
        start: bool = False
        yaml_lines: list[str] = []
        markdown_content = ""
        for line in f:
            cleaned = line.rstrip()
            if cleaned:
                if not start:
                    if cleaned == delimiter:
                        start = True
                    else:
                        return None
                else:
                    if cleaned == delimiter:
                        markdown_content = f.read()
                        break
                    else:
                        yaml_lines.append(f"{cleaned}\n")
    if yaml_lines:
        with StringIO() as f:
            f.writelines(yaml_lines)
            f.seek(0)
            return yaml.load(f, SafeLoader), markdown_content
    else:
        return None


def list_hugo_md_files(
    folder: Path, only_auto_generated: bool = True
) -> dict[Path, tuple[HugoHeader, str]]:
    res = {}
    folder = Path(folder)
    paths = folder.rglob("*.md")
    for path in paths:
        parsed = parse_hugo_md_file(path)
        if parsed is not None:
            header_dict, markdown_content = parsed
            parsed_header = HugoHeader(**header_dict)
            if only_auto_generated and (
                parsed_header.params is None or not parsed_header.params.auto_generated
            ):
                continue
            else:
                res[path.relative_to(folder)] = (parsed_header, markdown_content)
    return res
