from fastapi import APIRouter
from fastapi import HTTPException

from app.schemas.download import DownloadRequest
from app.services.downloader import VideoDownloader

router = APIRouter()


@router.post("/download/video")
async def download_video(
    payload: DownloadRequest
):

    try:

        # Built per-request (not module-level/shared) so each visitor's own
        # cookies_txt is scoped to just their request — a shared instance
        # would risk one visitor's cookies leaking into another's
        # concurrent download.
        downloader = VideoDownloader(cookies_txt=payload.cookies_txt)

        file_path = downloader.download(
            payload.url,
            format_type=payload.format_type,
            resolution=payload.resolution,
            audio_format=payload.audio_format,
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


# =========================================================
# FILE SERVING & ZIP DOWNLOAD ENDPOINTS
# =========================================================

import os
import shutil
from pathlib import Path
from fastapi.responses import FileResponse
from app.jobs.manager import job_manager
from app.utils.filehandler import DOWNLOAD_DIRECTORY


@router.get("/download/file")
async def get_downloaded_file(filepath: str):
    file_path = Path(filepath)
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Requested file not found on server"
        )
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream"
    )


from app.utils.filehandler import DOWNLOAD_DIRECTORY, sanitize_folder_name


@router.get("/download/zip/{job_id}")
async def download_job_zip(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    playlist_title = job.get("playlist_title", "")
    clean_title = sanitize_folder_name(playlist_title) if playlist_title else ""

    job_dir = None
    if clean_title and (DOWNLOAD_DIRECTORY / clean_title).is_dir():
        job_dir = DOWNLOAD_DIRECTORY / clean_title
    elif (DOWNLOAD_DIRECTORY / f"job_{job_id}").is_dir():
        job_dir = DOWNLOAD_DIRECTORY / f"job_{job_id}"

    if not job_dir or not any(job_dir.iterdir()):
        raise HTTPException(
            status_code=404,
            detail="No files found for this job"
        )

    zip_name = clean_title if clean_title else f"playlist_{job_id}"
    zip_base_name = str(DOWNLOAD_DIRECTORY / zip_name)
    zip_file_path = shutil.make_archive(zip_base_name, "zip", str(job_dir))

    return FileResponse(
        path=zip_file_path,
        filename=f"{zip_name}.zip",
        media_type="application/zip"
    )
