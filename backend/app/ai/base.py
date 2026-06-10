from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import Category, Priority


@dataclass
class TriageResult:
    category: Category
    priority: Priority
    suggested_response: str


class TriageProvider(ABC):
    @abstractmethod
    def triage(self, title: str, description: str) -> TriageResult:
        """Classify a ticket and draft a suggested response."""
        raise NotImplementedError
