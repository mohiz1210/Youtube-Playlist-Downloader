from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.downloader import VideoDownloader
from app.jobs.manager import job_manager


class PlaylistDownloader:

    # Maximum number of videos downloading simultaneously
    MAX_WORKERS = 4

    def download_single_video(
        self,
        job_id: str,
        video: dict,
    ):

        video_url = video.get("url")
        video_title = video.get(
            "title",
            "Unknown title"
        )

        try:

            if not video_url:

                raise ValueError(
                    "Video URL is missing"
                )

            print(
                f"[JOB {job_id}] "
                f"Starting: {video_title}"
            )

            # Create downloader for this worker
            downloader = VideoDownloader()

            # Download video
            downloader.download(
                video_url
            )

            # Update completed count
            job = job_manager.get_job(
                job_id
            )

            if not job:
                return

            job_manager.update_job(
                job_id,
                completed=job["completed"] + 1,
            )

            print(
                f"[JOB {job_id}] "
                f"Completed: {video_title}"
            )

            return {
                "status": "success",
                "video": video_title,
            }

        except Exception as error:

            print(
                f"[JOB {job_id}] "
                f"Failed: {video_title}"
            )

            print(
                f"[JOB {job_id}] "
                f"Error: {error}"
            )

            job = job_manager.get_job(
                job_id
            )

            if job:

                job_manager.update_job(
                    job_id,
                    failed=job["failed"] + 1,
                )

            return {
                "status": "failed",
                "video": video_title,
                "error": str(error),
            }


    def download_playlist(
        self,
        job_id: str,
        videos: list[dict],
    ):

        # Mark job as downloading
        job_manager.update_job(
            job_id,
            status="downloading",
        )

        total_videos = len(videos)

        print(
            f"[JOB {job_id}] "
            f"Starting playlist download"
        )

        print(
            f"[JOB {job_id}] "
            f"Total videos: {total_videos}"
        )

        # Create thread pool
        with ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS
        ) as executor:

            futures = []

            # Submit all videos
            for video in videos:

                future = executor.submit(
                    self.download_single_video,
                    job_id,
                    video,
                )

                futures.append(future)

            # Wait for all downloads
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

        # Get final job
        job = job_manager.get_job(
            job_id
        )

        if not job:
            return

        completed = job["completed"]
        failed = job["failed"]

        # Determine final status
        if completed == total_videos:

            final_status = "completed"

        elif completed + failed == total_videos:

            final_status = "completed_with_errors"

        else:

            final_status = "failed"

        job_manager.update_job(
            job_id,
            status=final_status,
        )

        print(
            f"[JOB {job_id}] "
            f"Playlist finished"
        )

        print(
            f"[JOB {job_id}] "
            f"Completed: {completed}"
        )

        print(
            f"[JOB {job_id}] "
            f"Failed: {failed}"
        )