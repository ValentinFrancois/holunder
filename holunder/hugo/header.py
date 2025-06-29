from pydantic import BaseModel, ConfigDict
from typing_extensions import Self

from holunder.gdrive.models import FileNode


class HugoHeader(BaseModel):
    model_config = ConfigDict(extra="allow")

    class Params(BaseModel):
        model_config = ConfigDict(extra="allow")
        auto_generated: bool = False

    date: str
    title: str
    draft: bool = True
    params: Params | None = None

    def merge(self, other: Self) -> Self:
        self.__dict__.update(other.__dict__)
        return self


def create_header(doc: FileNode, approved: bool) -> HugoHeader:
    return HugoHeader(
        date=doc.modifiedTime,
        title=doc.name,
        draft=not approved,
        params=HugoHeader.Params(auto_generated=True),
    )
