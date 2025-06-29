import json
from pathlib import Path

from pydantic import BaseModel, Field, FilePath, model_validator


class Config(BaseModel):
    service_account_key_path: FilePath | None = Field(
        description="Path to the Google Service Account JSON key file", default=""
    )
    service_account_key: str | None = Field(
        description="Content of the Google Service Account JSON key", default=""
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

    @model_validator(mode="after")
    def non_empty_service_account_key(self):  # better name needed ;)
        if not self.service_account_key and not self.service_account_key_path:
            raise ValueError("One of [service_account_key, service_account_key_path] is required.")
        return self

    @property
    def service_account_info(self) -> dict[str, str]:
        if self.service_account_key is not None:
            content_str = self.service_account_key
        else:
            with Path(self.service_account_key_path).open("r") as f:
                content_str = f.read()
        return json.loads(content_str)
