"""
utils/cache.py

Cache utility functions for storing and retrieving data.

This module provides simple in-memory caching capabilities
to optimize performance by avoiding redundant computations.
"""

import time
import threading
from collections import OrderedDict
from typing import Any, Optional

class LRUCache:
    """
    Custom LRU (Least Recently Used) cache implementation.
    """

    def __init__(self, max_size: int = 128, ttl: int = 300):
        """
        Initialize the TTL cache.
        Args:
            max_size (int): Maximum number of items to store in the cache.
            ttl (int): Time-to-live for each cache item in seconds.
        """
        self.max_size = max_size
        self.ttl = ttl
        self._store = OrderedDict()
        self._lock = threading.Lock()

    def __get__(self, cls, instance, owner):
        """
        Create getter and setter for the cache.
        Args:
            cls: Class type.
            instance: Instance of the class.
            owner: Owner class.
        Returns:
            getter (Callable): Function to get an item from the cache.
            setter (Callable): Function to set an item in the cache.
        """
        def getter(self, key: Any) -> Optional[Any]:
            """
            Retrieve an item from the cache.
            Args:
                key (Any): Key of the item to retrieve.
            Returns:
                Optional[Any]: The cached value, or None if not found or expired.
            """
            with self._lock:
                if key not in self._store:
                    return None

                value, timestamp = self._store[key]

                # TTL check
                if time.time() - timestamp > self.ttl:
                    del self._store[key]
                    return None

                # Mark as recently used
                self._store.move_to_end(key)
                return value

        def setter(self, key: Any, value: Any) -> None:
            """
            Store an item in the cache.
            Args:
                key (Any): Key of the item to store.
                value (Any): Value to store in the cache.
            """
            with self._lock:
                self._store[key] = (value, time.time())
                self._store.move_to_end(key)

                # Evict LRU
                if len(self._store) > self.maxsize:
                    self._store.popitem(last=False)

        return getter, setter

    def __len__(self):
        with self._lock:
            return len(self._store)

    def clear(self):
        with self._lock:
            self._store.clear()