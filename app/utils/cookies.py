import hashlib
import os
import tempfile
from pathlib import Path


def _write_cookies_to_tempfile(cookies_txt: str, prefix: str) -> str:
    """Materialize cookies.txt content to a content-hashed temp file and
    return its path. Same content -> same file (cheap reuse); different
    content -> a different file, so two different cookie sets (e.g. two
    different visitors) never collide or overwrite one another."""
    digest = hashlib.sha256(cookies_txt.encode("utf-8")).hexdigest()[:16]
    temp_path = Path(tempfile.gettempdir()) / f"{prefix}_{digest}.txt"

    if not temp_path.exists():
        temp_path.write_text(cookies_txt, encoding="utf-8")

    return str(temp_path)


def resolve_cookiefile() -> str | None:
    """Resolve the SERVER'S OWN cookies.txt path for yt-dlp to use — this is
    the deployer's/operator's cookies, shared by every visitor unless a
    request supplies its own (see materialize_cookies_txt).

    Priority:
      1. YTDLP_COOKIES_FILE — path to an existing cookies.txt already on disk
         (typical for running locally).
      2. YTDLP_COOKIES_TXT — the raw *contents* of a Netscape-format
         cookies.txt file. This is for hosted environments like Streamlit
         Community Cloud, where there's no browser to read cookies from and
         no writable place to keep a file except at deploy time — paste the
         exported cookies.txt content into the app's Secrets under this key
         (Streamlit exposes string secrets as environment variables too) and
         we materialize it to a temp file here, once, and reuse it.

    Returns None if neither is configured, in which case callers should fall
    back to YTDLP_COOKIES_FROM_BROWSER (which only works when a real, logged
    -in browser exists on the same machine the code is running on).
    """
    cookiefile = os.environ.get("YTDLP_COOKIES_FILE")
    if cookiefile and os.path.exists(cookiefile):
        return cookiefile

    cookies_txt = os.environ.get("YTDLP_COOKIES_TXT")
    if not cookies_txt:
        return None

    return _write_cookies_to_tempfile(cookies_txt, prefix="ytdlp_cookies")


def materialize_cookies_txt(cookies_txt: str) -> str | None:
    """Materialize a PER-REQUEST cookies.txt (e.g. pasted/uploaded by a
    visitor in the UI, or sent by a client through the API) to a temp file
    and return its path. Kept in a separate filename namespace from
    resolve_cookiefile() so a visitor's own cookies are never confused with
    the server operator's cookies, even if both happen to be configured at
    once. Returns None for empty/whitespace-only input."""
    if not cookies_txt or not cookies_txt.strip():
        return None

    return _write_cookies_to_tempfile(cookies_txt, prefix="ytdlp_user_cookies")
