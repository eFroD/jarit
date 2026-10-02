"""Per-run dependencies of the video agent."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from jarit.jobs.models import JobStatus


@dataclass
class ExtractionDeps:
    # Called by the tools when the job enters a new stage.
    report: Callable[[JobStatus], Awaitable[None]]
