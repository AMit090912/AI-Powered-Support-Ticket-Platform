from unittest.mock import MagicMock
import pytest

from app.services.ticket_service import TicketService
from app.services.exceptions import ForbiddenError, NotFoundError
from app.ai.base import TriageResult
from app.models.ticket import Ticket
from app.models.user import User
from app.models.enums import Role, Status, Priority, Category


def _user(uid, role):
    u = User(email=f"{uid}@x.com", hashed_password="h", full_name="U", role=role)
    u.id = uid
    return u


def _ticket(tid=1, owner=1, **kw):
    t = Ticket(title="t", description="d", created_by_id=owner,
               status=Status.open, priority=Priority.medium, category=Category.general)
    t.id = tid
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def _stub_provider():
    p = MagicMock()
    p.triage.return_value = TriageResult(Category.billing, Priority.high, "draft")
    return p


def _service(tickets, activity, users=None, provider=None):
    return TicketService(
        tickets=tickets,
        activity=activity,
        users=users or MagicMock(),
        triage=provider or _stub_provider(),
    )


def test_create_runs_triage_and_logs_created():
    tickets = MagicMock(); tickets.create.side_effect = lambda t: t
    activity = MagicMock()
    svc = _service(tickets, activity)
    creator = _user(1, Role.customer)
    ticket = svc.create_ticket(creator, "Charge issue", "double billed")
    assert ticket.category == Category.billing
    assert ticket.priority == Priority.high
    assert ticket.suggested_response == "draft"
    activity.log.assert_called_once()


def test_customer_cannot_view_others_ticket():
    tickets = MagicMock(); tickets.get.return_value = _ticket(owner=2)
    svc = _service(tickets, MagicMock())
    with pytest.raises(ForbiddenError):
        svc.get_ticket(_user(1, Role.customer), 1)


def test_agent_can_view_any_ticket():
    tickets = MagicMock(); tickets.get.return_value = _ticket(owner=2)
    svc = _service(tickets, MagicMock())
    t = svc.get_ticket(_user(99, Role.agent), 1)
    assert t.id == 1


def test_get_missing_ticket_raises_notfound():
    tickets = MagicMock(); tickets.get.return_value = None
    svc = _service(tickets, MagicMock())
    with pytest.raises(NotFoundError):
        svc.get_ticket(_user(99, Role.agent), 123)


def test_customer_cannot_update_status():
    tickets = MagicMock(); tickets.get.return_value = _ticket(owner=1)
    svc = _service(tickets, MagicMock())
    with pytest.raises(ForbiddenError):
        svc.update_ticket(_user(1, Role.customer), 1, {"status": Status.resolved})


def test_agent_status_change_logs_activity():
    ticket = _ticket(owner=2, status=Status.open)
    tickets = MagicMock(); tickets.get.return_value = ticket; tickets.save.side_effect = lambda t: t
    activity = MagicMock()
    svc = _service(tickets, activity)
    svc.update_ticket(_user(9, Role.agent), 1, {"status": Status.in_progress})
    assert ticket.status == Status.in_progress
    activity.log.assert_called()  # status_changed logged


def test_agent_assignment_logs_assigned():
    ticket = _ticket(owner=2)
    tickets = MagicMock(); tickets.get.return_value = ticket; tickets.save.side_effect = lambda t: t
    users = MagicMock(); users.get.return_value = _user(5, Role.agent)
    activity = MagicMock()
    svc = TicketService(tickets=tickets, activity=activity, users=users, triage=_stub_provider())
    svc.update_ticket(_user(9, Role.agent), 1, {"assigned_to_id": 5})
    assert ticket.assigned_to_id == 5
    activity.log.assert_called()


def test_agent_can_unassign_ticket():
    ticket = _ticket(owner=2, assigned_to_id=5)
    tickets = MagicMock(); tickets.get.return_value = ticket; tickets.save.side_effect = lambda t: t
    activity = MagicMock()
    svc = TicketService(tickets=tickets, activity=activity, users=MagicMock(), triage=_stub_provider())
    svc.update_ticket(_user(9, Role.agent), 1, {"assigned_to_id": None})
    assert ticket.assigned_to_id is None
    activity.log.assert_called()  # assigned (Unassigned) logged
