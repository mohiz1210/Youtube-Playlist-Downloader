from app.core.celery_app import celery_app
from app.services.playlist_downloader import PlaylistDownloader

playlist_downloader = PlaylistDownloader()


@celery_app.task(name="download_playlist_task")
def download_playlist_task(
    job_id: str,
    videos: list[dict],
    format_type: str = "video",
    resolution: str = "best",
    audio_format: str = "mp3",
    download_subtitles: bool = False,
):
    playlist_downloader.download_playlist(
        job_id,
        videos,
        format_type=format_type,
        resolution=resolution,
        audio_format=audio_format,
        download_subtitles=download_subtitles,
    )
    return {"job_id": job_id, "status": "completed"}
