"""
core/scheduler.py

Priority-based job scheduler with aging.

This module provides a Scheduler implementation that manages job
execution order using:
- Priority-based scheduling
- Aging to prevent starvation
- Thread-safe access to the scheduling queue
"""

import time
import threading
import heapq
from dataclasses import dataclass, field
from typing import List, Optional

from models.job import Job, JobStatus


@dataclass(order=True)
class _ScheduledItems:
    """
    Internal wrapper for jobs stored in the scheduler priority queue.

    This class exists solely to control heap ordering behavior and
    should not be used outside the scheduler.

    Attributes:
        sort_index (int): Computed value used for heap ordering.
            Lower values are dequeued first.
        job (Job): The job instance being scheduled.
        base_priority (int): Original priority assigned to the job.
        submitted_at (float): UNIX timestamp when the job was submitted.
    """

    sort_index: int = field(init=False, repr=False)
    job: Job = field(compare=False)
    base_priority: int = field(compare=False)
    submitted_at: float = field(compare=False)

    def __post_init__(self) -> None:
        """
        Initialize heap sort index.

        The priority is negated to simulate max-heap behavior
        using Python's min-heap implementation.
        """
        self.sort_index = -self.base_priority


class Scheduler:
    """
    Priority-based scheduler with fairness via aging.

    This scheduler:
    - Orders jobs by priority
    - Gradually increases priority of waiting jobs (aging)
    - Is safe for concurrent access

    Jobs must be in the PENDING state before submission.
    """

    def __init__(self, aging_factor: float = 0.1):
        """
        Initialize the scheduler.

        Args:
            aging_factor (float): Multiplier applied to job wait time
                to increase effective priority.
        """
        self.aging_factor = aging_factor
        self._queue: List[_ScheduledItems] = []
        self._lock = threading.Lock()

    # -------- Public APIs ----------

    def submit(self, job: Job) -> None:
        """
        Submit a job to the scheduler.

        Only jobs with status PENDING may be submitted.

        Args:
            job (Job): Job instance to schedule.

        Raises:
            ValueError: If the job is not in PENDING state.
        """
        if job.status != JobStatus.PENDING:
            raise ValueError(
                "Only jobs with status 'pending' can be submitted to the scheduler."
            )

        scheduled_item = _ScheduledItems(
            job=job,
            base_priority=job.priority,
            submitted_at=time.time(),
        )

        with self._lock:
            heapq.heappush(self._queue, scheduled_item)

    def next_job(self) -> Optional[Job]:
        """
        Retrieve the next job to execute.

        The scheduler recalculates effective priorities using aging
        before selecting the next job.

        Returns:
            Optional[Job]: Next job to execute, or None if the
                scheduler queue is empty.
        """
        with self._lock:
            if not self._queue:
                return None

            current_time = time.time()

            # Update priorities using aging
            for item in self._queue:
                wait_time = current_time - item.submitted_at
                effective_priority = (
                    item.base_priority
                    + int(self.aging_factor * wait_time)
                )
                item.sort_index = -effective_priority

            heapq.heapify(self._queue)

            scheduled_item = heapq.heappop(self._queue)
            return scheduled_item.job

    def size(self) -> int:
        """
        Get the number of jobs currently queued.

        Returns:
            int: Number of jobs in the scheduler queue.
        """
        with self._lock:
            return len(self._queue)
