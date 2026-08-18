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
    def __init__(self, subfolder: str | None = None, cookiefile: str | None = None):
        self.download_dir = create_download_directory(subfolder)
 
        # --------------------------------------------------
        # Optional cookies file (Netscape format) to reduce
        # 403s caused by YouTube requiring an authenticated
        # session for certain formats/clients.
        #
        # Export with a browser extension or:
        #   yt-dlp --cookies-from-browser chrome --cookies cookies.txt
        # --------------------------------------------------
        self.cookiefile = cookiefile
 
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
                "best[height<=1080]/b/best"
            ),
            "720p": (
                "bestvideo[height<=720]+bestaudio/"
                "best[height<=720]/b/best"
            ),
            "480p": (
                "bestvideo[height<=480]+bestaudio/"
                "best[height<=480]/b/best"
            ),
            "360p": (
                "bestvideo[height<=360]+bestaudio/"
                "best[height<=360]/b/best"
            ),
            "worst": "worst",
            "best": "bestvideo+bestaudio/b/best",
        }
 
        return resolution_map.get(
            resolution,
            "bestvideo+bestaudio/b/best"
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
 
    def _build_base_options(
        self,
        output_template: str,
        format_spec: str,
        format_type: str,
        audio_format: str,
        progress_hook,
    ) -> dict:
 
        options = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": format_spec,
            "merge_output_format": "mp4",
            "continuedl": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "check_formats": None,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr", "android", "mweb"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        }
 
        if FFMPEG_EXE:
            options["ffmpeg_location"] = FFMPEG_EXE
 
        if self.cookiefile and os.path.exists(self.cookiefile):
            options["cookiefile"] = self.cookiefile
 
        if format_type == "audio":
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192",
                }
            ]
 
        if progress_hook:
            options["progress_hooks"] = [progress_hook]
 
        return options


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
        # --------------------------------------------------
        options = self._build_base_options(
            output_template,
            format_spec,
            format_type,
            audio_format,
            progress_hook,
        )
 
        info = None
        filepath = None
 
        # --------------------------------------------------
        # Download
        # --------------------------------------------------
        try:
 
            print(f"Starting download: {url}")
            print(f"Format: {format_spec}")
            print(f"Resolution: {resolution}")
            print(f"Download directory: {self.download_dir}")
 
            if FFMPEG_EXE:
                print(f"FFmpeg: {FFMPEG_EXE}")
            else:
                print("FFmpeg: Not found")
 
            if self.cookiefile:
                print(f"Cookies file: {self.cookiefile}")
 
            with yt_dlp.YoutubeDL(options) as ydl:
 
                info = ydl.extract_info(
                    url,
                    download=True,
                )
 
                if not info:
                    raise RuntimeError(
                        "yt-dlp did not return video information."
                    )
 
                filepath = ydl.prepare_filename(info)
 
        except Exception as error:
 
            error_message = str(error)
 
            print("========================================")
            print("YT-DLP DOWNLOAD ERROR")
            print(error_message)
            print("========================================")
 
            is_bot_or_403 = any(
                term in error_message.lower()
                for term in ["403", "forbidden", "sign in", "bot", "format is not available"]
            )

            if is_bot_or_403:
                fallback_clients = ["android_vr", "android", "mweb", "ios"]

                fallback_format = (
                    "b/best" if format_type == "video" else "bestaudio/best"
                )
 
                success = False
                last_fallback_error = None
 
                for client in fallback_clients:
 
                    print(f"Attempting 403 recovery with player_client={client}...")
 
                    fallback_options = dict(options)
                    fallback_options["format"] = fallback_format
                    fallback_options["extractor_args"] = {
                        "youtube": {
                            "player_client": [client],
                            "player_skip": ["webpage", "configs"],
                        }
                    }

 
                    try:
                        with yt_dlp.YoutubeDL(fallback_options) as ydl:
                            info = ydl.extract_info(
                                url,
                                download=True,
                            )
 
                            if info:
                                filepath = ydl.prepare_filename(info)
                                success = True
                                print(f"Recovery succeeded with player_client={client}")
                                break
 
                    except Exception as fallback_err:
                        last_fallback_error = fallback_err
                        print(f"player_client={client} failed: {fallback_err}")
                        continue
 
                if not success:
                    raise RuntimeError(
                        "yt-dlp download failed after trying all 403 "
                        f"fallback clients ({', '.join(fallback_clients)}). "
                        f"Last error: {last_fallback_error}. "
                        "This often means: (1) yt-dlp is out of date - run "
                        "'pip install -U yt-dlp', (2) your server's IP is "
                        "datacenter/cloud-based and YouTube is blocking it - "
                        "consider a residential proxy, or (3) you need a "
                        "cookies file for authenticated access."
                    ) from (last_fallback_error or error)
 
            else:
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
 
            base_path, _ = os.path.splitext(filepath)
 
            final_audio_path = f"{base_path}.{audio_format}"
 
            if os.path.exists(final_audio_path):
 
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
                raise RuntimeError("Downloaded file is empty.")
 
            try:
                print(f"Download completed successfully: {filepath}")
            except Exception:
                print("Download completed successfully.")
            print(f"File size: {file_size / (1024 * 1024):.2f} MB")

 
        except OSError as error:
            raise RuntimeError(
                f"Could not verify downloaded file: {error}"
            ) from error
 
        return filepath
 