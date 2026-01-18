"""
concurrency/processes.py

Process management utilities for concurrent job execution.

This module provides a ProcessWorkerPool for managing
process-based concurrency using a queue-based approach.
"""

from multiprocessing import Process, Queue
from typing import Callable, Any


class ProcessWorkerPool:
    """
    Process worker pool for executing tasks concurrently across processes.

    This pool manages a fixed number of worker processes that process
    tasks submitted via a multiprocessing queue. All arguments must be
    pickleable for inter-process communication.
    """

    def __init__(self, num_workers: int = 2):
        """
        Initialize the process worker pool.

        Args:
            num_workers (int): Number of worker processes to create.
        """
        self._task_queue = Queue()
        self._processes = []

        for i in range(num_workers):
            p = Process(
                target=self._worker,
                args=(self._task_queue,),
                daemon=True
            )
            p.start()
            self._processes.append(p)

    def submit(self, fn: Callable, *args):
        """
        Submit a task to the worker pool.

        Args:
            fn (Callable): Function to execute (must be pickleable).
            *args: Positional arguments for the function (must be pickleable).
        """
        # args must be pickleable
        self._task_queue.put((fn, args))

    @staticmethod
    def _worker(queue: Queue):
        """
        Worker process function that processes tasks from the queue.
        """
        while True:
            fn, args = queue.get()
            fn(*args)

    def shutdown(self):
        """
        Shutdown the worker pool and terminate all processes.
        """
        for p in self._processes:
            p.terminate()