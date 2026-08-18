import os
import threading

# How many downloads (one playlist job OR one single video, each counts as
# ONE regardless of how many videos are inside a playlist) a visitor gets
# on the SERVER'S shared cookies before they must supply their own. Only
# applies when the visitor didn't paste their own cookies.txt — anyone
# using their own cookies is unlimited, since that download rides on
# their own account, not the shared one.
FREE_DOWNLOADS_PER_VISITOR = int(os.environ.get("SHARED_COOKIES_FREE_LIMIT", "1"))

# In-memory only: resets on app restart and isn't shared across separate
# processes (e.g. running `uvicorn` and `streamlit run` as two separate
# local processes). That's an acceptable trade-off for a soft, no-login
# usage limit — the goal is discouraging casual overuse of the owner's
# account, not airtight enforcement.
_lock = threading.Lock()
_usage: dict[str, int] = {}


class QuotaExceededError(Exception):
    """Raised when a visitor already used up their free download(s) on the
    shared cookies and didn't supply their own for this request."""


def check_and_consume(visitor_id: str | None, has_own_cookies: bool) -> None:
    """Call once per download ACTION (starting one playlist job, or one
    single-video download) — never per video inside a playlist. Raises
    QuotaExceededError if the limit is already used up and no own cookies
    were supplied; otherwise consumes one unit of quota (or is a no-op
    when has_own_cookies is True)."""
    if has_own_cookies:
        return

    if not visitor_id:
        # Couldn't identify the visitor (e.g. IP unavailable). Fail open
        # rather than blocking every visitor outright.
        return

    with _lock:
        used = _usage.get(visitor_id, 0)
        if used >= FREE_DOWNLOADS_PER_VISITOR:
            raise QuotaExceededError(
                "You've used your free download"
                + ("" if FREE_DOWNLOADS_PER_VISITOR == 1 else "s")
                + " on the app owner's shared YouTube session "
                f"({FREE_DOWNLOADS_PER_VISITOR} allowed). To download more "
                "playlists or videos, paste your own cookies.txt in the "
                "\"\U0001F36A YouTube Cookies\" section of the sidebar — "
                "your downloads then use your own session instead, with no "
                "limit."
            )
        _usage[visitor_id] = used + 1


def remaining(visitor_id: str | None) -> int:
    """Best-effort count of free shared-cookie downloads left for this
    visitor. Returns the full limit if the visitor can't be identified."""
    if not visitor_id:
        return FREE_DOWNLOADS_PER_VISITOR
    with _lock:
        return max(0, FREE_DOWNLOADS_PER_VISITOR - _usage.get(visitor_id, 0))
