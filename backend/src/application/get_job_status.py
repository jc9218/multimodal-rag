from typing import Optional
from src.domain.exceptions import JobNotFoundError
from src.domain.models import IngestionJob
from src.ports.job_repository_port import JobRepositoryPort


class GetJobStatusUseCase:
    def __init__(self, job_repo: JobRepositoryPort):
        self.job_repo = job_repo

    def execute(self, job_id: str) -> IngestionJob:
        job = self.job_repo.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID '{job_id}' not found.")
        return job
