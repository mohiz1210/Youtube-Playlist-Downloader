import uuid
from datetime import datetime
from threading import Lock


class JobManager:

    def __init__(self):

        self.jobs = {}

        # Protect job updates from multiple threads
        self.lock = Lock()

    def create_job(
        self,
        total_videos: int
    ):

        job_id = str(uuid.uuid4())

        job = {
            "job_id": job_id,
            "status": "queued",
            "total_videos": total_videos,
            "completed": 0,
            "failed": 0,
            "created_at": datetime.utcnow(),
        }

        with self.lock:

            self.jobs[job_id] = job

        return job

    def get_job(
        self,
        job_id: str
    ):

        with self.lock:

            job = self.jobs.get(job_id)

            if not job:
                return None

            return job.copy()

    def update_job(
        self,
        job_id: str,
        **updates
    ):

        with self.lock:

            job = self.jobs.get(job_id)

            if not job:
                return None

            job.update(updates)

            return job.copy()


# Shared JobManager instance
job_manager = JobManager()