import os
import tempfile
import uuid
from pathlib import Path


def materialize_cookies_txt(cookies_txt: str | None) -> str | None:
    """Write a visitor-SUPPLIED cookies.txt CONTENT (uploaded/pasted in the
    UI, or sent by an API client) to a private temp file for the duration
    of a single request/job, and return its path.

    There is no server-wide/shared cookies option anymore — this app only
    ever uses cookies a visitor explicitly provides for their own request,
    and never persists them: each call gets its own uniquely-named file
    (so concurrent requests, or several videos downloading at once from
    the same playlist job, never share or race on one file), and the
    caller is expected to delete it via delete_cookiefile() the moment
    that request/job is done, win or lose.

    Returns None for empty/whitespace-only input.
    """
    if not cookies_txt or not cookies_txt.strip():
        return None

    temp_path = Path(tempfile.gettempdir()) / f"ytdlp_cookies_{uuid.uuid4().hex}.txt"
    temp_path.write_text(cookies_txt, encoding="utf-8")
    return str(temp_path)


def delete_cookiefile(cookiefile: str | None) -> None:
    """Best-effort delete of a temp cookiefile created by
    materialize_cookies_txt(). Call this once the request/job it was
    supplied for has finished — success or failure — so a visitor's
    cookies never sit on disk longer than their own download takes."""
    if not cookiefile:
        return
    try:
        os.remove(cookiefile)
    except OSError:
        pass
