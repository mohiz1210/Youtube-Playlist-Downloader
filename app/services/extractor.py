import os

import yt_dlp

from app.core.exceptions import PlaylistError
from app.utils.cookies import resolve_cookiefile, materialize_cookies_txt

# Browser TLS/HTTP2 impersonation (yt-dlp's --impersonate) — see
# app/services/downloader.py for the full rationale. Same optional
# dependency, same fallback-to-off behavior if curl_cffi isn't installed.
try:
    import curl_cffi  # noqa: F401
    from yt_dlp.networking.impersonate import ImpersonateTarget

    IMPERSONATE_TARGET = ImpersonateTarget.from_str("chrome")
except Exception:
    IMPERSONATE_TARGET = None


class PlaylistExtractor:

    def _cookie_options(self, cookies_txt: str | None = None) -> dict:
        """Same cookie resolution used by VideoDownloader, so playlist
        extraction doesn't hit YouTube's "Sign in to confirm you're not a
        bot" check either.

        Priority: a visitor-supplied cookies_txt (this call) > the server
        operator's own cookies.txt (YTDLP_COOKIES_FILE / YTDLP_COOKIES_TXT)
        > YTDLP_COOKIES_FROM_BROWSER (local runs only — never works on a
        hosted deploy, since there's no real browser there)."""
        cookiefile = materialize_cookies_txt(cookies_txt) or resolve_cookiefile()
        if cookiefile:
            return {"cookiefile": cookiefile}

        cookies_from_browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER")
        if cookies_from_browser:
            browser, _, profile = cookies_from_browser.partition(":")
            return {
                "cookiesfrombrowser": (
                    browser.strip(),
                    profile.strip() or None,
                    None,
                    None,
                )
            }

        return {}

    def extract(self, url: str, cookies_txt: str | None = None):

        options = {
            "quiet": True,
            "extract_flat": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },
            **({"impersonate": IMPERSONATE_TARGET} if IMPERSONATE_TARGET else {}),
            **self._cookie_options(cookies_txt),
        }

        try:

            with yt_dlp.YoutubeDL(options) as ydl:

                data = ydl.extract_info(
                    url,
                    download=False,
                )

                return data

        except Exception as error:
            raise PlaylistError(str(error))
