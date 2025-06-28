import types

import click
from click import Command
from pydantic_core import PydanticUndefined

from holunder.config import Config
from holunder.gdrive.client import GDriveClient
from holunder.logger import logger
from holunder.sync.local_folder import check_for_duplicates, sync_local_dir
from holunder.sync.remote_sheet import sync_gsheet


def _get_client(config: Config) -> GDriveClient:
    try:
        return GDriveClient(config)
    except Exception:
        logger.exception("Service Account credentials seem incorrect")
        raise


@click.group()
def cli():
    pass


def add_config_params(func: Command) -> Command:
    """Programmatically add click options matching the fields of the Config pydantic model."""
    for field, field_info in Config.model_fields.items():
        if isinstance(field_info.annotation, types.UnionType):
            field_type = field_info.annotation.__args__[0]
        else:
            field_type = field_info.annotation
        if field_info.default is PydanticUndefined:
            default = None
            required = True
        else:
            default = field_info.default
            required = False
        func.params.append(
            click.Option(
                ["--" + field],
                type=field_type,
                default=default,
                show_default=True,
                required=required,
                help=field_info.description,
            )
        )
    return func


@add_config_params
@cli.command("check_config")
def check_config(**kwargs):
    try:
        config = Config(**kwargs)
    except Exception:
        logger.error("Invalid config")
        raise

    client = _get_client(config)

    root = client.get_root_folder()
    logger.info(f"Configured documents root folder: '{root.name}' ({root.id}).")

    if config.gdrive_management_spreadsheet:
        sheet = client.get_management_spreadsheet()
        logger.info(f"Configured management spreadsheet: '{sheet.name}' ({sheet.id}).")
    else:
        logger.info("No management spreadsheet configured.")


def sync_gdrive(config: Config) -> None:
    client = _get_client(config)
    docs = client.list_google_docs()
    check_for_duplicates(docs)
    if config.gdrive_management_spreadsheet:
        df = sync_gsheet(client, docs)
        approved_ids = set(df[df["approved"]]["id"])
        n_skipped = len(docs) - len(approved_ids)
        logger.info(f"Skipped {n_skipped} docs out of {len(docs)} because they are not approved.")
    else:
        approved_ids = {doc.id for doc in docs}
    sync_local_dir(
        local_dir=config.local_markdown_root_folder,
        client=client,
        docs=docs,
        download_only_ids=approved_ids,
    )


@add_config_params
@cli.command("sync_gdrive")
def cli_sync_gdrive(**kwargs):
    config = Config(**kwargs)
    sync_gdrive(config)


if __name__ == "__main__":
    cli()
