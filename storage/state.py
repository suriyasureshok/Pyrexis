"""
State management for storage system.

"""

import shelve
from typing import Optional

from models.job import Job
from models.result import Result

class StorageState:
    """
    Surable storage for Job and Result objects using shelve.
    Acts as a trust boundary: everything returned is validated.
    """
    
    def __init__(self, path: str):
        self._path = path

    # ------- Job storage -------
    def save_job(self, job: Job) -> None:
        """
        Save a Job object to storage atomically.
        Args:
            job (Job): The Job object to save.
        """
        key = f"job:{job.job_id}"

        with shelve.open(self._path, writeback=False) as db:
            db[key] = job.model_dump()

    def load_job(self, job_id: str) -> Optional[Job]:
        """
        Load a Job object from storage.
        Args:
            job_id (str): The ID of the Job to load.
        Returns:
            Optional[Job]: The loaded Job object, or None if not found.
        """
        key = f"job:{job_id}"

        with shelve.open(self._path, writeback=False) as db:
            raw = db.get(key)

            if raw is None:
                return None
            
            try:
                job = Job(**raw)
                return job
            except Exception:
                # Corrupted or invalid data
                return None
            
    # ------- Result storage -------
    def save_result(self, result: Result) -> None:
        """
        Save a Result object to storage atomically.
        Args:
            result (Result): The Result object to save.
        """
        key = f"result:{result.job_id}"

        with shelve.open(self._path, writeback=False) as db:
            if key in db:
                raise RuntimeError(
                    f"Result for job_id {result.job_id} already exists."
                    )
            db[key] = result.model_dump()

    def load_result(self, job_id: str) -> Optional[Result]:
        """
        Load a Result object from storage.
        Args:
            job_id (str): The ID of the Job whose Result to load.
        Returns:
            Optional[Result]: The loaded Result object, or None if not found.
        """
        key = f"result:{job_id}"

        with shelve.open(self._path, writeback=False) as db:
            raw = db.get(key)

            if raw is None:
                return None
            
            try:
                result = Result(**raw)
                return result
            except Exception:
                # Corrupted or invalid data
                return None