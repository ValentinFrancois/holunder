from pathlib import Path

from pydantic import BaseModel, Field, FilePath


class Config(BaseModel):
    service_account_key_path: FilePath = Field(
        description="Path to Google Service Account Key file"
    )
    gdrive_root_folder_id: str = Field(
        description="ID of the root folder containing all the GDoc files"
    )
    gdrive_management_spreadsheet: str | None = Field(
        description="ID of the GSheet to use for pages approval", default=""
    )
    ignore_images: bool = Field(
        description="Remove images from the GDoc -> markdown conversion output", default=True
    )
    local_markdown_root_folder: Path = Field(
        description="Local folder where GDocs will be downloaded as markdown files.",
        default=Path("./synced/"),
    )
