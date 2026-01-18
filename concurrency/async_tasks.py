"""
concurrency/async_tasks.py

Asynchronous task management utilities for concurrent job execution.

This module provides an AsyncTaskRunner for managing
asynchronous concurrency using asyncio queues.
"""

import asyncio
from typing import Callable, Any


class AsyncTaskRunner:
    """
    Asynchronous task runner for executing coroutines concurrently.

    This runner manages a queue of asynchronous tasks and processes
    them in a single event loop.
    """

    def __init__(self):
        """
        Initialize the async task runner.
        """
        self._queue = asyncio.Queue()

    async def submit(self, coro: Callable[..., Any], *args):
        """
        Submit a coroutine to the task queue.

        Args:
            coro: Coroutine function to execute.
            *args: Arguments for the coroutine.
        """
        await self._queue.put((coro, args))

    async def run(self):
        """
        Run the task processing loop.
        """
        while True:
            coro, args = await self._queue.get()
            await coro(*args)
            self._queue.task_done()