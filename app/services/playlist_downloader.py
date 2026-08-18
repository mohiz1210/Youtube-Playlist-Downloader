from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from app.services.downloader import (
    VideoDownloader
)

from app.jobs.manager import (
    job_manager
)


class PlaylistDownloader:

    MAX_WORKERS = 4

    # =====================================================
    # PROGRESS HOOK
    # =====================================================

    def create_progress_hook(
        self,
        job_id: str,
        video_id: str,
    ):

        def progress_hook(data):
            if job_manager.is_cancelled(job_id):
                raise RuntimeError("JOB_CANCELLED_BY_USER")

            import time
            while job_manager.is_paused(job_id):
                if job_manager.is_cancelled(job_id):
                    raise RuntimeError("JOB_CANCELLED_BY_USER")
                time.sleep(1)

            status = data.get(
                "status"
            )


            # ---------------------------------------------
            # DOWNLOADING
            # ---------------------------------------------

            if status == "downloading":

                downloaded = data.get(
                    "downloaded_bytes",
                    0
                )

                total = (
                    data.get("total_bytes")
                    or
                    data.get(
                        "total_bytes_estimate",
                        0
                    )
                )

                if total:

                    percentage = (
                        downloaded / total
                    ) * 100

                else:

                    percentage = 0.0

                speed = data.get(
                    "_speed_str"
                )

                eta = data.get(
                    "_eta_str"
                )

                filename = data.get(
                    "filename"
                )

                # Update video
                job_manager.update_video(
                    job_id,
                    video_id,

                    status="downloading",

                    progress=round(
                        percentage,
                        2
                    ),

                    downloaded_bytes=downloaded,

                    total_bytes=total,

                    speed=speed,

                    eta=eta,

                    filepath=filename,
                )

            # ---------------------------------------------
            # FINISHED
            # ---------------------------------------------

            elif status == "finished":

                filename = data.get(
                    "filename"
                )

                job_manager.update_video(
                    job_id,
                    video_id,

                    status="processing",

                    progress=100.0,

                    downloaded_bytes=data.get(
                        "downloaded_bytes",
                        0
                    ),

                    filepath=filename,
                )

        return progress_hook

    # =====================================================
    # DOWNLOAD SINGLE VIDEO
    # =====================================================

    def download_single_video(
        self,
        job_id: str,
        video: dict,
        format_type: str = "video",
        resolution: str = "best",
        audio_format: str = "mp3",
        playlist_title: str | None = None,
    ):
        video_id = video.get("id")
        video_url = video.get("url")
        video_title = video.get("title", "Unknown title")

        try:
            if job_manager.is_cancelled(job_id):
                return {"status": "cancelled", "video_id": video_id}

            if not video_url:
                raise ValueError("Video URL is missing")

            job_manager.update_video(
                job_id,
                video_id,
                status="downloading",
            )

            job_manager.update_job(
                job_id,
                current_video=video_title,
            )

            progress_hook = self.create_progress_hook(
                job_id,
                video_id,
            )

            if not playlist_title:
                job_info = job_manager.get_job(job_id)
                playlist_title = job_info.get("playlist_title") if job_info else f"job_{job_id}"

            downloader = VideoDownloader(subfolder=playlist_title)

            filepath = downloader.download(
                video_url,
                progress_hook=progress_hook,
                format_type=format_type,
                resolution=resolution,
                audio_format=audio_format,
            )




            # Check again if job was cancelled during download
            if job_manager.is_cancelled(job_id):
                job_manager.update_video(
                    job_id,
                    video_id,
                    status="cancelled",
                )
                return {"status": "cancelled", "video_id": video_id}

            # Mark completed
            job_manager.update_video(
                job_id,
                video_id,
                status="completed",
                progress=100.0,
                filepath=filepath,
                eta=None,
            )

            # Update completed count
            job = job_manager.get_job(
                job_id
            )

            if job and not job_manager.is_cancelled(job_id):
                job_manager.update_job(
                    job_id,
                    completed=(
                        job["completed"] + 1
                    ),
                )

            return {
                "status": "success",
                "video_id": video_id,
                "filepath": filepath,
            }

        except Exception as error:

            if "JOB_CANCELLED_BY_USER" in str(error) or job_manager.is_cancelled(job_id):
                job_manager.update_video(
                    job_id,
                    video_id,
                    status="cancelled",
                    error=None,
                )
                return {"status": "cancelled", "video_id": video_id}

            print(
                f"[JOB {job_id}] "
                f"Failed: {video_title}"
            )

            print(
                f"Error: {error}"
            )

            job_manager.update_video(
                job_id,
                video_id,

                status="failed",

                error=str(error),
            )

            job = job_manager.get_job(
                job_id
            )

            if job and not job_manager.is_cancelled(job_id):

                job_manager.update_job(
                    job_id,

                    failed=(
                        job["failed"] + 1
                    ),
                )

            return {
                "status": "failed",
                "video_id": video_id,
                "error": str(error),
            }

    # =====================================================
    # DOWNLOAD PLAYLIST
    # =====================================================

    def download_playlist(
        self,
        job_id: str,
        videos: list[dict],
        format_type: str = "video",
        resolution: str = "best",
        audio_format: str = "mp3",
        playlist_title: str | None = None,
    ):

        job_manager.update_job(
            job_id,
            status="downloading",
        )

        total_videos = len(
            videos
        )

        print(
            f"[JOB {job_id}] "
            f"Starting {total_videos} videos for playlist '{playlist_title}'"
        )

        with ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS
        ) as executor:

            futures = []

            for video in videos:

                future = executor.submit(
                    self.download_single_video,
                    job_id,
                    video,
                    format_type=format_type,
                    resolution=resolution,
                    audio_format=audio_format,
                    playlist_title=playlist_title,
                )

                futures.append(
                    future
                )




            for future in as_completed(
                futures
            ):

                try:

                    future.result()

                except Exception as error:

                    print(
                        f"[JOB {job_id}] "
                        f"Worker error: {error}"
                    )

        # Check if job was cancelled
        if job_manager.is_cancelled(job_id):
            job_manager.update_job(
                job_id,
                status="cancelled",
                current_video=None,
            )
            print(f"[JOB {job_id}] Cancelled cleanly")
            return

        # Get final job
        job = job_manager.get_job(
            job_id
        )

        if not job:
            return

        completed = job[
            "completed"
        ]

        failed = job[
            "failed"
        ]

        # Final status
        if completed == total_videos:

            final_status = "completed"

        elif completed + failed == total_videos:

            final_status = (
                "completed_with_errors"
            )

        else:

            final_status = "failed"

        job_manager.update_job(
            job_id,
            status=final_status,
            current_video=None,
        )

        print(
            f"[JOB {job_id}] "
            f"Finished"
        )