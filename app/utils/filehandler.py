import re
from pathlib import Path

DOWNLOAD_DIRECTORY = Path.home() / "Downloads"


def sanitize_folder_name(name: str) -> str:
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", name).strip(". ")
    return sanitized if sanitized else "Playlist"


def create_download_directory(subfolder: str | None = None) -> Path:
    if subfolder:
        clean_subfolder = sanitize_folder_name(subfolder)
        target_dir = DOWNLOAD_DIRECTORY / clean_subfolder
    else:
        target_dir = DOWNLOAD_DIRECTORY

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir
