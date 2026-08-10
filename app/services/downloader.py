from pathlib import Path

import yt_dlp

from app.core.exceptions import DownloadError


class VideoDownloader:

    def __init__(self):

        # self.download_path = Path("downloads")
        self.download_path = Path.home() / "Downloads"

        self.download_path.mkdir(
            parents=True,
            exist_ok=True
        )

    def download(self, url: str):

        options = {
            "format": "best",
            "outtmpl": str(
                self.download_path / "%(title)s.%(ext)s"
            ),
            "js_runtimes": {"node": {}},
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web_creator"]
                }
            },
        }

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                information = ydl.extract_info(
                    url,
                    download=True
                )

                filename = ydl.prepare_filename(
                    information
                )

                return filename

        except Exception as error:

            raise DownloadError(str(error))