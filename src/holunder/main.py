from pathlib import Path

from holunder.config import Config
from holunder.gdrive.client import GDriveClient
from holunder.logger import logger
from holunder.sync.local_folder import sync_local_dir


def check_config(config_path: Path | str) -> None:
    try:
        config = Config.from_yaml(config_path)
    except Exception:
        logger.exception(f'Config file {config_path} could not be found/loaded')

    try:
        client = GDriveClient(config)
    except Exception:
        logger.exception('Service Account credentials seem incorrect')

    root = client.get_root_folder()
    logger.info(f"Configured documents root folder: '{root.name}' ({root.id}).")

    sheet = client.get_management_spreadsheet()
    logger.info(f"Configured management spreadsheet: '{sheet.name}' ({sheet.id}).")

    sync_local_dir('synced', client)


if __name__ == '__main__':
    check_config(Path(__file__).parent.parent.parent / 'local' / 'config.yaml')
