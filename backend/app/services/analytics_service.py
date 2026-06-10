from app.models.enums import Status, Priority, Category
from app.repositories.ticket_repo import TicketRepository
from app.schemas.analytics import AnalyticsSummary


class AnalyticsService:
    def __init__(self, tickets: TicketRepository):
        self.tickets = tickets

    def summary(self) -> AnalyticsSummary:
        # Pull all tickets (page_size large enough for the assignment's scale).
        items, total = self.tickets.search(page=1, page_size=100000)

        counts = {s: 0 for s in Status}
        by_category = {c.value: 0 for c in Category}
        by_priority = {p.value: 0 for p in Priority}
        resolution_hours: list[float] = []

        for t in items:
            counts[t.status] += 1
            by_category[t.category.value] += 1
            by_priority[t.priority.value] += 1
            if t.status in (Status.resolved, Status.closed) and t.created_at and t.updated_at:
                delta = (t.updated_at - t.created_at).total_seconds() / 3600.0
                resolution_hours.append(delta)

        avg = round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else None
        return AnalyticsSummary(
            total=total,
            open=counts[Status.open],
            in_progress=counts[Status.in_progress],
            resolved=counts[Status.resolved],
            closed=counts[Status.closed],
            by_category=by_category,
            by_priority=by_priority,
            avg_resolution_hours=avg,
        )
