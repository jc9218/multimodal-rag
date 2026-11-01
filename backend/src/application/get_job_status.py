from typing import Optional
from src.domain.exceptions import JobNotFoundError
from src.domain.models import IngestionJob
from src.ports.job_repository_port import JobRepositoryPort


# Class: GetJobStatusUseCase.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class GetJobStatusUseCase:
    # Purpose: Init.
    # Inputs: self, job_repo.
    # Output: Operation result, or None when no value is returned.
    def __init__(self, job_repo: JobRepositoryPort):
        self.job_repo = job_repo

    # Purpose: Execute.
    # Inputs: self, job_id.
    # Output: IngestionJob.
    def execute(self, job_id: str) -> IngestionJob:
        job = self.job_repo.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID '{job_id}' not found.")
        return job
