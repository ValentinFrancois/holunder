import os.path

from google.auth.transport.requests import Request

# from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    """creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=8080, redirect_uri_trailing_slash=False)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())"""

    creds = Credentials.from_service_account_file("test-463923-a6e703d15939.json", scopes=SCOPES)

    try:
        service = build("drive", "v3", credentials=creds)

        # Call the Drive v3 API
        results = (
            service.files().list(pageSize=10, fields="nextPageToken, files(id, name)").execute()
        )
        items = results.get("files", [])

        if not items:
            print("No files found.")
        else:
            print("Files:")
            for item in items:
                print(f"{item['name']} ({item['id']})")

        bytes = (
            service.files()
            .export(
                fileId="1tFPNhcznfLb6Xm1JOrl9RI8kdpDdr26pocxdNINS8xw", mimeType="text/markdown"
            )
            .execute()
        )
        with open("test.md", "wb") as f:
            f.write(bytes)
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        print(f"An error occurred: {error}")

    req = Request()
    url = (
        "https://docs.google.com/document/u/0/export?format=md&id="
        + "1tFPNhcznfLb6Xm1JOrl9RI8kdpDdr26pocxdNINS8xw"
        + "&token="
        + creds.token
    )
    resp = req(
        method="GET",
        url=url,
        headers={
            "Referer": "https://docs.google.com/document/d/1tFPNhcznfLb6Xm1JOrl9RI8kdpDdr26pocxdNINS8xw/edit?tab=t.0"
        },
    )  # , headers={"Authorization": "Bearer " + creds.token})
    with open("response.html", "wb") as f:
        f.write(resp.data)


if __name__ == "__main__":
    main()
