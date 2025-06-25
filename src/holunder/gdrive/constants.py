from enum import Enum


class GDriveMimeType(Enum):
    # https://developers.google.com/workspace/drive/api/guides/mime-types
    folder = 'application/vnd.google-apps.folder'
    doc = 'application/vnd.google-apps.document'
    sheet = 'application/vnd.google-apps.spreadsheet'
    markdown = 'text/markdown'

    def __eq__(self, other):
        try:
            as_enum = self.__class__(other)
        except Exception:
            return False
        return super().__eq__(as_enum)
