import os
import yt_dlp

from app.core.exceptions import PlaylistError
from app.services.downloader import get_default_cookiefile

try:
    import curl_cffi  # noqa: F401
    from yt_dlp.networking.impersonate import ImpersonateTarget

    IMPERSONATE_TARGET = ImpersonateTarget.from_str("chrome")
except Exception:
    IMPERSONATE_TARGET = None


class PlaylistExtractor:

    def extract(self, url: str):
        cookiefile = get_default_cookiefile()
        options = {
            "quiet": True,
            "extract_flat": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "mweb"],
                    "player_skip": ["webpage", "configs"],
                }
            },
            **({"impersonate": IMPERSONATE_TARGET} if IMPERSONATE_TARGET else {}),
            **({"cookiefile": cookiefile} if (cookiefile and os.path.exists(cookiefile)) else {}),
        }


        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                data = ydl.extract_info(
                    url,
                    download=False,
                )
                return data

        except Exception as error:
            # Fallback retry with alternate clients
            try:
                fallback_options = dict(options)
                fallback_options["extractor_args"] = {
                    "youtube": {
                        "player_client": ["ios", "mweb"],
                    }
                }
                with yt_dlp.YoutubeDL(fallback_options) as ydl:
                    return ydl.extract_info(url, download=False)
            except Exception:
                raise PlaylistError(str(error))

