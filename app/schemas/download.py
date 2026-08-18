from pydantic import BaseModel


# =========================================================
# SINGLE VIDEO DOWNLOAD
# =========================================================

class DownloadRequest(BaseModel):
    url: str
    format_type: str = "video"  # "video" or "audio"
    resolution: str = "best"    # "best", "1080p", "720p", "480p", "360p", "worst"
    audio_format: str = "mp3"   # "mp3", "m4a", "wav", "flac"






class DownloadResponse(BaseModel):
    filename: str
    filepath: str
    status: str


# =========================================================
# PLAYLIST DOWNLOAD
# =========================================================

class PlaylistDownloadResponse(BaseModel):
    job_id: str
    status: str
    total_videos: int


class VideoProgress(BaseModel):

    id: str | None = None

    title: str

    url: str

    status: str

    progress: float = 0.0

    downloaded_bytes: int = 0

    total_bytes: int = 0

    speed: str | None = None

    eta: str | None = None

    filepath: str | None = None

    error: str | None = None


class JobStatusResponse(BaseModel):

    job_id: str

    status: str

    total_videos: int

    completed: int

    failed: int

    progress: float

    current_video: str | None = None

    videos: list[VideoProgress]