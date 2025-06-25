from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from holunder.gdrive.constants import GDriveMimeType


class BaseFileInfo(BaseModel):
    id: str
    name: str


class FileGetResponse(BaseFileInfo):
    mimeType: GDriveMimeType | str


class FileNode(BaseFileInfo):
    parents: tuple[str, ...] | None = (
        None  # Convention: parents[0] = root parent, parents[-1] = direct parent
    )

    def get_local_path(self, sanitize_func: Callable) -> Path:
        local_path = Path('')
        if self.parents:
            for parent_name in self.parents:
                local_path = local_path / sanitize_func(parent_name)
        local_path = local_path / (sanitize_func(self.name) + '.md')
        return local_path


SyncedDocs = list[tuple[FileNode, Path]]
