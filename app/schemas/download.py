from pydantic import BaseModel


class DownloadRequest(BaseModel):
    url: str


class DownloadResponse(BaseModel):
    filename: str
    filepath: str
    status: str


class PlaylistDownloadResponse(BaseModel):
    job_id: str
    status: str
    total_videos: int


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_videos: int
    completed: int
    failed: int