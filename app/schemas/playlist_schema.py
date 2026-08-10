from pydantic import BaseModel
from typing import List


class PlaylistRequest(BaseModel):
    url: str
    


class PlaylistVideo(BaseModel):
    id: str
    title: str
    url: str

class PlaylistResponse(BaseModel):
    title: str
    uploader: str | None = None
    video_count: int
    thumbnail: str | None = None
    videos: list[PlaylistVideo]