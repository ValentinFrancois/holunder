from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build

from holunder.config import Config
from holunder.gdrive.constants import GDriveMimeType
from holunder.gdrive.models import FileGetResponse, FileNode


class GDriveClient:
    SCOPES = [
        "https://www.googleapis.com/auth/drive.metadata.readonly",  # list files
        "https://www.googleapis.com/auth/drive.readonly",  # read file content
        "https://www.googleapis.com/auth/spreadsheets",  # read and write spreadsheets
    ]

    def __init__(self, config: Config):
        self._config = config
        self._creds = self.read_credentials()

    def read_credentials(self) -> Credentials:
        return Credentials.from_service_account_info(
            self._config.service_account_info, scopes=self.SCOPES
        )

    def build_drive_service(self) -> Resource:
        return build(serviceName="drive", version="v3", credentials=self._creds)

    def build_spreadsheet_service(self) -> Resource:
        return build(serviceName="sheets", version="v4", credentials=self._creds)

    def list_files_all_pages(
        self, page_size: int, q: str, page_token: str | None = None
    ) -> list[FileGetResponse]:
        with self.build_drive_service() as service:
            kwargs = dict(
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                q=q,
            )
            if page_token is not None:
                kwargs["pageToken"] = page_token
            response = service.files().list(**kwargs).execute()
        files = []
        for file in response["files"]:
            files.append(FileGetResponse(**file))
        if next_page_token := response.get("nextPageToken"):
            files.append(
                self.list_files_all_pages(page_size=page_size, q=q, page_token=next_page_token)
            )
        return files

    def list_google_docs(
        self, page_size: int = 100, folder_id: str | None = None, parents: tuple[str] = tuple()
    ) -> list[FileNode]:
        if folder_id is None:
            folder_id = self._config.gdrive_root_folder_id
        q = (
            f"(mimeType = '{GDriveMimeType.doc.value}'"
            f" or mimeType = '{GDriveMimeType.folder.value}')"
            f" and '{folder_id}' in parents"  # "in parents" actually means "is direct parent"
            f" and trashed=false"
        )
        docs: list[FileNode] = []
        docs_and_folders = self.list_files_all_pages(page_size=page_size, q=q)
        for file in docs_and_folders:
            if file.mimeType == GDriveMimeType.folder:
                docs.extend(
                    self.list_google_docs(
                        page_size=page_size, folder_id=file.id, parents=(*parents, file.name)
                    )
                )
            else:
                file = FileNode(
                    id=file.id, name=file.name, modifiedTime=file.modifiedTime, parents=parents
                )
                docs.append(file)
        return docs

    def get_file_info(self, file_id: str) -> FileGetResponse:
        with self.build_drive_service() as service:
            response = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
            return FileGetResponse(**response)

    def get_root_folder(self) -> FileGetResponse:
        file_id = self._config.gdrive_root_folder_id
        root = self.get_file_info(file_id)
        if root.mimeType != GDriveMimeType.folder:
            raise ValueError(
                f"Unexpected MIME type for configured root folder ({file_id}): {root.mimeType}"
            )
        return root

    def get_management_spreadsheet(self) -> FileGetResponse:
        file_id = self._config.gdrive_management_spreadsheet
        sheet = self.get_file_info(file_id)
        if sheet.mimeType != GDriveMimeType.sheet:
            raise ValueError(
                f"Unexpected MIME type for configured root folder ({file_id}): {sheet.mimeType}"
            )
        return sheet

    def get_doc_markdown(self, file_id: str) -> bytes:
        with self.build_drive_service() as service:
            bytes = (
                service.files()
                .export(fileId=file_id, mimeType=GDriveMimeType.markdown.value)
                .execute()
            )
        if self._config.ignore_images:
            return bytes
        raise NotImplementedError()

    def download_spreadsheet(self, file_id: str, sheet: str | None = None) -> list[list]:
        cells_range = "!A1:ZZ900000"
        cells_range = (sheet + cells_range) if sheet is not None else cells_range
        with self.build_spreadsheet_service() as service:
            return (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=file_id, range=cells_range)
                .execute()["values"]
            )

    def update_spreadsheet(
        self, file_id: str, values: list[list], sheet: str | None = None
    ) -> None:
        cells_range = "!A1:ZZ900000"
        cells_range = (sheet + cells_range) if sheet is not None else cells_range
        with self.build_spreadsheet_service() as service:
            service.spreadsheets().values().update(
                spreadsheetId=file_id,
                # See https://developers.google.com/workspace/sheets/api/reference/rest/v4/ValueInputOption
                valueInputOption="USER_ENTERED",
                range=cells_range,
                body=dict(majorDimension="ROWS", values=values),
            ).execute()
