"""
core/base_pipeline.py

Abstract base class for pipelines.

This module defines the `BasePipeline` abstract class,
which serves as:
- A blueprint for all pipeline implementations
- An integration point with the PluginRegistry for automatic registration
of pipeline classes by name.
"""

from abc import ABC, abstractmethod
from utils.registry import PluginRegistry


class BasePipeline(ABC, metaclass=PluginRegistry):
    """
    Abstract base class for all pipelines.

    This class enforces the implementation of the `stages` method,
    which should return a list of callables representing the pipeline stages.
    Each pipeline implementation must define a unique `name` attribute for registration.
    """

    name: str  # must be overridden

    @abstractmethod
    def stages(self):
        """
        Return a list of callables representing pipeline stages.
        """
        raise NotImplementedError
