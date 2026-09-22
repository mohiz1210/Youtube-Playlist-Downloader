import os
import urllib.request
from pathlib import Path
 
import yt_dlp
 
try:
    import imageio_ffmpeg

    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

# Browser TLS/HTTP2 impersonation (yt-dlp's --impersonate). Makes requests
# look like real Chrome at the network level instead of a bare Python
# client, which lowers the odds of YouTube's bot-check firing — with no
# cookies, account, or proxy required. Needs the curl_cffi package
# (installed via the "curl-cffi" extra in requirements.txt); if it isn't
# present, or no impersonate target ends up available, we skip it and
# behave as before. YoutubeDL requires an actual ImpersonateTarget object
# here, not a plain string — a raw string passes yt-dlp's own type check
# but fails its target-availability check with a bare AssertionError.
try:
    import curl_cffi  # noqa: F401
    from yt_dlp.networking.impersonate import ImpersonateTarget

    IMPERSONATE_TARGET = ImpersonateTarget.from_str("chrome")
except Exception:
    IMPERSONATE_TARGET = None

from app.utils.filehandler import create_download_directory


import tempfile

def get_default_cookiefile() -> str | None:
    """Find YouTube cookies from .env (file or text) or project directory."""
    # 1. Direct file path from .env / environment
    cookie_env = os.environ.get("YTDLP_COOKIES_FILE")
    if cookie_env:
        resolved_path = Path(cookie_env)
        if not resolved_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent.parent
            resolved_path = project_root / cookie_env
        if resolved_path.is_file() and resolved_path.stat().st_size > 0:
            return str(resolved_path)

    # 2. Raw cookie text in .env / environment (ideal for cloud/container deployments)
    cookie_text = os.environ.get("YTDLP_COOKIES_TEXT")
    if cookie_text and cookie_text.strip():
        # Clean escaped newlines if coming from quoted env string
        cleaned_text = cookie_text.encode("utf-8").decode("unicode_escape").strip()
        temp_cookie_path = Path(tempfile.gettempdir()) / "ytdlp_env_cookies.txt"
        temp_cookie_path.write_text(cleaned_text, encoding="utf-8")
        return str(temp_cookie_path)

    # 3. Project directory fallback
    project_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        project_root / "cookies.txt",
        project_root / "app" / "services" / "www.youtube.com_cookies (1).txt",
        project_root / "www.youtube.com_cookies (1).txt",
    ]
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return str(candidate)
    return None



class VideoDownloader:

    def __init__(
        self,
        subfolder: str | None = None,
        proxy: str | None = None,
        cookiefile: str | None = None,
    ):
        self.download_dir = create_download_directory(subfolder)
        self.proxy = proxy or os.environ.get("YTDLP_PROXY")
        self.cookiefile = cookiefile or get_default_cookiefile()



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
                    "player_client": ["android", "ios", "web", "mweb"],
                }
            },
        }


 
        if FFMPEG_EXE:
            options["ffmpeg_location"] = FFMPEG_EXE

        if IMPERSONATE_TARGET:
            options["impersonate"] = IMPERSONATE_TARGET

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
 
    def _download_direct_stream(self, url: str) -> tuple[bool, str | None]:
        """
        Ultimate fallback: extract media URL with download=False and stream byte chunks directly via urllib.
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "b/best",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        }
        if IMPERSONATE_TARGET:
            opts["impersonate"] = IMPERSONATE_TARGET
        if self.cookiefile and os.path.exists(self.cookiefile):
            opts["cookiefile"] = self.cookiefile

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return False, None
                expected = ydl.prepare_filename(info)
                media_url = info.get("url")
                if not media_url:
                    for fmt in reversed(info.get("formats", [])):
                        if fmt.get("url") and fmt.get("vcodec") != "none":
                            media_url = fmt.get("url")
                            break
                if not media_url:
                    return False, None

                print(f"Direct urllib stream extraction downloading...")
                req = urllib.request.Request(
                    media_url,
                    headers={
                        "User-Agent": (
                            "com.google.android.youtube/19.29.37 (Linux; U; Android 11)"
                        ),
                        "Accept": "*/*",
                    },
                )
                with urllib.request.urlopen(req, timeout=60) as resp, open(expected, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)

                if os.path.exists(expected) and os.path.getsize(expected) > 0:
                    print("Direct urllib stream extraction succeeded!")
                    return True, expected
        except Exception as exc:
            print(f"Direct stream recovery extraction failed: {exc}")

        return False, None

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

        return self._download(
            url,
            progress_hook=progress_hook,
            format_type=format_type,
            resolution=resolution,
            audio_format=audio_format,
        )

    def _download(
        self,
        url: str,
        progress_hook=None,
        format_type: str = "video",
        resolution: str = "best",
        audio_format: str = "mp3",
    ):
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

        if self.proxy:
            print("Proxy: enabled")

        if self.cookiefile and os.path.exists(self.cookiefile):
            print(f"Cookies: loaded from {self.cookiefile}")
        else:
            print("Cookies: none (anonymous request)")

        if IMPERSONATE_TARGET:

            print(f"Impersonate: {IMPERSONATE_TARGET}")
        else:
            print(
                "Impersonate: NOT AVAILABLE (curl_cffi not installed — "
                "add the 'curl-cffi' extra to requirements.txt)"
            )

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

            fallback_clients = ["ios", "android", "mweb", "tv", "android_vr"]

            fallback_formats = (
                ["bestvideo*+bestaudio/best", "b/best/worst", "18/22/b/best"]
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
                print("Standard fallback clients failed. Attempting direct urllib stream extraction recovery...")
                direct_ok, direct_path = self._download_direct_stream(url)
                if direct_ok and direct_path:
                    expected_path = direct_path
                    info = {"filepath": direct_path}
                    success = True
                    print(f"Direct stream recovery succeeded: {direct_path}")

            if not success:
                raise RuntimeError(
                    f"yt-dlp download failed: {error_message} "
                    f"(Fallback error: {last_fallback_err})"
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
