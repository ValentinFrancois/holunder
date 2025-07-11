from typing import Any

import pandas as pd

from holunder.gdrive.client import GDriveClient
from holunder.gdrive.models import FileNode


def download_spreadsheet_as_df(client: GDriveClient) -> pd.DataFrame | None:
    rows = client.download_spreadsheet(file_id=client._config.gdrive_management_spreadsheet)
    if not rows or len(rows) < 2:
        return None
    n_columns = max(len(row) for row in rows)
    columns = rows[0]
    if len(columns) < n_columns:
        for i in range(n_columns - len(columns)):
            columns.append(f"unknown_{i}")
    rows = rows[1:]
    for row in rows:
        if len(row) < n_columns:
            for _ in range(n_columns - len(row)):
                row.append("")
    return pd.DataFrame(data=rows, columns=columns)


def update_spreadsheet_from_df(client: GDriveClient, df: pd.DataFrame) -> None:
    df = df.fillna("")

    def clean(value: Any) -> Any:
        if isinstance(value, str | int | float | bool):
            return value
        else:
            return str(value)

    df = df.map(clean)

    values = df.T.reset_index().T.values.tolist()
    client.update_spreadsheet(file_id=client._config.gdrive_management_spreadsheet, values=values)


def sync_gsheet(client: GDriveClient, docs: list[FileNode]) -> pd.DataFrame:
    url_prefix = "https://docs.google.com/document/d/"
    rows = [
        {
            "url": f"{url_prefix}{doc.id}",
            "folder": "" if not doc.parents else "/".join(doc.parents),
            "title": doc.name,
            "approved": False,
            "reviewers": "",
        }
        for doc in docs
    ]
    df = pd.DataFrame(rows)

    current_df = download_spreadsheet_as_df(client)
    if current_df is None:
        consolidated_df = df
    else:
        intersection = set(df.url).intersection(current_df.url)
        consolidated_df = pd.concat(
            [df[~df.url.isin(intersection)], current_df[current_df.url.isin(intersection)]]
        )

    consolidated_df = consolidated_df.sort_values(by=["approved", "folder", "title"])
    consolidated_df["approved"] = consolidated_df["approved"].apply(
        lambda x: str(x).lower() == "true"
    )

    upload_df = consolidated_df.copy()
    if len(upload_df) < len(current_df):
        # Add empty rows to overwrite the rows of the remote Spreadsheet
        empty_rows = pd.DataFrame(
            data=[
                ["" for _ in range(len(upload_df.columns.values))]
                for _ in range(len(current_df) - len(upload_df))
            ],
            columns=list(upload_df.columns.values),
        )
        upload_df = pd.concat([upload_df, empty_rows])

    update_spreadsheet_from_df(client, upload_df)
    consolidated_df["id"] = consolidated_df["url"].apply(lambda url: url.replace(url_prefix, ""))
    return consolidated_df
