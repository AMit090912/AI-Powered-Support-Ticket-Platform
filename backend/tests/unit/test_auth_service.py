from unittest.mock import MagicMock
import pytest

from app.services.auth_service import AuthService
from app.services.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.models.enums import Role
from app.core import security


def _user(**kw):
    defaults = dict(id=1, email="a@b.com", full_name="A", role=Role.customer,
                    hashed_password=security.hash_password("secret"))
    defaults.update(kw)
    u = User(**{k: v for k, v in defaults.items() if k != "id"})
    u.id = defaults["id"]
    return u


def test_register_rejects_duplicate_email():
    repo = MagicMock()
    repo.get_by_email.return_value = _user()
    svc = AuthService(repo)
    with pytest.raises(ConflictError):
        svc.register("a@b.com", "secret", "A", Role.customer)


def test_register_hashes_password_and_creates():
    repo = MagicMock()
    repo.get_by_email.return_value = None
    repo.create.side_effect = lambda u: u
    svc = AuthService(repo)
    user = svc.register("new@b.com", "secret", "New", Role.agent)
    assert user.hashed_password != "secret"
    assert user.role == Role.agent
    repo.create.assert_called_once()


def test_authenticate_wrong_password_raises():
    repo = MagicMock()
    repo.get_by_email.return_value = _user()
    svc = AuthService(repo)
    with pytest.raises(NotFoundError):
        svc.authenticate("a@b.com", "wrong")


def test_authenticate_success_returns_user():
    repo = MagicMock()
    repo.get_by_email.return_value = _user()
    svc = AuthService(repo)
    user = svc.authenticate("a@b.com", "secret")
    assert user.email == "a@b.com"
