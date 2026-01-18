"""
storage/state.py

Persistent state management for jobs and results.

This module provides the `StateStore` class, which uses SQLite
to persist `Job` and `Result` objects. It acts as a trust boundary 
by validating all objects upon retrieval.
"""

import sqlite3
import json
import threading
from typing import Optional, List

from models.job import Job, JobStatus
from models.result import Result


class StateStore:
    """
    Durable storage for Job and Result objects using SQLite.

    This class is responsible for:
    - Persisting Job and Result data atomically
    - Validating objects on load to prevent propagation of corrupted data
    - Thread-safe concurrent access via locking

    All objects returned from this storage layer are guaranteed
    to be valid Pydantic models or None.
    """

    def __init__(self, path: str):
        """
        Initialize storage state.

        Args:
            path (str): Filesystem path for the SQLite database.
        """
        self._path = path
        self._lock = threading.Lock()  # Thread-safe access
        
        # Initialize database tables
        with self._lock:
            self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self._path, check_same_thread=False)
        try:
            cursor = conn.cursor()
            
            # Create jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            
            # Create results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    job_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def _get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self._path, check_same_thread=False)

    # ------- Job storage -------

    def save_job(self, job: Job) -> None:
        """
        Persist a Job object to storage.

        The job is serialized using `model_dump` and stored atomically.

        Args:
            job (Job): Job instance to persist.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                job_data = json.dumps(job.model_dump(), default=str)
                cursor.execute(
                    "INSERT OR REPLACE INTO jobs (job_id, data) VALUES (?, ?)",
                    (job.job_id, job_data)
                )
                conn.commit()
            finally:
                conn.close()

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
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data FROM jobs WHERE job_id = ?",
                    (job_id,)
                )
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                try:
                    raw = json.loads(row[0])
                    return Job(**raw)
                except Exception:
                    # Corrupted or invalid stored data
                    return None
            finally:
                conn.close()
            
    def update_job(self, job: Job) -> None:
        """
        Update an existing Job object in storage.

        This method overwrites the stored job data with the
        current state of the provided Job instance.

        Args:
            job (Job): Job instance to update.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Check if job exists
                cursor.execute(
                    "SELECT 1 FROM jobs WHERE job_id = ?",
                    (job.job_id,)
                )
                if cursor.fetchone() is None:
                    raise RuntimeError(f"Job with id {job.job_id} does not exist.")
                
                # Update job
                job_data = json.dumps(job.model_dump(), default=str)
                cursor.execute(
                    "UPDATE jobs SET data = ? WHERE job_id = ?",
                    (job_data, job.job_id)
                )
                conn.commit()
            finally:
                conn.close()

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
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                
                # Check if result already exists
                cursor.execute(
                    "SELECT 1 FROM results WHERE job_id = ?",
                    (result.job_id,)
                )
                if cursor.fetchone() is not None:
                    raise RuntimeError(
                        f"Result for job_id {result.job_id} already exists."
                    )
                
                # Insert result
                result_data = json.dumps(result.model_dump(), default=str)
                cursor.execute(
                    "INSERT INTO results (job_id, data) VALUES (?, ?)",
                    (result.job_id, result_data)
                )
                conn.commit()
            finally:
                conn.close()

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
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data FROM results WHERE job_id = ?",
                    (job_id,)
                )
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                try:
                    raw = json.loads(row[0])
                    return Result(**raw)
                except Exception:
                    # Corrupted or invalid stored data
                    return None
            finally:
                conn.close()

    # ------- Querying all jobs -------

    def get_all_jobs(self, status: Optional["JobStatus"] = None) -> list[Job]:
        """
        Retrieve all jobs from storage, optionally filtered by status.

        Args:
            status (Optional[JobStatus]): Filter jobs by status.

        Returns:
            list[Job]: List of all jobs matching the filter.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT data FROM jobs")
                rows = cursor.fetchall()
                
                jobs = []
                for row in rows:
                    try:
                        job_data = json.loads(row[0])
                        job = Job(**job_data)
                        if status is None or job.status == status:
                            jobs.append(job)
                    except Exception:
                        pass  # Skip invalid entries
                return jobs
            finally:
                conn.close()
