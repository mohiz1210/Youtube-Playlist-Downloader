from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas.download import DownloadRequest
from app.services.downloader import VideoDownloader

router = APIRouter()

downloader = VideoDownloader()


@router.post("/download/video")
async def download_video(
    payload: DownloadRequest
):

    try:

        file_path = downloader.download(
            payload.url
        )

        return {
            "status": "success",
            "filepath": file_path,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )