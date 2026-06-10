from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    avg_resolution_hours: float | None
