from pathlib import Path


DOWNLOAD_DIRECTORY = Path("downloads")


def create_download_directory():

    DOWNLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    return DOWNLOAD_DIRECTORY