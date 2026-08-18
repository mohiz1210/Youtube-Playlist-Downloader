import os
from pathlib import Path

import yt_dlp

try:
    import imageio_ffmpeg

    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

from app.utils.filehandler import create_download_directory


class VideoDownloader:
    def __init__(self, subfolder: str | None = None):
        self.download_dir = create_download_directory(subfolder)

    def _get_format_spec(
        self,
        format_type: str,
        resolution: str
    ) -> str:

        if format_type == "audio":
            return "bestaudio/best"

        resolution_map = {
            "1080p": (
                "bestvideo[height<=1080]+bestaudio/"
                "best[height<=1080]/best"
            ),
            "720p": (
                "bestvideo[height<=720]+bestaudio/"
                "best[height<=720]/best"
            ),
            "480p": (
                "bestvideo[height<=480]+bestaudio/"
                "best[height<=480]/best"
            ),
            "360p": (
                "bestvideo[height<=360]+bestaudio/"
                "best[height<=360]/best"
            ),
            "worst": "worst",
            "best": "bestvideo+bestaudio/best",
        }

        return resolution_map.get(
            resolution,
            "bestvideo+bestaudio/best"
        )

    def _find_downloaded_file(
        self,
        info,
        expected_path: str
    ) -> str | None:

        # --------------------------------------------------
        # 1. Check expected yt-dlp filename
        # --------------------------------------------------
        if os.path.exists(expected_path):
            return expected_path

        # --------------------------------------------------
        # 2. Check requested_downloads
        # --------------------------------------------------
        requested_downloads = info.get("requested_downloads", [])

        for requested in requested_downloads:
            filepath = requested.get("filepath")

            if filepath and os.path.exists(filepath):
                return filepath

        # --------------------------------------------------
        # 3. Check common extensions
        # --------------------------------------------------
        base_path, _ = os.path.splitext(expected_path)

        extensions = [
            ".mp4",
            ".mkv",
            ".webm",
            ".mp3",
            ".m4a",
            ".wav",
            ".flac",
            ".aac",
            ".3gp",
            ".mov",
        ]

        for extension in extensions:
            candidate = f"{base_path}{extension}"

            if os.path.exists(candidate):
                return candidate

        # --------------------------------------------------
        # 4. Search download directory
        # --------------------------------------------------
        try:
            all_files = [
                file
                for file in self.download_dir.glob("*")
                if (
                    file.is_file()
                    and not file.name.endswith(".part")
                    and not file.name.endswith(".ytdl")
                )
            ]

            if all_files:
                latest_file = max(
                    all_files,
                    key=lambda file: file.stat().st_mtime
                )

                return str(latest_file)

        except Exception:
            pass

        return None

    def download(
        self,
        url: str,
        progress_hook=None,
        format_type: str = "video",
        resolution: str = "best",
        audio_format: str = "mp3",
    ):

        if not url:
            raise ValueError("Video URL cannot be empty.")

        # --------------------------------------------------
        # Output filename
        # --------------------------------------------------
        output_template = os.path.join(
            str(self.download_dir),
            "%(title)s.%(ext)s"
        )

        # --------------------------------------------------
        # Format
        # --------------------------------------------------
        format_spec = self._get_format_spec(
            format_type,
            resolution
        )

        # --------------------------------------------------
        # yt-dlp options
        #
        # IMPORTANT:
        # We intentionally do NOT force:
        #
        # "player_client": ["android"]
        #
        # because this can cause YouTube 403 errors when
        # deployed on cloud/datacenter environments.
        # --------------------------------------------------
        options = {
            "outtmpl": output_template,

            # Set False temporarily so deployment logs
            # show useful yt-dlp information.
            "quiet": False,

            "no_warnings": False,

            "noplaylist": True,

            "format": format_spec,

            # Needed when video and audio are downloaded
            # separately.
            "merge_output_format": "mp4",

            # Avoid leaving partial files if download fails.
            "continuedl": True,

            # Don't download an entire playlist accidentally.
            "playlistend": 1,
        }

        # --------------------------------------------------
        # FFmpeg
        # --------------------------------------------------
        if FFMPEG_EXE:
            options["ffmpeg_location"] = FFMPEG_EXE

        # --------------------------------------------------
        # Audio conversion
        # --------------------------------------------------
        if format_type == "audio":

            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                }
            ]

        # --------------------------------------------------
        # Progress callback
        # --------------------------------------------------
        if progress_hook:
            options["progress_hooks"] = [
                progress_hook
            ]

        # --------------------------------------------------
        # Download
        # --------------------------------------------------
        try:

            print(
                f"Starting download: {url}"
            )

            print(
                f"Format: {format_spec}"
            )

            print(
                f"Resolution: {resolution}"
            )

            print(
                f"Download directory: "
                f"{self.download_dir}"
            )

            if FFMPEG_EXE:
                print(
                    f"FFmpeg: {FFMPEG_EXE}"
                )
            else:
                print(
                    "FFmpeg: Not found"
                )

            with yt_dlp.YoutubeDL(options) as ydl:

                info = ydl.extract_info(
                    url,
                    download=True,
                )

                if not info:
                    raise RuntimeError(
                        "yt-dlp did not return video information."
                    )

                # --------------------------------------------------
                # Get expected filename
                # --------------------------------------------------
                filepath = ydl.prepare_filename(info)

        except Exception as error:

            error_message = str(error)

            print(
                "========================================"
            )

            print(
                "YT-DLP DOWNLOAD ERROR"
            )

            print(
                error_message
            )

            print(
                "========================================"
            )

            if (
                "403" in error_message
                or "Forbidden" in error_message
            ):
                raise RuntimeError(
                    "YouTube returned HTTP 403 Forbidden. "
                    "The deployed server was not allowed to "
                    "download this media. "
                    "This can be caused by YouTube's current "
                    "client/PO-token requirements or by the "
                    "cloud server's IP environment. "
                    f"Original error: {error_message}"
                ) from error

            raise RuntimeError(
                f"yt-dlp download failed: {error_message}"
            ) from error

        # --------------------------------------------------
        # Find actual downloaded file
        # --------------------------------------------------
        filepath = self._find_downloaded_file(
            info,
            filepath
        )

        if not filepath:
            raise RuntimeError(
                "Download completed according to yt-dlp, "
                "but the downloaded file could not be found."
            )

        # --------------------------------------------------
        # Audio output
        # --------------------------------------------------
        if format_type == "audio":

            base_path, _ = os.path.splitext(
                filepath
            )

            final_audio_path = (
                f"{base_path}.{audio_format}"
            )

            # FFmpeg postprocessor may have generated
            # the final audio file.
            if os.path.exists(final_audio_path):

                # Remove the original temporary file
                # if it is different from final audio.
                if (
                    os.path.exists(filepath)
                    and filepath != final_audio_path
                ):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

                filepath = final_audio_path

        # --------------------------------------------------
        # Final validation
        # --------------------------------------------------
        if not os.path.exists(filepath):

            raise RuntimeError(
                "Video download failed. "
                "The output file was not created."
            )

        # --------------------------------------------------
        # Check file size
        # --------------------------------------------------
        try:

            file_size = os.path.getsize(filepath)

            if file_size <= 0:
                raise RuntimeError(
                    "Downloaded file is empty."
                )

            print(
                f"Download completed successfully: "
                f"{filepath}"
            )

            print(
                f"File size: {file_size / (1024 * 1024):.2f} MB"
            )

        except OSError as error:

            raise RuntimeError(
                f"Could not verify downloaded file: {error}"
            ) from error

        return filepath