"""
concurrency/threads.py

Thread management utilities for concurrent job execution.

This module provides a ThreadWorkerPool for managing
thread-based concurrency using a queue-based approach.
"""

import threading
from queue import Queue
from typing import Callable, Any


class ThreadWorkerPool:
    """
    Thread worker pool for executing tasks concurrently.

    This pool manages a fixed number of worker threads that process
    tasks submitted via a thread-safe queue.
    """

    def __init__(self, num_workers: int = 4):
        """
        Initialize the thread worker pool.

        Args:
            num_workers (int): Number of worker threads to create.
        """
        self._queue = Queue()
        self._workers = []
        self._shutdown = threading.Event()

        for i in range(num_workers):
            t = threading.Thread(
                target=self._worker,
                name=f"thread-worker-{i}",
                daemon=True
            )
            t.start()
            self._workers.append(t)

    def submit(self, fn: Callable, *args, **kwargs):
        """
        Submit a task to the worker pool.

        Args:
            fn (Callable): Function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        self._queue.put((fn, args, kwargs))

    def _worker(self):
        """
        Worker thread function that processes tasks from the queue.
        """
        while not self._shutdown.is_set():
            try:
                fn, args, kwargs = self._queue.get(timeout=0.5)
                fn(*args, **kwargs)
                self._queue.task_done()
            except Exception:
                continue

    def shutdown(self):
        """
        Shutdown the worker pool and stop all threads.
        """
        self._shutdown.set()