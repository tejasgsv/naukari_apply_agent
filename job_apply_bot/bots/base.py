"""PlatformBot interface (stub)."""

from abc import ABC, abstractmethod
from typing import Dict, Iterable, Optional


class PlatformBot(ABC):
    @abstractmethod
    def search_jobs(self, role: str, filters: Dict) -> Iterable[object]:
        """Yield JobPosting objects (stub type: object)."""

    @abstractmethod
    def extract_job_details(self, job: object) -> object:
        """Return enriched JobPosting (e.g., full description)."""

    @abstractmethod
    def apply(self, job: object, application_plan: object, behavior: object) -> object:
        """Perform application steps and return ApplicationResult."""

