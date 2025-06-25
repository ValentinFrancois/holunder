from pathlib import Path

from pydantic import BaseModel, Field
from typing_extensions import Self
from yaml import CSafeLoader, load


class Config(BaseModel):
    service_account_key_path: Path = Field(description='Path to Google Service Account Key file')
    gdrive_root_folder_id: str = Field(
        description='ID of the root folder containing all the GDoc files'
    )
    gdrive_management_sheet_id: str | None = Field(
        description='ID of the GSheet to use for pages approval'
    )
    ignore_images: bool = Field(
        description='Remove images from the GDoc -> markdown conversion output', default=True
    )
    delete_non_synced_pages: bool = Field(
        description='If a local markdown page is no longer found in the GDrive root folder, delete it.',
        default=False,
    )

    @classmethod
    def from_yaml(cls, path: Path | str) -> Self:
        with Path(path).open('r') as f:
            parsed = load(f, CSafeLoader)
            config = cls(**parsed)
        if not config.service_account_key_path.is_file():
            error = FileNotFoundError(config.service_account_key_path)
            if config.service_account_key_path.is_absolute():
                raise error
            else:
                relative = path.parent / config.service_account_key_path
                if relative.is_file():
                    config.service_account_key_path = relative
                else:
                    raise error
        return config
