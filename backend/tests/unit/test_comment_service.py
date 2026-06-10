from unittest.mock import MagicMock
import pytest

from app.services.comment_service import CommentService
from app.services.exceptions import ForbiddenError, NotFoundError
from app.models.ticket import Ticket
from app.models.user import User
from app.models.comment import Comment
from app.models.enums import Role, Status, Priority, Category


def _user(uid, role):
    u = User(email=f"{uid}@x.com", hashed_password="h", full_name="U", role=role)
    u.id = uid
    return u


def _ticket(owner=1):
    t = Ticket(title="t", description="d", created_by_id=owner,
               status=Status.open, priority=Priority.low, category=Category.general)
    t.id = 1
    return t


def _svc(tickets, comments, activity):
    return CommentService(tickets=tickets, comments=comments, activity=activity)


def test_add_comment_on_missing_ticket_raises():
    tickets = MagicMock(); tickets.get.return_value = None
    svc = _svc(tickets, MagicMock(), MagicMock())
    with pytest.raises(NotFoundError):
        svc.add_comment(_user(1, Role.customer), 1, "hi")


def test_customer_cannot_comment_on_others_ticket():
    tickets = MagicMock(); tickets.get.return_value = _ticket(owner=2)
    svc = _svc(tickets, MagicMock(), MagicMock())
    with pytest.raises(ForbiddenError):
        svc.add_comment(_user(1, Role.customer), 1, "hi")


def test_owner_can_comment_and_activity_logged():
    tickets = MagicMock(); tickets.get.return_value = _ticket(owner=1)
    comments = MagicMock(); comments.create.side_effect = lambda c: c
    activity = MagicMock()
    svc = _svc(tickets, comments, activity)
    c = svc.add_comment(_user(1, Role.customer), 1, "hello")
    assert c.body == "hello"
    activity.log.assert_called_once()


def test_list_comments_checks_access():
    tickets = MagicMock(); tickets.get.return_value = _ticket(owner=2)
    svc = _svc(tickets, MagicMock(), MagicMock())
    with pytest.raises(ForbiddenError):
        svc.list_comments(_user(1, Role.customer), 1)
