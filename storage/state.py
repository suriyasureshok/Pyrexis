"""
storage/state.py

Persistent state management for jobs and results.

This module provides the `StateStore` class, which uses Python's
`shelve` module to persist `Job` and `Result` objects. It acts as a
trust boundary by validating all objects upon retrieval.
"""

import shelve
from typing import Optional

from models.job import Job
from models.result import Result


class StateStore:
    """
    Durable storage for Job and Result objects using shelve.

    This class is responsible for:
    - Persisting Job and Result data atomically
    - Namespacing stored keys to avoid collisions
    - Validating objects on load to prevent propagation of corrupted data

    All objects returned from this storage layer are guaranteed
    to be valid Pydantic models or None.
    """

    def __init__(self, path: str):
        """
        Initialize storage state.

        Args:
            path (str): Filesystem path used by the shelve backend.
        """
        self._path = path

    # ------- Job storage -------

    def save_job(self, job: Job) -> None:
        """
        Persist a Job object to storage.

        The job is serialized using `model_dump` and stored atomically.

        Args:
            job (Job): Job instance to persist.
        """
        key = f"job:{job.job_id}"

        with shelve.open(self._path, writeback=False) as db:
            db[key] = job.model_dump()

    def load_job(self, job_id: str) -> Optional[Job]:
        """
        Load a Job object from storage.

        The retrieved data is validated by reconstructing
        a `Job` model instance.

        Args:
            job_id (str): Identifier of the job to load.

        Returns:
            Optional[Job]: Validated Job instance if found and valid,
                otherwise None.
        """
        key = f"job:{job_id}"

        with shelve.open(self._path, writeback=False) as db:
            raw = db.get(key)

            if raw is None:
                return None

            try:
                return Job(**raw)
            except Exception:
                # Corrupted or invalid stored data
                return None
            
    def update_job(self, job: Job) -> None:
        """
        Update an existing Job object in storage.

        This method overwrites the stored job data with the
        current state of the provided Job instance.

        Args:
            job (Job): Job instance to update.
        """
        key = f"job:{job.job_id}"

        with shelve.open(self._path, writeback=False) as db:
            if key not in db:
                raise RuntimeError(f"Job with id {job.job_id} does not exist.")
            db[key] = job.model_dump()

    # ------- Result storage -------

    def save_result(self, result: Result) -> None:
        """
        Persist a Result object to storage.

        Results are immutable and write-once. Attempting to overwrite
        an existing result raises an error.

        Args:
            result (Result): Result instance to persist.

        Raises:
            RuntimeError: If a result already exists for the job.
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

        The retrieved data is validated by reconstructing
        a `Result` model instance.

        Args:
            job_id (str): Identifier of the job whose result is requested.

        Returns:
            Optional[Result]: Validated Result instance if found and valid,
                otherwise None.
        """
        key = f"result:{job_id}"

        with shelve.open(self._path, writeback=False) as db:
            raw = db.get(key)

            if raw is None:
                return None

            try:
                return Result(**raw)
            except Exception:
                # Corrupted or invalid stored data
                return None
