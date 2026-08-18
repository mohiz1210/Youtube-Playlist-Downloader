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
        proxy: str | None = None,
    ):
        self.download_dir = create_download_directory(subfolder)
        self.cookiefile = cookiefile
        # Optional proxy, e.g. "http://user:pass@host:port".
        # Can also be supplied via env var so you don't have to
        # hardcode credentials anywhere.
        self.proxy = proxy or os.environ.get("YTDLP_PROXY")
 
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
            "1080p": (
                "bestvideo*[height<=1080]+bestaudio/"
                "b[height<=1080]/b/best/worst"
            ),
            "720p": (
                "bestvideo*[height<=720]+bestaudio/"
                "b[height<=720]/b/best/worst"
            ),
            "480p": (
                "bestvideo*[height<=480]+bestaudio/"
                "b[height<=480]/b/best/worst"
            ),
            "360p": (
                "bestvideo*[height<=360]+bestaudio/"
                "b[height<=360]/b/best/worst"
            ),
            "best": "b/best/bestvideo*+bestaudio/worst",
            "worst": "worst",
        }
 
        return resolution_map.get(
            resolution,
            "b/best/bestvideo*+bestaudio/worst",
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
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": format_spec,
            "merge_output_format": "mp4",
            "continuedl": True,
            "force_ipv4": True,
            "retries": 3,
            "fragment_retries": 3,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "check_formats": None,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "android_vr"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        }

 
        if FFMPEG_EXE:
            options["ffmpeg_location"] = FFMPEG_EXE
 
        if self.cookiefile and os.path.exists(self.cookiefile):
            options["cookiefile"] = self.cookiefile
 
        if self.proxy:
            options["proxy"] = self.proxy
 
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
 
    # ---------------------------------------------------------
    # FIND OUTPUT FILE
    # ---------------------------------------------------------
 
    def _find_downloaded_file(
        self,
        info,
        expected_path: str | None,
    ) -> str | None:
 
        if expected_path and os.path.exists(expected_path):
            return expected_path
 
        if info:
            for item in info.get("requested_downloads", []):
                filepath = item.get("filepath")
                if filepath and os.path.exists(filepath):
                    return filepath
 
        if expected_path:
            base_path, _ = os.path.splitext(expected_path)
            extensions = [
                ".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".wav", ".flac", ".aac", ".3gp", ".mov"
            ]
            for extension in extensions:
                candidate = f"{base_path}{extension}"
                if os.path.exists(candidate):
                    return candidate
 
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
                latest = max(files, key=lambda file: file.stat().st_mtime)
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
            raise ValueError("Video URL cannot be empty.")
 
        output_template = os.path.join(
            str(self.download_dir),
            "%(title)s.%(ext)s",
        )
 
        format_spec = self._get_format_spec(
            format_type,
            resolution,
        )
 
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
 
        if self.proxy:
            print("Proxy: enabled")
 
        print("=" * 60)
 
        info = None
        expected_path = None
 
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    url,
                    download=True,
                )
                if not info:
                    raise RuntimeError("yt-dlp returned no video information.")
 
                expected_path = ydl.prepare_filename(info)
 
        except Exception as error:
            error_message = str(error)
 
            print("=" * 60)
            print("YT-DLP PRIMARY DOWNLOAD ERROR")
            print(error_message)
            print("=" * 60)
 
            # Fallback client recovery sequence.
            # Ordered by which clients currently tend to avoid
            # PO-token / 403 issues most often — this changes as
            # YouTube adjusts its anti-bot rules, so revisit periodically.
            fallback_clients = ["android", "android_vr", "mweb", "ios", "tv_embedded"]
            fallback_formats = (
                ["b/best/worst", "18/22/b/best"]
                if format_type == "video"
                else ["bestaudio/best/worst"]
            )
 
            success = False
            last_fallback_err = None
 
            for client in fallback_clients:
                for fmt in fallback_formats:
                    print(
                        f"Attempting recovery with player_client={client}, format={fmt}..."
                    )
                    fallback_options = dict(options)
                    fallback_options["format"] = fmt
                    fallback_options["extractor_args"] = {
                        "youtube": {
                            "player_client": [client],
                            "player_skip": ["webpage", "configs"],
                        }
                    }
                    try:
                        with yt_dlp.YoutubeDL(fallback_options) as ydl:
                            info = ydl.extract_info(url, download=True)
                            if info:
                                expected_path = ydl.prepare_filename(info)
                                success = True
                                print(
                                    f"Recovery succeeded with player_client={client}, format={fmt}"
                                )
                                break
                    except Exception as fb_err:
                        last_fallback_err = fb_err
                        print(
                            f"Recovery with player_client={client}, format={fmt} failed: {fb_err}"
                        )
                        continue
                if success:
                    break
 
            if not success:
                hint = (
                    " This looks like it may be a datacenter/cloud IP block "
                    "rather than a config issue — if you're running on "
                    "Streamlit Cloud or similar, consider routing through "
                    "a residential proxy (set YTDLP_PROXY or pass proxy=...)."
                )
                raise RuntimeError(
                    f"yt-dlp download failed: {error_message} "
                    f"(Fallback error: {last_fallback_err}){hint}"
                ) from (last_fallback_err or error)
 
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
        try:
            print(f"File: {filepath}")
        except Exception:
            print("File downloaded successfully.")
        print(
            f"Size: {size / (1024 * 1024):.2f} MB"
        )
        print("=" * 60)
 
        return filepath
 