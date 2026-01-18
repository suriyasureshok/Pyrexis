"""
utils/shutdown.py

Shutdown coordination utilities.

This module provides a ShutdownCoordinator for managing
graceful shutdown sequences across the system.
"""

import threading
import logging
from typing import Callable, List


class ShutdownCoordinator:
    """
    Coordinates graceful shutdown across the system.

    Allows registration of shutdown callbacks that are invoked
    when a shutdown signal is received.
    """

    def __init__(self):
        """
        Initialize the shutdown coordinator.
        """
        self._shutdown_event = threading.Event()
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()

    def register(self, callback: Callable[[], None]) -> None:
        """
        Register a shutdown callback.
        Args:
            callback (Callable[[], None]): Function to call on shutdown.
        """
        with self._lock:
            self._callbacks.append(callback)

    def initiate_shutdown(self, signum=None, frame=None):
        """
        Trigger shutdown sequence.
        Args:
            signum: Signal number (if applicable).
            frame: Current stack frame (if applicable).
        """
        if self._shutdown_event.is_set():
            return  # already shutting down

        logging.warning(f"Shutdown initiated (signal={signum})")
        self._shutdown_event.set()

        with self._lock:
            for callback in reversed(self._callbacks):
                try:
                    callback()
                except Exception as exc:
                    logging.error(f"Shutdown callback failed: {exc}")

    def should_shutdown(self) -> bool:
        """
        Check if shutdown has been initiated.
        Returns:
            bool: True if shutdown is in progress, False otherwise.
        """
        return self._shutdown_event.is_set()
