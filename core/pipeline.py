"""
core/pipeline.py

Pipeline management and orchestration.

This module defines the `Pipeline` class, which orchestrates:
- Job creation and submission
- Sequential and parallel job execution within a defined pipeline

It integrates with the `Engine` for job lifecycle management
and provides high-level methods for pipeline execution.
"""

from typing import Iterable, Callable, Any, Generator, List

class Pipeline:
    """
    Generator-based execution pipeline.

    This Pipeline:
    - Composes multiple stages into a sequential workflow
    - Yields intermediate results after each stage
    - Supports flexible input and output types for each stage
    """

    def __init__(self, stages: Iterable[Callable[[Any], Any]]):
        """
        Initialize the pipeline with a sequence of stages.

        Args:
            stages (Iterable[Callable[..., Any]]): Sequence of functions representing pipeline stages.
        """
        self._stages = stages

    def run(self, initial_input: Any) -> Generator[Any, None, None]:
        """
        Execute the pipeline stages sequentially.

        Each stage receives the output of the previous stage as input.

        Args:
            initial_input (Any): Input to the first stage of the pipeline.
        Yields:
            Any: Output from each stage of the pipeline.
        """
        data = initial_input
        for stage in self._stages:
            data = stage(data)
            yield data

        return data