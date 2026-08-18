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
from app.utils.cookies import resolve_cookiefile, materialize_cookies_txt


class VideoDownloader:

    def __init__(
        self,
        subfolder: str | None = None,
        cookiefile: str | None = None,
        cookies_from_browser: str | None = None,
        cookies_txt: str | None = None,
        proxy: str | None = None,
    ):
        self.download_dir = create_download_directory(subfolder)
        # Cookies are the real fix for YouTube's "Sign in to confirm
        # you're not a bot" error — the player-client spoofing below is
        # only a fallback and YouTube increasingly blocks it outright.
        # Priority:
        #   1. cookies_txt — cookies.txt CONTENT supplied for this one
        #      request/visitor (e.g. pasted into the UI). Takes priority
        #      over everything else so one visitor's own cookies are used
        #      for their own request instead of the server operator's.
        #   2. cookiefile / resolve_cookiefile() — an explicit path, or the
        #      server operator's own cookies.txt (YTDLP_COOKIES_FILE, or its
        #      content via YTDLP_COOKIES_TXT for hosted deploys like
        #      Streamlit Cloud) — shared by every visitor who didn't supply
        #      their own.
        #   3. cookies_from_browser (YTDLP_COOKIES_FROM_BROWSER) — only
        #      works when this code runs on the same machine as a real,
        #      logged-in browser, i.e. locally, never on a cloud/server
        #      deploy.
        self.cookiefile = (
            materialize_cookies_txt(cookies_txt)
            or cookiefile
            or resolve_cookiefile()
        )
        self.cookies_from_browser = cookies_from_browser or os.environ.get(
            "YTDLP_COOKIES_FROM_BROWSER"
        )
        # Optional proxy, e.g. "http://user:pass@host:port".
        # Can also be supplied via env var so you don't have to
        # hardcode credentials anywhere.
        self.proxy = proxy or os.environ.get("YTDLP_PROXY")

    # ---------------------------------------------------------
    # COOKIE OPTIONS HELPER
    # ---------------------------------------------------------

    def _cookiesfrombrowser_tuple(self):
        """Parse YTDLP_COOKIES_FROM_BROWSER ("chrome" or "chrome:Profile 1")
        into the (browser, profile, keyring, container) tuple yt-dlp expects."""
        browser, _, profile = self.cookies_from_browser.partition(":")
        return (browser.strip(), profile.strip() or None, None, None)
 
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

        if IMPERSONATE_TARGET:
            options["impersonate"] = IMPERSONATE_TARGET

        if self.cookiefile and os.path.exists(self.cookiefile):
            options["cookiefile"] = self.cookiefile
        elif self.cookies_from_browser:
            options["cookiesfrombrowser"] = self._cookiesfrombrowser_tuple()

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
        elif self.cookies_from_browser:
            opts["cookiesfrombrowser"] = self._cookiesfrombrowser_tuple()
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
            print(f"Cookies: file={self.cookiefile}")
        elif self.cookies_from_browser:
            print(f"Cookies: browser={self.cookies_from_browser}")
        else:
            print(
                "Cookies: NOT CONFIGURED (set YTDLP_COOKIES_TXT/YTDLP_COOKIES_FILE "
                "for hosted deploys, or YTDLP_COOKIES_FROM_BROWSER for local runs)"
            )

        if self.proxy:
            print("Proxy: enabled")

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
            if not success:
                print("Standard fallback clients failed. Attempting direct urllib stream extraction recovery...")
                direct_ok, direct_path = self._download_direct_stream(url)
                if direct_ok and direct_path:
                    expected_path = direct_path
                    info = {"filepath": direct_path}
                    success = True
                    print(f"Direct stream recovery succeeded: {direct_path}")


            if not success:
                # Check BOTH the primary error and the fallback-client error —
                # the primary failure is often a bare "403 Forbidden" while the
                # real "sign in to confirm you're not a bot" text only shows up
                # in the fallback error, so checking error_message alone missed
                # it and showed the less useful generic proxy hint instead.
                combined_message = (
                    f"{error_message} {last_fallback_err or ''}"
                ).lower()
                is_bot_check = (
                    "sign in" in combined_message
                    or "not a bot" in combined_message
                )
                if is_bot_check and not self.cookiefile and not self.cookies_from_browser:
                    hint = (
                        " YouTube is asking for authentication on this IP/session — "
                        "player-client spoofing alone is no longer enough to bypass "
                        "this check, and no cookies are configured for this request. "
                        "Running locally: set YTDLP_COOKIES_FROM_BROWSER to a browser "
                        "you're logged into YouTube with on THIS machine (e.g. "
                        "\"chrome\", \"edge\", \"firefox\"). Running on a hosted deploy "
                        "(Streamlit Cloud, Docker, etc. — no real browser exists "
                        "there, so YTDLP_COOKIES_FROM_BROWSER cannot work): export "
                        "cookies.txt from your own browser and set YTDLP_COOKIES_TXT "
                        "to its contents in the app's Secrets (or YTDLP_COOKIES_FILE "
                        "to its path), or paste it into the app's own \"YouTube "
                        "Cookies\" sidebar field instead."
                    )
                elif is_bot_check:
                    hint = (
                        " YouTube is asking for authentication on this IP/session "
                        "even though cookies are configured — they're likely expired "
                        "or invalid (YouTube cookies typically stop working after a "
                        "while, especially the __Secure-3PSID/HSID family). Re-export "
                        "a fresh cookies.txt from a browser that is currently logged "
                        "into youtube.com and update YTDLP_COOKIES_TXT (or the "
                        "pasted cookies). If a fresh export still fails immediately, "
                        "this is likely a datacenter/cloud IP block that cookies "
                        "alone can't get around; consider routing through a "
                        "residential proxy (set YTDLP_PROXY)."
                    )
                else:
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
 