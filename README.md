![Holunder logo](logo.png) 

`v0.1.0`

Easy content management framework for [Hugo](https://github.com/gohugoio/hugo) based on Google Drive.

---

# Concept

This tool aims to ease content management for websites created with Hugo.

It offers a pragmatic solution for groups/organizations with little means who typically have 1-2 technical persons maintaing the website and far more people writing the content of the website.

These people are usually not familiar with git or Markdown. They won't have a GitHub account.
But, they are quite likely to have a Google account and to be familiar with writing Google Docs.

So that's our solution: let the content writers work with Google Docs, and provide an automatic tool that convert these docs into Markdown pages ready to be published with Hugo.

# Advantages

- No additional permission management than what you're probably already doing in Google Drive: anyone who is allowed to write/edit pages for the website gets write access to a folder of your choice.
- Anyone can write content on a familiar interface (Google Docs).
- The formatting to Markdown is done automatically, so you don't waste your developer time.
- A simple approval pipeline allows the writers to block the publishing of a page until its content is finalized.

# Installation

## 1. Install __holunder__ with pip

```shell
pip install git+https://github.com/ValentinFrancois/holunder.git
```

### Requirements
- `python >= 3.10`
- packages:
  - `google-auth`
  - `google-api-python-client`
  - `pydantic`
  - `Unidecode`
  - `tqdm`
  - `pandas`
  - `click`
  - `PyYAML`

## 2. Set up the project Google Drive
- Create a root folder where all the pages for the website will be written. Share it with your contributors and store its ID (from the URL).
- [Create a Google Service Account](https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts/create?walkthrough_id=iam--create-service-account) and share the previously created folder to the account as __Viewer__.
- [Create a JSON key file](https://cloud.google.com/iam/docs/keys-create-delete) for your Service Account and download it.
- Optional: create a Google Spreadsheet and store its ID (it will be used for page content approval tracking). Share the spreadsheet to the Service Account as __Editor__.

That's it! You can now configure __holunder__ to use the above resources for automatic download & conversion of Google Docs to a local directory.

__NOTE__: Be careful with the service account and its key. Only store it in places that are meant for secets (e.g. GitHub repo secrets).

## 3. Test your config
After 1. you should now be able to call `holunder` from the terminal.
```shell
$ holunder check_config --help
Usage: holunder check_config [OPTIONS]

Options:
  --service_account_key_path PATH
                                  Path to Google Service Account Key file
                                  [required]
  --gdrive_root_folder_id TEXT    ID of the root folder containing all the
                                  GDoc files  [required]
  --gdrive_management_spreadsheet TEXT
                                  ID of the GSheet to use for pages approval
                                  [default: ""]
  --ignore_images BOOLEAN         Remove images from the GDoc -> markdown
                                  conversion output  [default: True]
  --local_markdown_root_folder PATH
                                  Local folder where GDocs will be downloaded
                                  as markdown files.  [default: synced]
```
