from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

from app.services.analytics_service import AnalyticsService
from app.models.ticket import Ticket
from app.models.enums import Status, Priority, Category


def _t(status, priority, category, created=None, updated=None):
    t = Ticket(title="t", description="d", created_by_id=1,
               status=status, priority=priority, category=category)
    t.created_at = created or datetime(2026, 1, 1, tzinfo=timezone.utc)
    t.updated_at = updated or t.created_at
    return t


def test_summary_counts_and_grouping():
    repo = MagicMock()
    repo.search.return_value = (
        [
            _t(Status.open, Priority.low, Category.billing),
            _t(Status.open, Priority.high, Category.technical),
            _t(Status.resolved, Priority.high, Category.billing,
               created=datetime(2026, 1, 1, tzinfo=timezone.utc),
               updated=datetime(2026, 1, 1, 2, tzinfo=timezone.utc)),
        ],
        3,
    )
    svc = AnalyticsService(repo)
    s = svc.summary()
    assert s.total == 3
    assert s.open == 2
    assert s.resolved == 1
    assert s.by_category["billing"] == 2
    assert s.by_priority["high"] == 2
    assert s.avg_resolution_hours == 2.0
