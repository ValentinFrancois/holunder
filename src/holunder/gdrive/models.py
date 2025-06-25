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
