import os
from pathlib import Path
import yt_dlp


class VideoDownloader:

    DOWNLOAD_DIR = Path.home() / "Downloads"

    def __init__(self):

        os.makedirs(
            self.DOWNLOAD_DIR,
            exist_ok=True
        )

    def download(
        self,
        url: str,
        progress_hook=None,
    ):

        output_template = os.path.join(
            self.DOWNLOAD_DIR,
            "%(title)s.%(ext)s"
        )

        options = {

            "outtmpl": output_template,

            "quiet": True,

            "noplaylist": True,

            "js_runtimes": {
                "node": {}
            },

            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android",
                        "web_creator"
                    ]
                }
            },
        }

        # Add progress hook if provided
        if progress_hook:

            options["progress_hooks"] = [
                progress_hook
            ]

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True,
            )

            filepath = ydl.prepare_filename(
                info
            )

            return filepath