import uuid
from datetime import datetime
from threading import Lock


class JobManager:

    def __init__(self):

        self.jobs = {}

        self.lock = Lock()

    # =====================================================
    # CREATE JOB
    # =====================================================

    def create_job(
        self,
        total_videos: int,
        videos: list[dict],
        playlist_title: str = "Playlist",
        cookies_txt: str | None = None,
    ):

        job_id = str(uuid.uuid4())

        video_progress = {}

        for video in videos:

            video_id = video.get("id")

            video_progress[video_id] = {
                "id": video_id,
                "title": video.get(
                    "title",
                    "Unknown title"
                ),
                "url": video.get(
                    "url",
                    ""
                ),
                "status": "queued",
                "progress": 0.0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "speed": None,
                "eta": None,
                "filepath": None,
                "error": None,
            }

        job = {
            "job_id": job_id,
            "playlist_title": playlist_title,
            "status": "queued",

            "total_videos": total_videos,

            "completed": 0,

            "failed": 0,

            "progress": 0.0,

            "current_video": None,

            "videos": video_progress,

            "created_at": datetime.utcnow(),

            # Kept only for internal reuse (e.g. by the retry endpoint) —
            # not part of JobStatusResponse, so it's never returned to
            # clients via the status API.
            "cookies_txt": cookies_txt,
        }


        with self.lock:

            self.jobs[job_id] = job

        return job

    # =====================================================
    # GET JOB
    # =====================================================

    def get_job(
        self,
        job_id: str,
    ):

        with self.lock:

            job = self.jobs.get(
                job_id
            )

            if not job:
                return None

            job_copy = job.copy()
            job_copy["videos"] = list(job["videos"].values())
            return job_copy

    # =====================================================
    # UPDATE JOB
    # =====================================================

    def update_job(
        self,
        job_id: str,
        **updates,
    ):

        with self.lock:

            job = self.jobs.get(
                job_id
            )

            if not job:
                return None

            job.update(
                updates
            )

            return job.copy()

    # =====================================================
    # UPDATE VIDEO
    # =====================================================

    def update_video(
        self,
        job_id: str,
        video_id: str,
        **updates,
    ):

        with self.lock:

            job = self.jobs.get(
                job_id
            )

            if not job:
                return None

            video = job["videos"].get(
                video_id
            )

            if not video:
                return None

            video.update(
                updates
            )

            # ---------------------------------------------
            # Calculate overall progress
            # ---------------------------------------------

            videos = job["videos"].values()

            if videos:

                total_progress = sum(
                    video["progress"]
                    for video in videos
                )

                job["progress"] = round(
                    total_progress
                    / len(job["videos"]),
                    2,
                )

            return video.copy()

    # =====================================================
    # JOB CONTROL METHODS
    # =====================================================

    def cancel_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            job["status"] = "cancelled"
            job["current_video"] = None
            for v in job["videos"].values():
                if v["status"] in ("queued", "downloading"):
                    v["status"] = "cancelled"
            return True

    def pause_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            job["status"] = "paused"
            return True

    def resume_job(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            job["status"] = "downloading"
            return True

    def reset_failed_videos(self, job_id: str) -> list[dict]:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return []
            failed_videos = []
            for v in job["videos"].values():
                if v["status"] == "failed":
                    v["status"] = "queued"
                    v["error"] = None
                    v["progress"] = 0.0
                    failed_videos.append(v.copy())
            if failed_videos:
                job["failed"] = max(0, job["failed"] - len(failed_videos))
                job["status"] = "downloading"
            return failed_videos

    def is_cancelled(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            return job.get("status") == "cancelled" if job else False

    def is_paused(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            return job.get("status") == "paused" if job else False


job_manager = JobManager()