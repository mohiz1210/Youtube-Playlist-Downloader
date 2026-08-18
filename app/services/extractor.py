import os

import yt_dlp

from app.core.exceptions import PlaylistError


class PlaylistExtractor:

    def _cookie_options(self) -> dict:
        """Same YTDLP_COOKIES_FILE / YTDLP_COOKIES_FROM_BROWSER env vars used
        by VideoDownloader, so playlist extraction doesn't hit YouTube's
        "Sign in to confirm you're not a bot" check either."""
        cookiefile = os.environ.get("YTDLP_COOKIES_FILE")
        cookies_from_browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER")

        if cookiefile and os.path.exists(cookiefile):
            return {"cookiefile": cookiefile}

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

    def extract(self, url: str):

        options = {
            "quiet": True,
            "extract_flat": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },
            **self._cookie_options(),
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