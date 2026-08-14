
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.schemas.playlist_schema import (
    PlaylistRequest,
    PlaylistResponse,
)

from app.schemas.download import (
    PlaylistDownloadResponse,
    JobStatusResponse,
)

from app.services.playlist_service import PlaylistService
from app.services.playlist_downloader import PlaylistDownloader

from app.utils.validator import validate_youtube_url
from app.core.exceptions import PlaylistError
from app.jobs.manager import job_manager


router = APIRouter()

playlist_service = PlaylistService()
playlist_downloader = PlaylistDownloader()


# =========================================================
# EXTRACT PLAYLIST
# =========================================================

@router.post(
    "/playlist/extract",
    response_model=PlaylistResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_playlist(
    payload: PlaylistRequest,
):

    if not validate_youtube_url(payload.url):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube playlist URL",
        )

    try:

        return playlist_service.get_playlist(
            payload.url
        )

    except PlaylistError as error:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )


# =========================================================
# CREATE PLAYLIST DOWNLOAD JOB
# =========================================================

@router.post(
    "/playlist/download",
    response_model=PlaylistDownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def download_playlist(
    payload: PlaylistRequest,
    background_tasks: BackgroundTasks,
):

    if not validate_youtube_url(payload.url):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube playlist URL",
        )

    try:

        # Extract playlist information
        playlist = playlist_service.get_playlist(
            payload.url
        )

        # Get total number of videos
        total_videos = playlist["video_count"]

        # Create download job
        job = job_manager.create_job(
            total_videos=total_videos,
            videos=playlist["videos"]
        )

        # Start playlist download in background
        background_tasks.add_task(
            playlist_downloader.download_playlist,
            job["job_id"],
            playlist["videos"],
        )

        # Return job information immediately
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "total_videos": job["total_videos"],
        }

    except PlaylistError as error:

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )


# =========================================================
# GET DOWNLOAD JOB STATUS
# =========================================================

@router.get(
    "/playlist/status/{job_id}",
    response_model=JobStatusResponse,
)
async def get_playlist_status(
    job_id: str,
):

    job = job_manager.get_job(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download job not found",
        )

    return job
