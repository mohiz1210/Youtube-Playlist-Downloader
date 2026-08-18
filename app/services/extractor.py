import yt_dlp

from app.core.exceptions import PlaylistError
from app.utils.cookies import materialize_cookies_txt, delete_cookiefile

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

    def extract(self, url: str, cookies_txt: str | None = None):
        # Two options only — see VideoDownloader for the full rationale:
        #   A. No cookies_txt supplied — plain anonymous extraction.
        #   B. cookies_txt — THIS visitor's own cookies.txt content, used
        #      only for this one extraction and deleted right after,
        #      never persisted or shared with anyone else.
        cookiefile = materialize_cookies_txt(cookies_txt)

        options = {
            "quiet": True,
            "extract_flat": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },
            **({"impersonate": IMPERSONATE_TARGET} if IMPERSONATE_TARGET else {}),
            **({"cookiefile": cookiefile} if cookiefile else {}),
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

        finally:
            delete_cookiefile(cookiefile)
