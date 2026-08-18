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

    def __init__(
        self,
        subfolder: str | None = None,
        cookiefile: str | None = None,
    ):
        self.download_dir = create_download_directory(subfolder)
        self.cookiefile = cookiefile

    # ---------------------------------------------------------
    # FORMAT SELECTION
    # ---------------------------------------------------------

    def _get_format_spec(
        self,
        format_type: str,
        resolution: str,
    ) -> str:

        # Audio
        if format_type == "audio":
            return "bestaudio/best"

        # Video
        resolution_map = {
            "1080p": "bestvideo*[height<=1080]+bestaudio/best",
            "720p": "bestvideo*[height<=720]+bestaudio/best",
            "480p": "bestvideo*[height<=480]+bestaudio/best",
            "360p": "bestvideo*[height<=360]+bestaudio/best",

            # Let yt-dlp choose a reasonable format
            "best": "bestvideo*+bestaudio/best",

            # Avoid "worst" because it is often not what users
            # actually want and can produce poor results.
            "worst": "worstvideo*+worstaudio/worst",
        }

        return resolution_map.get(
            resolution,
            "bestvideo*+bestaudio/best",
        )

    # ---------------------------------------------------------
    # BUILD OPTIONS
    # ---------------------------------------------------------

    def _build_options(
        self,
        output_template: str,
        format_spec: str,
        format_type: str,
        audio_format: str,
        progress_hook=None,
    ) -> dict:

        options = {
            "outtmpl": output_template,

            # Keep logs visible while diagnosing deployment.
            "quiet": False,
            "no_warnings": False,

            "noplaylist": True,

            "format": format_spec,

            # Needed when separate video/audio streams
            # need to be merged.
            "merge_output_format": "mp4",

            # Continue partial downloads.
            "continuedl": True,

            # Force IPv4 as an additional diagnostic.
            "force_ipv4": True,

            # Retry network failures.
            "retries": 3,
            "fragment_retries": 3,

            # Do NOT force Android, iOS, mweb, TV, etc.
            #
            # yt-dlp should choose its current supported
            # configuration.
        }

        # -----------------------------------------------------
        # FFmpeg
        # -----------------------------------------------------

        if FFMPEG_EXE:
            options["ffmpeg_location"] = FFMPEG_EXE

        # -----------------------------------------------------
        # Cookies
        # -----------------------------------------------------

        if self.cookiefile:

            if os.path.exists(self.cookiefile):
                options["cookiefile"] = self.cookiefile

        # -----------------------------------------------------
        # Audio conversion
        # -----------------------------------------------------

        if format_type == "audio":

            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                }
            ]

        # -----------------------------------------------------
        # Progress hook
        # -----------------------------------------------------

        if progress_hook:
            options["progress_hooks"] = [
                progress_hook
            ]

        return options

    # ---------------------------------------------------------
    # FIND OUTPUT FILE
    # ---------------------------------------------------------

    def _find_downloaded_file(
        self,
        info,
        expected_path: str | None,
    ) -> str | None:

        # -----------------------------------------------------
        # 1. Expected path
        # -----------------------------------------------------

        if expected_path:

            if os.path.exists(expected_path):
                return expected_path

        # -----------------------------------------------------
        # 2. requested_downloads
        # -----------------------------------------------------

        if info:

            for item in info.get(
                "requested_downloads",
                [],
            ):

                filepath = item.get("filepath")

                if filepath and os.path.exists(filepath):
                    return filepath

        # -----------------------------------------------------
        # 3. Check common extensions
        # -----------------------------------------------------

        if expected_path:

            base_path, _ = os.path.splitext(
                expected_path
            )

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

                candidate = (
                    f"{base_path}{extension}"
                )

                if os.path.exists(candidate):
                    return candidate

        # -----------------------------------------------------
        # 4. Search download directory
        # -----------------------------------------------------

        try:

            files = [
                file
                for file in self.download_dir.glob("*")
                if (
                    file.is_file()
                    and not file.name.endswith(".part")
                    and not file.name.endswith(".ytdl")
                )
            ]

            if files:

                latest = max(
                    files,
                    key=lambda file: file.stat().st_mtime,
                )

                return str(latest)

        except Exception:
            pass

        return None

    # ---------------------------------------------------------
    # MAIN DOWNLOAD
    # ---------------------------------------------------------

    def download(
        self,
        url: str,
        progress_hook=None,
        format_type: str = "video",
        resolution: str = "best",
        audio_format: str = "mp3",
    ):

        if not url:
            raise ValueError(
                "Video URL cannot be empty."
            )

        # -----------------------------------------------------
        # Output
        # -----------------------------------------------------

        output_template = os.path.join(
            str(self.download_dir),
            "%(title)s.%(ext)s",
        )

        # -----------------------------------------------------
        # Format
        # -----------------------------------------------------

        format_spec = self._get_format_spec(
            format_type,
            resolution,
        )

        # -----------------------------------------------------
        # Options
        # -----------------------------------------------------

        options = self._build_options(
            output_template=output_template,
            format_spec=format_spec,
            format_type=format_type,
            audio_format=audio_format,
            progress_hook=progress_hook,
        )

        print("=" * 60)
        print("YT-DLP DOWNLOAD")
        print("=" * 60)
        print(f"URL: {url}")
        print(f"Format: {format_spec}")
        print(f"Resolution: {resolution}")
        print(f"Directory: {self.download_dir}")

        if FFMPEG_EXE:
            print(f"FFmpeg: {FFMPEG_EXE}")
        else:
            print("FFmpeg: NOT FOUND")

        if self.cookiefile:
            print(f"Cookies: {self.cookiefile}")

        print("=" * 60)

        info = None
        expected_path = None

        # -----------------------------------------------------
        # Download
        # -----------------------------------------------------

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                info = ydl.extract_info(
                    url,
                    download=True,
                )

                if not info:
                    raise RuntimeError(
                        "yt-dlp returned no video information."
                    )

                expected_path = ydl.prepare_filename(
                    info
                )

        except Exception as error:

            error_message = str(error)

            print("=" * 60)
            print("YT-DLP ERROR")
            print(error_message)
            print("=" * 60)

            # -----------------------------------------------
            # FORMAT ERROR
            # -----------------------------------------------

            if (
                "requested format is not available"
                in error_message.lower()
            ):

                raise RuntimeError(
                    "The requested video format is not "
                    "available for this YouTube video/client. "
                    "Try resolution='best'. "
                    f"yt-dlp error: {error_message}"
                ) from error

            # -----------------------------------------------
            # 403 ERROR
            # -----------------------------------------------

            if (
                "403" in error_message
                or "forbidden" in error_message.lower()
            ):

                raise RuntimeError(
                    "YouTube returned HTTP 403 Forbidden. "
                    "The request was rejected by YouTube. "
                    "This is not an FFmpeg error. "
                    "Your Streamlit Cloud environment may "
                    "require a current YouTube PO-token/client "
                    "configuration or may be affected by "
                    "YouTube's cloud/datacenter restrictions. "
                    f"Original error: {error_message}"
                ) from error

            # -----------------------------------------------
            # SIGN-IN / BOT
            # -----------------------------------------------

            if (
                "sign in" in error_message.lower()
                or "bot" in error_message.lower()
            ):

                raise RuntimeError(
                    "YouTube requires additional verification "
                    "for this request. "
                    f"Original error: {error_message}"
                ) from error

            # -----------------------------------------------
            # EVERYTHING ELSE
            # -----------------------------------------------

            raise RuntimeError(
                f"yt-dlp download failed: "
                f"{error_message}"
            ) from error

        # -----------------------------------------------------
        # Find final file
        # -----------------------------------------------------

        filepath = self._find_downloaded_file(
            info,
            expected_path,
        )

        if not filepath:

            raise RuntimeError(
                "yt-dlp reported success, but the downloaded "
                "file could not be located."
            )

        # -----------------------------------------------------
        # Audio
        # -----------------------------------------------------

        if format_type == "audio":

            base_path, _ = os.path.splitext(
                filepath
            )

            final_audio_path = (
                f"{base_path}.{audio_format}"
            )

            if os.path.exists(final_audio_path):

                if (
                    filepath != final_audio_path
                    and os.path.exists(filepath)
                ):

                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

                filepath = final_audio_path

        # -----------------------------------------------------
        # Final validation
        # -----------------------------------------------------

        if not os.path.exists(filepath):

            raise RuntimeError(
                "Download failed because the output "
                "file does not exist."
            )

        try:

            size = os.path.getsize(filepath)

            if size <= 0:

                raise RuntimeError(
                    "Downloaded file is empty."
                )

        except OSError as error:

            raise RuntimeError(
                f"Could not inspect downloaded file: {error}"
            ) from error

        print("=" * 60)
        print("DOWNLOAD SUCCESS")
        print(f"File: {filepath}")
        print(
            f"Size: {size / (1024 * 1024):.2f} MB"
        )
        print("=" * 60)

        return filepath