from pydantic import BaseModel
from typing import List


class PlaylistRequest(BaseModel):
    url: str
    format_type: str = "video"  # "video" or "audio"
    resolution: str = "best"    # "best", "1080p", "720p", "480p", "360p", "worst"
    audio_format: str = "mp3"   # "mp3", "m4a", "wav", "flac"
    selected_video_ids: list[str] | None = None
    cookies_txt: str | None = None  # visitor's own cookies.txt content, optional




    


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