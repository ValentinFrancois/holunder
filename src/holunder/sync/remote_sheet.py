import pandas as pd

from holunder.gdrive.client import GDriveClient
from holunder.gdrive.models import FileNode


def sync_gsheet(client: GDriveClient, docs: list[FileNode]) -> pd.DataFrame:
    sheet_client = client.get_gsheet_pandas_client()

    rows = [
        {
            'url': f'https://docs.google.com/document/d/{doc.id}',
            'folder': '' if not doc.parents else '/'.join(doc.parents),
            'title': doc.name,
            'approved': False,
            'reviewers': '',
        }
        for doc in docs
    ]
    df = pd.DataFrame(rows)

    try:
        current_df = sheet_client.download(
            spreadsheet_id=client._config.gdrive_management_spreadsheet.id,
            sheet_name=client._config.gdrive_management_spreadsheet.sheet,
        )
    except Exception as e:
        if str(e) == 'Empty data':
            current_df = None
        else:
            raise

    if current_df is None:
        consolidated_df = df

    else:
        consolidated_df = pd.concat([current_df, df]).drop_duplicates(keep='first', subset=['url'])
    consolidated_df = consolidated_df.sort_values(by=['approved', 'folder', 'title'])

    sheet_client.upload(
        consolidated_df,
        spreadsheet_id=client._config.gdrive_management_spreadsheet.id,
        sheet_name=client._config.gdrive_management_spreadsheet.sheet,
    )
