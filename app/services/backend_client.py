import threading
import requests
from app.jobs.manager import job_manager
from app.services.downloader import VideoDownloader
from app.services.playlist_downloader import PlaylistDownloader
from app.services.playlist_service import PlaylistService

playlist_service = PlaylistService()
playlist_downloader = PlaylistDownloader()
video_downloader = VideoDownloader()


def extract_playlist_api(api_base_url: str, url: str):
    """Extract playlist info via FastAPI HTTP or direct Python fallback for Streamlit Cloud."""
    try:
        res = requests.post(
            f"{api_base_url}/playlist/extract",
            json={"url": url},
            timeout=5,
        )
        if res.status_code == 200:
            return True, res.json(), None
        detail = res.json().get("detail", res.text) if res.content else f"HTTP {res.status_code}"
        return False, None, detail
    except Exception:
        # Fallback to direct Python execution (e.g. Streamlit Cloud)
        try:
            data = playlist_service.get_playlist(url)
            return True, data, None
        except Exception as e:
            return False, None, str(e)


def start_playlist_download_api(
    api_base_url: str,
    url: str,
    format_type: str,
    resolution: str,
    audio_format: str,
    selected_video_ids: list[str] | None = None,
):
    """Start playlist download via FastAPI HTTP or direct Python background thread fallback."""
    payload = {
        "url": url,
        "format_type": format_type,
        "resolution": resolution,
        "audio_format": audio_format,
        "selected_video_ids": selected_video_ids,
    }
    try:
        res = requests.post(
            f"{api_base_url}/playlist/download",
            json=payload,
            timeout=5,
        )
        if res.status_code == 202:
            return True, res.json(), None
        detail = res.json().get("detail", res.text) if res.content else f"HTTP {res.status_code}"
        return False, None, detail
    except Exception:
        # Fallback to direct Python execution (e.g. Streamlit Cloud)
        try:
            playlist = playlist_service.get_playlist(url)
            videos_to_download = playlist["videos"]
            if selected_video_ids:
                videos_to_download = [
                    v for v in videos_to_download
                    if v.get("id") in selected_video_ids
                ]

            if not videos_to_download:
                return False, None, "No matching videos selected for download"

            job = job_manager.create_job(
                total_videos=len(videos_to_download),
                videos=videos_to_download,
                playlist_title=playlist["title"],
            )

            thread = threading.Thread(
                target=playlist_downloader.download_playlist,
                args=(job["job_id"], videos_to_download),
                kwargs={
                    "format_type": format_type,
                    "resolution": resolution,
                    "audio_format": audio_format,
                    "playlist_title": playlist["title"],
                },
                daemon=True,
            )
            thread.start()

            return True, {
                "job_id": job["job_id"],
                "status": job["status"],
                "total_videos": job["total_videos"],
            }, None
        except Exception as e:
            return False, None, str(e)


def get_job_status_api(api_base_url: str, job_id: str):
    """Get job status via HTTP or direct job manager fallback."""
    try:
        res = requests.get(f"{api_base_url}/playlist/status/{job_id}", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return job_manager.get_job(job_id)



def control_job_api(api_base_url: str, job_id: str, action: str):
    """Control job (pause/resume/cancel/retry) via HTTP or direct job manager fallback."""
    try:
        res = requests.post(f"{api_base_url}/playlist/jobs/{job_id}/{action}", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass

    if action == "pause":
        return job_manager.pause_job(job_id)
    elif action == "resume":
        return job_manager.resume_job(job_id)
    elif action == "cancel":
        return job_manager.cancel_job(job_id)
    elif action == "retry":
        return job_manager.retry_job(job_id)
    return None


def download_single_video_api(
    api_base_url: str,
    url: str,
    format_type: str,
    resolution: str,
    audio_format: str,
):
    """Download single video via HTTP or direct Python execution fallback."""
    payload = {
        "url": url,
        "format_type": format_type,
        "resolution": resolution,
        "audio_format": audio_format,
    }
    try:
        res = requests.post(f"{api_base_url}/download/video", json=payload, timeout=5)
        if res.status_code == 200:
            return True, res.json(), None
        return False, None, res.text
    except Exception:
        try:
            filepath = video_downloader.download(
                url,
                format_type=format_type,
                resolution=resolution,
                audio_format=audio_format,
            )
            return True, {"status": "success", "filepath": filepath}, None
        except Exception as e:
            return False, None, str(e)


import os
import shutil
from app.utils.filehandler import DOWNLOAD_DIRECTORY, sanitize_folder_name


def get_zip_file_bytes(api_base_url: str, job_id: str):
    """Get zip bytes via HTTP or direct zip creation fallback."""
    try:
        zip_res = requests.get(f"{api_base_url}/download/zip/{job_id}", timeout=5)
        if zip_res.status_code == 200:
            return zip_res.content
    except Exception:
        pass

    job = job_manager.get_job(job_id)
    if not job:
        return None

    playlist_title = job.get("playlist_title", "")
    clean_title = sanitize_folder_name(playlist_title) if playlist_title else ""

    job_dir = None
    if clean_title and (DOWNLOAD_DIRECTORY / clean_title).is_dir():
        job_dir = DOWNLOAD_DIRECTORY / clean_title
    elif (DOWNLOAD_DIRECTORY / f"job_{job_id}").is_dir():
        job_dir = DOWNLOAD_DIRECTORY / f"job_{job_id}"

    if not job_dir or not any(job_dir.iterdir()):
        return None

    zip_name = clean_title if clean_title else f"playlist_{job_id}"
    zip_base_name = str(DOWNLOAD_DIRECTORY / zip_name)
    zip_file_path = shutil.make_archive(zip_base_name, "zip", str(job_dir))

    if os.path.exists(zip_file_path):
        with open(zip_file_path, "rb") as f:
            return f.read()
    return None

