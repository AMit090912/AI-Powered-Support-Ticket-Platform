# AI-Powered Support Ticket Platform — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-minded full-stack support ticket platform — FastAPI + MySQL backend with JWT auth, role-based access, Gemini-powered ticket triage (with rule-based fallback), search/filter/pagination, audit trail; plus a lean React+Vite+Tailwind SPA — fully unit/integration tested.

**Architecture:** Layered backend (routers → services → repositories → SQLAlchemy models) with AI triage behind a `TriageProvider` strategy interface, all dependencies injected via FastAPI deps. React SPA consumes the REST API with React Query. SOLID + KISS throughout.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, PyMySQL, pydantic-settings, python-jose (JWT), passlib[bcrypt], google-genai, pytest; React, Vite, Tailwind, React Router, React Query, axios.

> **Note on commits:** The user handles all git commits themselves. The `Commit` steps below are kept for logical grouping/checkpoints — the implementing agent should NOT run `git commit`. Treat each "Commit" step as a checkpoint marker only.

> **Note on TDD + DB:** Service unit tests mock repositories and use a stub `TriageProvider`. Integration tests use FastAPI `TestClient` against in-memory SQLite (SQLAlchemy keeps this portable). No running MySQL required for tests.

---

## File Structure

```
backend/
  .env.example
  .gitignore
  requirements.txt
  pytest.ini
  app/
    __init__.py
    main.py                 # app factory, CORS, error handlers, router wiring
    core/
      __init__.py
      config.py             # Settings (pydantic-settings, reads .env)
      database.py           # engine, SessionLocal, Base, get_db
      security.py           # bcrypt hashing, JWT encode/decode
    models/
      __init__.py
      enums.py              # Role, Status, Priority, Category, EventType
      user.py               # User ORM
      ticket.py             # Ticket ORM
      comment.py            # Comment ORM
      activity.py           # ActivityEvent ORM
    schemas/
      __init__.py
      auth.py               # Register, Login, Token, UserOut
      ticket.py             # TicketCreate, TicketUpdate, TicketOut, paginated
      comment.py            # CommentCreate, CommentOut
      activity.py           # ActivityOut
      analytics.py          # AnalyticsSummary
    repositories/
      __init__.py
      user_repo.py
      ticket_repo.py
      comment_repo.py
      activity_repo.py
    services/
      __init__.py
      auth_service.py
      ticket_service.py
      comment_service.py
      analytics_service.py
      exceptions.py         # domain exceptions (NotFound, Forbidden, Conflict)
    ai/
      __init__.py
      base.py               # TriageProvider ABC + TriageResult dataclass
      rule_based.py         # RuleBasedProvider (fallback + test double)
      gemini.py             # GeminiProvider
      factory.py            # get_triage_provider() — picks Gemini, falls back
    api/
      __init__.py
      deps.py               # get_db, current_user, require_agent, service factories
      routers/
        __init__.py
        auth.py
        tickets.py
        comments.py
        users.py
        analytics.py
  tests/
    __init__.py
    conftest.py             # test app, in-memory SQLite, client, auth helpers
    unit/
      test_security.py
      test_rule_based_provider.py
      test_gemini_provider.py
      test_ticket_service.py
    integration/
      test_auth_api.py
      test_tickets_api.py
      test_comments_api.py
      test_activity_api.py
      test_analytics_api.py
frontend/
  (Vite React app — see Phase F)
docs/...
README.md
ARCHITECTURE.md
```

---

# PHASE A — Backend Scaffolding

### Task A1: Project files, dependencies, config

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/app/core/__init__.py` (empty)
- Create: `backend/app/core/config.py`

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
SQLAlchemy==2.0.36
PyMySQL==1.1.1
pydantic==2.10.4
pydantic-settings==2.7.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
python-multipart==0.0.20
google-genai>=1.0.0
pytest==8.3.4
httpx==0.28.1
```

- [ ] **Step 2: Create `.env.example`**

```
# Database — local MySQL for dev. For prod set the hosted MySQL URL.
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/support_tickets
# JWT
JWT_SECRET=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
# AI
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
# CORS (comma-separated origins for the frontend)
CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
*.db
```

- [ ] **Step 4: Create `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
addopts = -q
```

- [ ] **Step 5: Create `app/core/config.py`**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Create venv and install** (one-time environment setup)

Run:
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# bash: source .venv/bin/activate
pip install -r requirements.txt
```
Expected: all packages install without error.

- [ ] **Step 7: Commit (checkpoint)** — `chore: backend scaffolding, deps, config`

---

### Task A2: Database engine, Base, session

**Files:**
- Create: `backend/app/core/database.py`

- [ ] **Step 1: Create `database.py`**

```python
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = get_settings().database_url
    # SQLite (tests) needs this flag; MySQL ignores it.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Commit (checkpoint)** — `feat: db engine and session`

---

# PHASE B — Models

### Task B1: Enums

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/enums.py`

- [ ] **Step 1: Create `enums.py`**

```python
import enum


class Role(str, enum.Enum):
    customer = "customer"
    agent = "agent"


class Status(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Category(str, enum.Enum):
    billing = "billing"
    technical = "technical"
    account_access = "account_access"
    feature_request = "feature_request"
    general = "general"


class EventType(str, enum.Enum):
    created = "created"
    status_changed = "status_changed"
    assigned = "assigned"
    priority_changed = "priority_changed"
    category_changed = "category_changed"
    commented = "commented"
```

- [ ] **Step 2: Populate `app/models/__init__.py`** so all models import via one module (needed for `Base.metadata.create_all`):

```python
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.activity import ActivityEvent

__all__ = ["User", "Ticket", "Comment", "ActivityEvent"]
```

- [ ] **Step 3: Commit (checkpoint)** — `feat: model enums`

---

### Task B2: ORM models

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/ticket.py`
- Create: `backend/app/models/comment.py`
- Create: `backend/app/models/activity.py`

- [ ] **Step 1: Create `user.py`**

```python
from datetime import datetime, timezone
from sqlalchemy import String, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Role


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.customer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
```

- [ ] **Step 2: Create `ticket.py`**

```python
from datetime import datetime, timezone
from sqlalchemy import String, Text, Enum as SAEnum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Status, Priority, Category


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[Status] = mapped_column(SAEnum(Status), default=Status.open, index=True)
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), default=Priority.medium, index=True)
    category: Mapped[Category] = mapped_column(SAEnum(Category), default=Category.general, index=True)
    suggested_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
```

- [ ] **Step 3: Create `comment.py`**

```python
from datetime import datetime, timezone
from sqlalchemy import Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    author = relationship("User")
```

- [ ] **Step 4: Create `activity.py`**

```python
from datetime import datetime, timezone
from sqlalchemy import String, Enum as SAEnum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EventType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType))
    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    actor = relationship("User")
```

- [ ] **Step 5: Commit (checkpoint)** — `feat: ORM models for user, ticket, comment, activity`

---

# PHASE C — Security (TDD)

### Task C1: Password hashing + JWT

**Files:**
- Create: `backend/app/core/security.py`
- Test: `backend/tests/__init__.py` (empty), `backend/tests/unit/test_security.py`

- [ ] **Step 1: Write the failing test** — `tests/unit/test_security.py`

```python
from datetime import timedelta
from app.core import security


def test_password_hash_roundtrip():
    hashed = security.hash_password("s3cret")
    assert hashed != "s3cret"
    assert security.verify_password("s3cret", hashed) is True
    assert security.verify_password("wrong", hashed) is False


def test_jwt_encode_decode_roundtrip():
    token = security.create_access_token({"sub": "5", "role": "agent"})
    payload = security.decode_token(token)
    assert payload["sub"] == "5"
    assert payload["role"] == "agent"


def test_decode_invalid_token_returns_none():
    assert security.decode_token("not.a.jwt") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_security.py -v`
Expected: FAIL (module `app.core.security` has no `hash_password`).

- [ ] **Step 3: Implement `security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/unit/test_security.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit (checkpoint)** — `feat: password hashing and JWT helpers`

---

# PHASE D — Schemas

### Task D1: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/__init__.py` (empty)
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/ticket.py`
- Create: `backend/app/schemas/comment.py`
- Create: `backend/app/schemas/activity.py`
- Create: `backend/app/schemas/analytics.py`

- [ ] **Step 1: Create `auth.py`**

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.enums import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)
    role: Role = Role.customer


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `comment.py`**

```python
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.auth import UserOut


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


class CommentOut(BaseModel):
    id: int
    ticket_id: int
    body: str
    created_at: datetime
    author: UserOut

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `activity.py`**

```python
from datetime import datetime
from pydantic import BaseModel
from app.models.enums import EventType
from app.schemas.auth import UserOut


class ActivityOut(BaseModel):
    id: int
    event_type: EventType
    old_value: str | None
    new_value: str | None
    created_at: datetime
    actor: UserOut | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create `ticket.py`**

```python
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.enums import Status, Priority, Category
from app.schemas.auth import UserOut


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)


class TicketUpdate(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    category: Category | None = None
    assigned_to_id: int | None = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    category: Category
    suggested_response: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UserOut
    assigned_to: UserOut | None

    model_config = {"from_attributes": True}


class PaginatedTickets(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 5: Create `analytics.py`**

```python
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
```

- [ ] **Step 6: Commit (checkpoint)** — `feat: pydantic schemas`

---

# PHASE E — AI Triage (TDD)

### Task E1: TriageProvider interface + RuleBasedProvider

**Files:**
- Create: `backend/app/ai/__init__.py` (empty)
- Create: `backend/app/ai/base.py`
- Create: `backend/app/ai/rule_based.py`
- Test: `backend/tests/unit/test_rule_based_provider.py`

- [ ] **Step 1: Write the failing test** — `tests/unit/test_rule_based_provider.py`

```python
from app.ai.rule_based import RuleBasedProvider
from app.models.enums import Category, Priority


def test_billing_keyword_maps_to_billing_category():
    r = RuleBasedProvider().triage("Refund for double charge", "I was billed twice on my invoice")
    assert r.category == Category.billing


def test_password_keyword_maps_to_account_access():
    r = RuleBasedProvider().triage("Cannot login", "I forgot my password and am locked out")
    assert r.category == Category.account_access


def test_critical_keyword_bumps_priority():
    r = RuleBasedProvider().triage("Production down", "Outage, system is completely broken urgent")
    assert r.priority == Priority.critical


def test_unknown_text_defaults_to_general_medium():
    r = RuleBasedProvider().triage("Hello", "Just saying hi")
    assert r.category == Category.general
    assert r.priority == Priority.medium


def test_suggested_response_is_nonempty():
    r = RuleBasedProvider().triage("Bug", "App crashes")
    assert isinstance(r.suggested_response, str) and len(r.suggested_response) > 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_rule_based_provider.py -v`
Expected: FAIL (no module `app.ai.rule_based`).

- [ ] **Step 3: Implement `base.py`**

```python
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
```

- [ ] **Step 4: Implement `rule_based.py`**

```python
from app.ai.base import TriageProvider, TriageResult
from app.models.enums import Category, Priority

_CATEGORY_KEYWORDS = {
    Category.billing: ["bill", "invoice", "charge", "refund", "payment", "subscription", "price"],
    Category.account_access: ["login", "log in", "password", "locked", "access", "2fa", "sign in"],
    Category.technical: ["error", "bug", "crash", "broken", "not working", "fail", "outage", "500"],
    Category.feature_request: ["feature", "request", "would be nice", "suggest", "add support", "enhancement"],
}

_PRIORITY_KEYWORDS = {
    Priority.critical: ["urgent", "critical", "outage", "down", "asap", "immediately", "data loss"],
    Priority.high: ["important", "blocked", "cannot", "can't", "broken", "error"],
    Priority.low: ["question", "wondering", "minor", "typo", "cosmetic", "whenever"],
}

_RESPONSES = {
    Category.billing: "Thanks for reaching out about your billing concern. We're reviewing your account and will follow up with details shortly.",
    Category.account_access: "Sorry you're having trouble accessing your account. We're looking into it and will help you regain access as soon as possible.",
    Category.technical: "Thanks for the report. Our technical team is investigating the issue and we'll keep you updated on progress.",
    Category.feature_request: "Thanks for the suggestion! We've logged your feature request and will share it with our product team.",
    Category.general: "Thanks for contacting support. We've received your request and will get back to you shortly.",
}


class RuleBasedProvider(TriageProvider):
    """Deterministic fallback used when Gemini is unavailable; also the test double."""

    def triage(self, title: str, description: str) -> TriageResult:
        text = f"{title} {description}".lower()
        category = self._match_category(text)
        priority = self._match_priority(text)
        return TriageResult(
            category=category,
            priority=priority,
            suggested_response=_RESPONSES[category],
        )

    def _match_category(self, text: str) -> Category:
        for category, keywords in _CATEGORY_KEYWORDS.items():
            if any(k in text for k in keywords):
                return category
        return Category.general

    def _match_priority(self, text: str) -> Priority:
        for priority, keywords in _PRIORITY_KEYWORDS.items():
            if any(k in text for k in keywords):
                return priority
        return Priority.medium
```

- [ ] **Step 5: Run to verify it passes**

Run: `pytest tests/unit/test_rule_based_provider.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit (checkpoint)** — `feat: triage interface + rule-based provider`

---

### Task E2: GeminiProvider + factory (TDD with mocked client)

**Files:**
- Create: `backend/app/ai/gemini.py`
- Create: `backend/app/ai/factory.py`
- Test: `backend/tests/unit/test_gemini_provider.py`

- [ ] **Step 1: Write the failing test** — `tests/unit/test_gemini_provider.py`

```python
from unittest.mock import MagicMock
from app.ai.gemini import GeminiProvider
from app.ai.factory import get_triage_provider
from app.ai.rule_based import RuleBasedProvider
from app.models.enums import Category, Priority


def _fake_client(text: str):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client


def test_gemini_parses_valid_json():
    client = _fake_client(
        '{"category": "billing", "priority": "high", "suggested_response": "We will help."}'
    )
    p = GeminiProvider(client=client, model="x")
    r = p.triage("Charge", "Double billed")
    assert r.category == Category.billing
    assert r.priority == Priority.high
    assert r.suggested_response == "We will help."


def test_gemini_strips_markdown_fences():
    client = _fake_client(
        '```json\n{"category":"technical","priority":"low","suggested_response":"ok"}\n```'
    )
    r = GeminiProvider(client=client, model="x").triage("t", "d")
    assert r.category == Category.technical


def test_gemini_invalid_json_raises():
    client = _fake_client("not json at all")
    p = GeminiProvider(client=client, model="x")
    try:
        p.triage("t", "d")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_factory_without_key_returns_rule_based():
    provider = get_triage_provider(api_key="", model="x")
    assert isinstance(provider, RuleBasedProvider)
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_gemini_provider.py -v`
Expected: FAIL (no module `app.ai.gemini`).

- [ ] **Step 3: Implement `gemini.py`**

```python
import json

from app.ai.base import TriageProvider, TriageResult
from app.models.enums import Category, Priority

_PROMPT = """You are a support-ticket triage assistant. Classify the ticket and draft a short, professional response.

Return ONLY a JSON object with exactly these keys:
- "category": one of ["billing","technical","account_access","feature_request","general"]
- "priority": one of ["low","medium","high","critical"]
- "suggested_response": a 1-3 sentence draft reply to the customer

Ticket title: {title}
Ticket description: {description}
"""


class GeminiProvider(TriageProvider):
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def triage(self, title: str, description: str) -> TriageResult:
        prompt = _PROMPT.format(title=title, description=description)
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        return self._parse(resp.text)

    def _parse(self, text: str) -> TriageResult:
        cleaned = self._strip_fences(text)
        try:
            data = json.loads(cleaned)
            return TriageResult(
                category=Category(data["category"]),
                priority=Priority(data["priority"]),
                suggested_response=str(data["suggested_response"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise ValueError(f"Gemini returned unparseable triage output: {exc}") from exc

    @staticmethod
    def _strip_fences(text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[1] if "\n" in t else t
            t = t.replace("```json", "").replace("```", "").strip()
        return t
```

- [ ] **Step 4: Implement `factory.py`**

```python
import logging

from app.ai.base import TriageProvider, TriageResult
from app.ai.rule_based import RuleBasedProvider
from app.ai.gemini import GeminiProvider

logger = logging.getLogger(__name__)


def get_triage_provider(api_key: str, model: str) -> TriageProvider:
    """Return Gemini when a key is configured, else the rule-based fallback."""
    if not api_key:
        logger.info("No GEMINI_API_KEY set; using RuleBasedProvider.")
        return RuleBasedProvider()
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return GeminiProvider(client=client, model=model)
    except Exception as exc:  # import or client init failure
        logger.warning("Gemini init failed (%s); using RuleBasedProvider.", exc)
        return RuleBasedProvider()


class SafeTriageProvider(TriageProvider):
    """Wraps a primary provider; on ANY failure falls back to rule-based."""

    def __init__(self, primary: TriageProvider):
        self._primary = primary
        self._fallback = RuleBasedProvider()

    def triage(self, title: str, description: str) -> TriageResult:
        try:
            return self._primary.triage(title, description)
        except Exception as exc:
            logger.warning("Triage primary failed (%s); falling back.", exc)
            return self._fallback.triage(title, description)
```

- [ ] **Step 5: Add a test for SafeTriageProvider fallback** — append to `test_gemini_provider.py`

```python
from app.ai.factory import SafeTriageProvider


class _Boom:
    def triage(self, title, description):
        raise RuntimeError("api down")


def test_safe_provider_falls_back_on_error():
    r = SafeTriageProvider(_Boom()).triage("urgent outage", "system down")
    assert r.priority == Priority.critical  # came from rule-based fallback
```

- [ ] **Step 6: Run to verify all pass**

Run: `pytest tests/unit/test_gemini_provider.py -v`
Expected: PASS (5 passed).

- [ ] **Step 7: Commit (checkpoint)** — `feat: gemini provider + safe fallback factory`

---

# PHASE F — Repositories

### Task F1: Repositories

**Files:**
- Create: `backend/app/repositories/__init__.py` (empty)
- Create: `backend/app/repositories/user_repo.py`
- Create: `backend/app/repositories/ticket_repo.py`
- Create: `backend/app/repositories/comment_repo.py`
- Create: `backend/app/repositories/activity_repo.py`

> Repositories are thin SQLAlchemy wrappers. They're exercised by integration tests (Phase I); no separate unit tests (they have no logic to mock).

- [ ] **Step 1: Create `user_repo.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.enums import Role


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list_agents(self) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role == Role.agent)))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

- [ ] **Step 2: Create `ticket_repo.py`**

```python
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.enums import Status, Priority, Category


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, ticket_id: int) -> Ticket | None:
        return self.db.get(Ticket, ticket_id)

    def create(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def save(self, ticket: Ticket) -> Ticket:
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def search(
        self,
        *,
        owner_id: int | None = None,
        q: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        category: Category | None = None,
        assignee_id: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Ticket], int]:
        stmt = select(Ticket)
        if owner_id is not None:
            stmt = stmt.where(Ticket.created_by_id == owner_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))
        if status is not None:
            stmt = stmt.where(Ticket.status == status)
        if priority is not None:
            stmt = stmt.where(Ticket.priority == priority)
        if category is not None:
            stmt = stmt.where(Ticket.category == category)
        if assignee_id is not None:
            stmt = stmt.where(Ticket.assigned_to_id == assignee_id)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self.db.scalars(
            stmt.order_by(Ticket.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)
```

- [ ] **Step 3: Create `comment_repo.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_for_ticket(self, ticket_id: int) -> list[Comment]:
        return list(
            self.db.scalars(
                select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.created_at)
            )
        )
```

- [ ] **Step 4: Create `activity_repo.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.models.enums import EventType


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        ticket_id: int,
        actor_id: int | None,
        event_type: EventType,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            ticket_id=ticket_id,
            actor_id=actor_id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_for_ticket(self, ticket_id: int) -> list[ActivityEvent]:
        return list(
            self.db.scalars(
                select(ActivityEvent)
                .where(ActivityEvent.ticket_id == ticket_id)
                .order_by(ActivityEvent.created_at)
            )
        )
```

- [ ] **Step 5: Commit (checkpoint)** — `feat: repositories`

---

# PHASE G — Services (TDD)

### Task G1: Domain exceptions

**Files:**
- Create: `backend/app/services/__init__.py` (empty)
- Create: `backend/app/services/exceptions.py`

- [ ] **Step 1: Create `exceptions.py`**

```python
class DomainError(Exception):
    """Base for domain errors."""


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ConflictError(DomainError):
    pass
```

- [ ] **Step 2: Commit (checkpoint)** — `feat: domain exceptions`

---

### Task G2: AuthService (TDD, mocked repo)

**Files:**
- Create: `backend/app/services/auth_service.py`
- Test: covered indirectly + via integration; add a focused unit test in `tests/unit/test_ticket_service.py`'s sibling is not needed. Add `tests/unit/test_auth_service.py`.

- [ ] **Step 1: Write the failing test** — `tests/unit/test_auth_service.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_auth_service.py -v`
Expected: FAIL (no module `app.services.auth_service`).

- [ ] **Step 3: Implement `auth_service.py`**

```python
from app.core import security
from app.models.user import User
from app.models.enums import Role
from app.repositories.user_repo import UserRepository
from app.services.exceptions import ConflictError, NotFoundError


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    def register(self, email: str, password: str, full_name: str, role: Role) -> User:
        if self.users.get_by_email(email):
            raise ConflictError("Email already registered")
        user = User(
            email=email,
            hashed_password=security.hash_password(password),
            full_name=full_name,
            role=role,
        )
        return self.users.create(user)

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not user or not security.verify_password(password, user.hashed_password):
            raise NotFoundError("Invalid email or password")
        return user

    def issue_token(self, user: User) -> str:
        return security.create_access_token({"sub": str(user.id), "role": user.role.value})
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/unit/test_auth_service.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit (checkpoint)** — `feat: auth service`

---

### Task G3: TicketService (TDD, mocked repos + stub provider)

**Files:**
- Create: `backend/app/services/ticket_service.py`
- Test: `backend/tests/unit/test_ticket_service.py`

- [ ] **Step 1: Write the failing test** — `tests/unit/test_ticket_service.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_ticket_service.py -v`
Expected: FAIL (no module `app.services.ticket_service`).

- [ ] **Step 3: Implement `ticket_service.py`**

```python
from app.ai.base import TriageProvider
from app.models.ticket import Ticket
from app.models.user import User
from app.models.enums import Role, Status, Priority, Category, EventType
from app.repositories.ticket_repo import TicketRepository
from app.repositories.activity_repo import ActivityRepository
from app.repositories.user_repo import UserRepository
from app.services.exceptions import ForbiddenError, NotFoundError

_AGENT_ONLY_FIELDS = {"status", "priority", "category", "assigned_to_id"}


class TicketService:
    def __init__(
        self,
        tickets: TicketRepository,
        activity: ActivityRepository,
        users: UserRepository,
        triage: TriageProvider,
    ):
        self.tickets = tickets
        self.activity = activity
        self.users = users
        self.triage = triage

    def create_ticket(self, creator: User, title: str, description: str) -> Ticket:
        result = self.triage.triage(title, description)
        ticket = Ticket(
            title=title,
            description=description,
            status=Status.open,
            priority=result.priority,
            category=result.category,
            suggested_response=result.suggested_response,
            created_by_id=creator.id,
        )
        ticket = self.tickets.create(ticket)
        self.activity.log(
            ticket_id=ticket.id, actor_id=creator.id, event_type=EventType.created
        )
        return ticket

    def get_ticket(self, user: User, ticket_id: int) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        self._assert_can_view(user, ticket)
        return ticket

    def list_tickets(self, user: User, **filters) -> tuple[list[Ticket], int]:
        # Customers are scoped to their own tickets.
        if user.role == Role.customer:
            filters["owner_id"] = user.id
        return self.tickets.search(**filters)

    def update_ticket(self, user: User, ticket_id: int, changes: dict) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        provided = {k: v for k, v in changes.items() if v is not None}
        if provided and user.role != Role.agent:
            raise ForbiddenError("Only agents can update tickets")

        if "status" in provided and provided["status"] != ticket.status:
            old = ticket.status.value
            ticket.status = provided["status"]
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.status_changed,
                              old_value=old, new_value=ticket.status.value)
        if "priority" in provided and provided["priority"] != ticket.priority:
            old = ticket.priority.value
            ticket.priority = provided["priority"]
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.priority_changed,
                              old_value=old, new_value=ticket.priority.value)
        if "category" in provided and provided["category"] != ticket.category:
            old = ticket.category.value
            ticket.category = provided["category"]
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.category_changed,
                              old_value=old, new_value=ticket.category.value)
        if "assigned_to_id" in provided and provided["assigned_to_id"] != ticket.assigned_to_id:
            assignee = self.users.get(provided["assigned_to_id"])
            if not assignee or assignee.role != Role.agent:
                raise NotFoundError("Assignee must be an existing agent")
            ticket.assigned_to_id = assignee.id
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.assigned,
                              new_value=assignee.full_name)
        return self.tickets.save(ticket)

    def _assert_can_view(self, user: User, ticket: Ticket) -> None:
        if user.role == Role.agent:
            return
        if ticket.created_by_id != user.id:
            raise ForbiddenError("You can only view your own tickets")
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/unit/test_ticket_service.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit (checkpoint)** — `feat: ticket service with RBAC + activity logging`

---

### Task G4: CommentService (TDD)

**Files:**
- Create: `backend/app/services/comment_service.py`
- Test: add to `tests/unit/test_ticket_service.py` a new file `tests/unit/test_comment_service.py`

- [ ] **Step 1: Write the failing test** — `tests/unit/test_comment_service.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_comment_service.py -v`
Expected: FAIL (no module `app.services.comment_service`).

- [ ] **Step 3: Implement `comment_service.py`**

```python
from app.models.comment import Comment
from app.models.user import User
from app.models.enums import Role, EventType
from app.repositories.ticket_repo import TicketRepository
from app.repositories.comment_repo import CommentRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.exceptions import ForbiddenError, NotFoundError


class CommentService:
    def __init__(
        self,
        tickets: TicketRepository,
        comments: CommentRepository,
        activity: ActivityRepository,
    ):
        self.tickets = tickets
        self.comments = comments
        self.activity = activity

    def add_comment(self, user: User, ticket_id: int, body: str) -> Comment:
        ticket = self._get_accessible(user, ticket_id)
        comment = self.comments.create(
            Comment(ticket_id=ticket.id, author_id=user.id, body=body)
        )
        self.activity.log(
            ticket_id=ticket.id, actor_id=user.id, event_type=EventType.commented
        )
        return comment

    def list_comments(self, user: User, ticket_id: int) -> list[Comment]:
        self._get_accessible(user, ticket_id)
        return self.comments.list_for_ticket(ticket_id)

    def _get_accessible(self, user: User, ticket_id: int):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if user.role != Role.agent and ticket.created_by_id != user.id:
            raise ForbiddenError("You can only access your own tickets")
        return ticket
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/unit/test_comment_service.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit (checkpoint)** — `feat: comment service`

---

### Task G5: AnalyticsService (TDD)

**Files:**
- Create: `backend/app/services/analytics_service.py`
- Test: `backend/tests/unit/test_analytics_service.py`

- [ ] **Step 1: Write the failing test** — `tests/unit/test_analytics_service.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/test_analytics_service.py -v`
Expected: FAIL (no module).

- [ ] **Step 3: Implement `analytics_service.py`**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/unit/test_analytics_service.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit (checkpoint)** — `feat: analytics service`

---

# PHASE H — API Layer

### Task H1: Dependencies (deps.py)

**Files:**
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/api/routers/__init__.py` (empty)
- Create: `backend/app/api/deps.py`

- [ ] **Step 1: Create `deps.py`**

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core import security
from app.models.user import User
from app.models.enums import Role
from app.repositories.user_repo import UserRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.comment_repo import CommentRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.auth_service import AuthService
from app.services.ticket_service import TicketService
from app.services.comment_service import CommentService
from app.services.analytics_service import AnalyticsService
from app.ai.factory import get_triage_provider, SafeTriageProvider

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbDep) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = security.decode_token(token)
    if not payload or "sub" not in payload:
        raise cred_exc
    user = UserRepository(db).get(int(payload["sub"]))
    if not user:
        raise cred_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_agent(user: CurrentUser) -> User:
    if user.role != Role.agent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent role required")
    return user


AgentUser = Annotated[User, Depends(require_agent)]


# --- service factories ---
def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(UserRepository(db))


def get_ticket_service(db: DbDep) -> TicketService:
    settings = get_settings()
    provider = SafeTriageProvider(
        get_triage_provider(settings.gemini_api_key, settings.gemini_model)
    )
    return TicketService(
        tickets=TicketRepository(db),
        activity=ActivityRepository(db),
        users=UserRepository(db),
        triage=provider,
    )


def get_comment_service(db: DbDep) -> CommentService:
    return CommentService(
        tickets=TicketRepository(db),
        comments=CommentRepository(db),
        activity=ActivityRepository(db),
    )


def get_analytics_service(db: DbDep) -> AnalyticsService:
    return AnalyticsService(TicketRepository(db))
```

- [ ] **Step 2: Commit (checkpoint)** — `feat: API dependencies and service factories`

---

### Task H2: Auth router

**Files:**
- Create: `backend/app/api/routers/auth.py`

- [ ] **Step 1: Create `auth.py`**

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service, CurrentUser
from app.services.auth_service import AuthService
from app.services.exceptions import ConflictError, NotFoundError
from app.schemas.auth import RegisterRequest, LoginRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
AuthDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, svc: AuthDep):
    try:
        return svc.register(payload.email, payload.password, payload.full_name, payload.role)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, svc: AuthDep):
    try:
        user = svc.authenticate(payload.email, payload.password)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return Token(access_token=svc.issue_token(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
```

> Note: `/login` accepts JSON (`LoginRequest`). The `OAuth2PasswordBearer` is only used to read the bearer token on protected routes; we don't require form-encoded login. The Swagger "Authorize" button still works because tokens are bearer.

- [ ] **Step 2: Commit (checkpoint)** — `feat: auth router`

---

### Task H3: Tickets router

**Files:**
- Create: `backend/app/api/routers/tickets.py`

- [ ] **Step 1: Create `tickets.py`**

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_ticket_service, CurrentUser
from app.services.ticket_service import TicketService
from app.services.exceptions import NotFoundError, ForbiddenError
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketOut, PaginatedTickets
from app.models.enums import Status, Priority, Category

router = APIRouter(prefix="/tickets", tags=["tickets"])
SvcDep = Annotated[TicketService, Depends(get_ticket_service)]


def _raise(e: Exception):
    if isinstance(e, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if isinstance(e, ForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    raise e


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, user: CurrentUser, svc: SvcDep):
    return svc.create_ticket(user, payload.title, payload.description)


@router.get("", response_model=PaginatedTickets)
def list_tickets(
    user: CurrentUser,
    svc: SvcDep,
    q: str | None = None,
    status_: Status | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    category: Category | None = None,
    assignee_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    items, total = svc.list_tickets(
        user, q=q, status=status_, priority=priority, category=category,
        assignee_id=assignee_id, page=page, page_size=page_size,
    )
    return PaginatedTickets(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, user: CurrentUser, svc: SvcDep):
    try:
        return svc.get_ticket(user, ticket_id)
    except (NotFoundError, ForbiddenError) as e:
        _raise(e)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, user: CurrentUser, svc: SvcDep):
    try:
        return svc.update_ticket(user, ticket_id, payload.model_dump(exclude_unset=True))
    except (NotFoundError, ForbiddenError) as e:
        _raise(e)
```

- [ ] **Step 2: Commit (checkpoint)** — `feat: tickets router`

---

### Task H4: Comments, Users, Analytics routers

**Files:**
- Create: `backend/app/api/routers/comments.py`
- Create: `backend/app/api/routers/users.py`
- Create: `backend/app/api/routers/analytics.py`

- [ ] **Step 1: Create `comments.py`**

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_comment_service, CurrentUser
from app.services.comment_service import CommentService
from app.services.exceptions import NotFoundError, ForbiddenError
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/tickets", tags=["comments"])
SvcDep = Annotated[CommentService, Depends(get_comment_service)]


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(ticket_id: int, payload: CommentCreate, user: CurrentUser, svc: SvcDep):
    try:
        return svc.add_comment(user, ticket_id, payload.body)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(ticket_id: int, user: CurrentUser, svc: SvcDep):
    try:
        return svc.list_comments(user, ticket_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
```

- [ ] **Step 2: Create `users.py`** (agents list + activity endpoint lives here for ticket access)

```python
from typing import Annotated
from fastapi import APIRouter, Depends

from app.api.deps import AgentUser, DbDep, CurrentUser, get_ticket_service
from app.repositories.user_repo import UserRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.ticket_service import TicketService
from app.schemas.auth import UserOut
from app.schemas.activity import ActivityOut

router = APIRouter(tags=["users"])


@router.get("/users/agents", response_model=list[UserOut])
def list_agents(_: AgentUser, db: DbDep):
    return UserRepository(db).list_agents()


@router.get("/tickets/{ticket_id}/activity", response_model=list[ActivityOut])
def ticket_activity(
    ticket_id: int,
    user: CurrentUser,
    db: DbDep,
    svc: Annotated[TicketService, Depends(get_ticket_service)],
):
    # Reuse ticket access check, then return the activity log.
    svc.get_ticket(user, ticket_id)  # raises 403/404 via router? -> handled globally
    return ActivityRepository(db).list_for_ticket(ticket_id)
```

> Domain exceptions raised here are converted to HTTP by the global handler added in Task H5.

- [ ] **Step 3: Create `analytics.py`**

```python
from typing import Annotated
from fastapi import APIRouter, Depends

from app.api.deps import AgentUser, get_analytics_service
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(_: AgentUser, svc: Annotated[AnalyticsService, Depends(get_analytics_service)]):
    return svc.summary()
```

- [ ] **Step 4: Commit (checkpoint)** — `feat: comments, users, analytics routers`

---

### Task H5: App factory + global error handlers

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: Create `main.py`**

```python
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.services.exceptions import NotFoundError, ForbiddenError, ConflictError
from app.api.routers import auth, tickets, comments, users, analytics

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI Support Ticket Platform", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tables (assignment scale; production would use Alembic migrations).
    Base.metadata.create_all(bind=engine)

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_: Request, exc: ForbiddenError):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(tickets.router)
    app.include_router(comments.router)
    app.include_router(users.router)
    app.include_router(analytics.router)
    return app


app = create_app()
```

- [ ] **Step 2: Run the app to smoke-test**

Run: `uvicorn app.main:app --reload` (then open `/docs`)
Expected: server boots, Swagger UI lists all routes. Stop with Ctrl+C.

- [ ] **Step 3: Commit (checkpoint)** — `feat: app factory, CORS, global error handlers`

---

# PHASE I — Integration Tests

### Task I1: Test fixtures (conftest)

**Files:**
- Create: `backend/tests/__init__.py` (empty, if not already)
- Create: `backend/tests/unit/__init__.py` (empty)
- Create: `backend/tests/integration/__init__.py` (empty)
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `conftest.py`**

```python
import os
# Force a hermetic in-memory DB BEFORE importing app modules (engine is built at import time).
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("GEMINI_API_KEY", "")  # ensure rule-based fallback in tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
get_settings.cache_clear()  # drop any cached settings so the env override above takes effect

from app.core.database import Base, get_db
import app.models  # noqa: F401
from app.main import create_app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    app = create_app()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _register(client, email, password, full_name, role):
    return client.post("/auth/register", json={
        "email": email, "password": password, "full_name": full_name, "role": role,
    })


def _login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest.fixture()
def customer_token(client):
    _register(client, "cust@x.com", "secret1", "Cust", "customer")
    return _login(client, "cust@x.com", "secret1")


@pytest.fixture()
def agent_token(client):
    _register(client, "agent@x.com", "secret1", "Agent", "agent")
    return _login(client, "agent@x.com", "secret1")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
```

> The `create_app()` call runs `Base.metadata.create_all` against the real engine too; harmless for SQLite tests because the route DB is overridden to the in-memory session. To keep tests hermetic we rely on `dependency_overrides[get_db]`.

- [ ] **Step 2: Commit (checkpoint)** — `test: integration fixtures`

---

### Task I2: Auth API tests

**Files:**
- Create: `backend/tests/integration/test_auth_api.py`

- [ ] **Step 1: Write the tests**

```python
from tests.conftest import auth


def test_register_returns_201_and_user(client):
    r = client.post("/auth/register", json={
        "email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@x.com"
    assert "hashed_password" not in r.json()


def test_duplicate_email_returns_409(client):
    body = {"email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"}
    client.post("/auth/register", json=body)
    r = client.post("/auth/register", json=body)
    assert r.status_code == 409


def test_login_returns_token(client):
    client.post("/auth/register", json={
        "email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"})
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "secret1"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password_401(client):
    client.post("/auth/register", json={
        "email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"})
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, customer_token):
    r = client.get("/auth/me", headers=auth(customer_token))
    assert r.status_code == 200
    assert r.json()["role"] == "customer"
```

- [ ] **Step 2: Run**

Run: `pytest tests/integration/test_auth_api.py -v`
Expected: PASS (6 passed).

- [ ] **Step 3: Commit (checkpoint)** — `test: auth API`

---

### Task I3: Tickets API tests (create/triage, RBAC, search, filter, pagination)

**Files:**
- Create: `backend/tests/integration/test_tickets_api.py`

- [ ] **Step 1: Write the tests**

```python
from tests.conftest import auth


def _create(client, token, title="Cannot login", desc="I forgot my password, locked out"):
    return client.post("/tickets", json={"title": title, "description": desc}, headers=auth(token))


def test_create_ticket_runs_triage(client, customer_token):
    r = _create(client, customer_token)
    assert r.status_code == 201
    body = r.json()
    # rule-based fallback (no GEMINI key in tests) -> account_access
    assert body["category"] == "account_access"
    assert body["status"] == "open"
    assert body["suggested_response"]


def test_customer_only_sees_own_tickets(client, customer_token, agent_token):
    _create(client, customer_token, "Mine", "x")
    # agent creates one as agent (still created_by agent)
    client.post("/tickets", json={"title": "AgentTicket", "description": "y"}, headers=auth(agent_token))
    r = client.get("/tickets", headers=auth(customer_token))
    titles = [t["title"] for t in r.json()["items"]]
    assert "Mine" in titles
    assert "AgentTicket" not in titles


def test_agent_sees_all_tickets(client, customer_token, agent_token):
    _create(client, customer_token, "CustTicket", "x")
    r = client.get("/tickets", headers=auth(agent_token))
    assert r.json()["total"] >= 1


def test_search_by_title(client, customer_token):
    _create(client, customer_token, "Billing refund please", "charge twice")
    _create(client, customer_token, "App crash", "it broke")
    r = client.get("/tickets?q=refund", headers=auth(customer_token))
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "Billing refund please"


def test_filter_by_status(client, customer_token, agent_token):
    cr = _create(client, customer_token, "ToResolve", "x")
    tid = cr.json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=auth(agent_token))
    r = client.get("/tickets?status=resolved", headers=auth(agent_token))
    assert all(t["status"] == "resolved" for t in r.json()["items"])
    assert r.json()["total"] >= 1


def test_pagination(client, customer_token):
    for i in range(3):
        _create(client, customer_token, f"T{i}", "x")
    r = client.get("/tickets?page=1&page_size=2", headers=auth(customer_token))
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] == 3


def test_customer_cannot_patch_ticket(client, customer_token):
    tid = _create(client, customer_token).json()["id"]
    r = client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=auth(customer_token))
    assert r.status_code == 403


def test_agent_can_assign_ticket(client, customer_token, agent_token):
    tid = _create(client, customer_token).json()["id"]
    # find the agent's id via /users/agents
    agents = client.get("/users/agents", headers=auth(agent_token)).json()
    agent_id = agents[0]["id"]
    r = client.patch(f"/tickets/{tid}", json={"assigned_to_id": agent_id}, headers=auth(agent_token))
    assert r.status_code == 200
    assert r.json()["assigned_to"]["id"] == agent_id


def test_customer_cannot_view_others_ticket(client, customer_token, agent_token):
    # agent creates a ticket; customer tries to read it
    tid = client.post("/tickets", json={"title": "secret", "description": "z"},
                      headers=auth(agent_token)).json()["id"]
    r = client.get(f"/tickets/{tid}", headers=auth(customer_token))
    assert r.status_code == 403


def test_get_missing_ticket_404(client, agent_token):
    assert client.get("/tickets/9999", headers=auth(agent_token)).status_code == 404
```

- [ ] **Step 2: Run**

Run: `pytest tests/integration/test_tickets_api.py -v`
Expected: PASS (10 passed).

- [ ] **Step 3: Commit (checkpoint)** — `test: tickets API (triage, RBAC, search, filter, pagination)`

---

### Task I4: Comments + Activity + Analytics API tests

**Files:**
- Create: `backend/tests/integration/test_comments_api.py`
- Create: `backend/tests/integration/test_activity_api.py`
- Create: `backend/tests/integration/test_analytics_api.py`

- [ ] **Step 1: Write `test_comments_api.py`**

```python
from tests.conftest import auth


def _ticket(client, token):
    return client.post("/tickets", json={"title": "t", "description": "d"}, headers=auth(token)).json()["id"]


def test_owner_can_add_and_list_comments(client, customer_token):
    tid = _ticket(client, customer_token)
    r = client.post(f"/tickets/{tid}/comments", json={"body": "hello"}, headers=auth(customer_token))
    assert r.status_code == 201
    lst = client.get(f"/tickets/{tid}/comments", headers=auth(customer_token))
    assert len(lst.json()) == 1
    assert lst.json()[0]["body"] == "hello"
    assert lst.json()[0]["author"]["email"] == "cust@x.com"


def test_agent_can_comment_on_any_ticket(client, customer_token, agent_token):
    tid = _ticket(client, customer_token)
    r = client.post(f"/tickets/{tid}/comments", json={"body": "agent here"}, headers=auth(agent_token))
    assert r.status_code == 201


def test_other_customer_cannot_comment(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "a", "description": "b"},
                      headers=auth(agent_token)).json()["id"]
    r = client.post(f"/tickets/{tid}/comments", json={"body": "x"}, headers=auth(customer_token))
    assert r.status_code == 403


def test_empty_comment_rejected(client, customer_token):
    tid = _ticket(client, customer_token)
    r = client.post(f"/tickets/{tid}/comments", json={"body": ""}, headers=auth(customer_token))
    assert r.status_code == 422
```

- [ ] **Step 2: Write `test_activity_api.py`**

```python
from tests.conftest import auth


def test_activity_logs_created_and_status_change(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "t", "description": "d"},
                      headers=auth(customer_token)).json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=auth(agent_token))
    r = client.get(f"/tickets/{tid}/activity", headers=auth(customer_token))
    types = [e["event_type"] for e in r.json()]
    assert "created" in types
    assert "status_changed" in types


def test_activity_access_controlled(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "t", "description": "d"},
                      headers=auth(agent_token)).json()["id"]
    r = client.get(f"/tickets/{tid}/activity", headers=auth(customer_token))
    assert r.status_code == 403
```

- [ ] **Step 3: Write `test_analytics_api.py`**

```python
from tests.conftest import auth


def test_analytics_requires_agent(client, customer_token):
    assert client.get("/analytics/summary", headers=auth(customer_token)).status_code == 403


def test_analytics_summary_counts(client, customer_token, agent_token):
    for i in range(2):
        client.post("/tickets", json={"title": f"t{i}", "description": "d"}, headers=auth(customer_token))
    r = client.get("/analytics/summary", headers=auth(agent_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert "by_category" in body and "by_priority" in body
```

- [ ] **Step 4: Run the whole backend suite**

Run: `pytest -v`
Expected: ALL tests pass (unit + integration).

- [ ] **Step 5: Commit (checkpoint)** — `test: comments, activity, analytics API`

---

### Task I5: Seed script (optional dev helper)

**Files:**
- Create: `backend/seed.py`

- [ ] **Step 1: Create `seed.py`**

```python
"""Seed the configured database with a demo agent, customer, and tickets."""
from app.core.database import SessionLocal, Base, engine
import app.models  # noqa: F401
from app.repositories.user_repo import UserRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.auth_service import AuthService
from app.services.ticket_service import TicketService
from app.ai.rule_based import RuleBasedProvider
from app.models.enums import Role


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        auth = AuthService(UserRepository(db))
        for email, name, role in [
            ("agent@demo.com", "Demo Agent", Role.agent),
            ("customer@demo.com", "Demo Customer", Role.customer),
        ]:
            if not UserRepository(db).get_by_email(email):
                auth.register(email, "password123", name, role)
        customer = UserRepository(db).get_by_email("customer@demo.com")
        svc = TicketService(TicketRepository(db), ActivityRepository(db),
                            UserRepository(db), RuleBasedProvider())
        for title, desc in [
            ("Double charged on invoice", "I was billed twice this month, need a refund."),
            ("Cannot log in", "Forgot password and locked out of my account."),
            ("App crashes on upload", "The app crashes every time I upload a file. Urgent."),
        ]:
            svc.create_ticket(customer, title, desc)
        print("Seed complete. Login: agent@demo.com / customer@demo.com (password123)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Commit (checkpoint)** — `chore: dev seed script`

---

# PHASE J — Frontend (React + Vite + Tailwind)

> Frontend is intentionally lean. Each task lists exact files. Tests are light (the assignment de-prioritizes frontend); focus on working UI with loading/error/empty states. Run `npm run dev` after Task J6 to verify against the running backend.

### Task J1: Scaffold Vite app + Tailwind + deps

**Files:**
- Create: `frontend/` (Vite React app)

- [ ] **Step 1: Scaffold**

Run:
```bash
cd frontend  # from repo root; create if missing
npm create vite@latest . -- --template react
npm install
npm install react-router-dom @tanstack/react-query axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 2: Configure Tailwind** — `frontend/tailwind.config.js`

```js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 3: Replace `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Create `frontend/.env.example`**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 5: Commit (checkpoint)** — `chore: frontend scaffold + tailwind`

---

### Task J2: API client + auth context

**Files:**
- Create: `frontend/src/lib/api.js`
- Create: `frontend/src/lib/auth.jsx`

- [ ] **Step 1: Create `src/lib/api.js`**

```js
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
```

- [ ] **Step 2: Create `src/lib/auth.jsx`**

```jsx
import { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { setLoading(false); return; }
    api.get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", r.data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
    return me.data;
  };

  const register = async (payload) => {
    await api.post("/auth/register", payload);
    return login(payload.email, payload.password);
  };

  const logout = () => { localStorage.removeItem("token"); setUser(null); };

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
```

- [ ] **Step 3: Commit (checkpoint)** — `feat: frontend api client + auth context`

---

### Task J3: App shell, routing, protected routes

**Files:**
- Modify: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/components/Layout.jsx`
- Create: `frontend/src/components/ProtectedRoute.jsx`
- Create: `frontend/src/components/ui.jsx` (small shared UI: Spinner, Badge, EmptyState, ErrorBox)

- [ ] **Step 1: Replace `src/main.jsx`**

```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./lib/auth";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
```

- [ ] **Step 2: Create `src/components/ui.jsx`**

```jsx
export function Spinner() {
  return <div className="animate-spin h-6 w-6 border-2 border-gray-300 border-t-blue-600 rounded-full" />;
}

export function ErrorBox({ message }) {
  return <div className="bg-red-50 text-red-700 px-4 py-2 rounded text-sm">{message}</div>;
}

export function EmptyState({ children }) {
  return <div className="text-gray-500 text-center py-12">{children}</div>;
}

const COLORS = {
  open: "bg-blue-100 text-blue-800", in_progress: "bg-yellow-100 text-yellow-800",
  resolved: "bg-green-100 text-green-800", closed: "bg-gray-200 text-gray-700",
  low: "bg-gray-100 text-gray-700", medium: "bg-blue-100 text-blue-800",
  high: "bg-orange-100 text-orange-800", critical: "bg-red-100 text-red-800",
};

export function Badge({ value }) {
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${COLORS[value] || "bg-gray-100 text-gray-700"}`}>{value?.replace("_", " ")}</span>;
}
```

- [ ] **Step 3: Create `src/components/ProtectedRoute.jsx`**

```jsx
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Spinner } from "./ui";

export default function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex justify-center p-12"><Spinner /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return children;
}
```

- [ ] **Step 4: Create `src/components/Layout.jsx`**

```jsx
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold text-gray-900">🎫 Support Desk</Link>
          <div className="flex items-center gap-4 text-sm">
            {user && <span className="text-gray-500">{user.full_name} · {user.role}</span>}
            {user && <button onClick={() => { logout(); nav("/login"); }} className="text-blue-600">Logout</button>}
          </div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 5: Create `src/App.jsx`**

```jsx
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import CustomerDashboard from "./pages/CustomerDashboard";
import AgentDashboard from "./pages/AgentDashboard";
import TicketDetail from "./pages/TicketDetail";

function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "agent" ? "/agent" : "/dashboard"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<Home />} />
      <Route path="/dashboard" element={<ProtectedRoute role="customer"><Layout><CustomerDashboard /></Layout></ProtectedRoute>} />
      <Route path="/agent" element={<ProtectedRoute role="agent"><Layout><AgentDashboard /></Layout></ProtectedRoute>} />
      <Route path="/tickets/:id" element={<ProtectedRoute><Layout><TicketDetail /></Layout></ProtectedRoute>} />
    </Routes>
  );
}
```

- [ ] **Step 6: Commit (checkpoint)** — `feat: app shell, routing, protected routes`

---

### Task J4: Auth pages (Login, Register)

**Files:**
- Create: `frontend/src/pages/Login.jsx`
- Create: `frontend/src/pages/Register.jsx`

- [ ] **Step 1: Create `src/pages/Login.jsx`**

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ErrorBox } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const user = await login(email, password);
      nav(user.role === "agent" ? "/agent" : "/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <form onSubmit={submit} className="bg-white p-8 rounded-lg shadow-sm w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Sign in</h1>
        {error && <ErrorBox message={error} />}
        <input className="w-full border rounded px-3 py-2" type="email" placeholder="Email"
               value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full border rounded px-3 py-2" type="password" placeholder="Password"
               value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button disabled={loading} className="w-full bg-blue-600 text-white rounded py-2 disabled:opacity-50">
          {loading ? "Signing in..." : "Sign in"}
        </button>
        <p className="text-sm text-gray-500">No account? <Link to="/register" className="text-blue-600">Register</Link></p>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Create `src/pages/Register.jsx`**

```jsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ErrorBox } from "../components/ui";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "customer" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const user = await register(form);
      nav(user.role === "agent" ? "/agent" : "/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <form onSubmit={submit} className="bg-white p-8 rounded-lg shadow-sm w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold">Create account</h1>
        {error && <ErrorBox message={error} />}
        <input className="w-full border rounded px-3 py-2" placeholder="Full name"
               value={form.full_name} onChange={set("full_name")} required />
        <input className="w-full border rounded px-3 py-2" type="email" placeholder="Email"
               value={form.email} onChange={set("email")} required />
        <input className="w-full border rounded px-3 py-2" type="password" placeholder="Password (min 6)"
               value={form.password} onChange={set("password")} required minLength={6} />
        <select className="w-full border rounded px-3 py-2" value={form.role} onChange={set("role")}>
          <option value="customer">Customer</option>
          <option value="agent">Support Agent</option>
        </select>
        <button disabled={loading} className="w-full bg-blue-600 text-white rounded py-2 disabled:opacity-50">
          {loading ? "Creating..." : "Create account"}
        </button>
        <p className="text-sm text-gray-500">Have an account? <Link to="/login" className="text-blue-600">Sign in</Link></p>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: Commit (checkpoint)** — `feat: login + register pages`

---

### Task J5: Shared ticket hooks + TicketList/Filters components

**Files:**
- Create: `frontend/src/lib/tickets.js` (React Query hooks)
- Create: `frontend/src/components/TicketTable.jsx`
- Create: `frontend/src/components/Filters.jsx`
- Create: `frontend/src/components/Pagination.jsx`

- [ ] **Step 1: Create `src/lib/tickets.js`**

```js
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "./api";

export function useTickets(params) {
  return useQuery({
    queryKey: ["tickets", params],
    queryFn: async () => {
      const { data } = await api.get("/tickets", { params });
      return data;
    },
    keepPreviousData: true,
  });
}

export function useTicket(id) {
  return useQuery({
    queryKey: ["ticket", id],
    queryFn: async () => (await api.get(`/tickets/${id}`)).data,
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload) => (await api.post("/tickets", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tickets"] }),
  });
}

export function useUpdateTicket(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (changes) => (await api.patch(`/tickets/${id}`, changes)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["activity", id] });
    },
  });
}

export function useComments(id) {
  return useQuery({
    queryKey: ["comments", id],
    queryFn: async () => (await api.get(`/tickets/${id}/comments`)).data,
  });
}

export function useAddComment(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`/tickets/${id}/comments`, { body })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["comments", id] });
      qc.invalidateQueries({ queryKey: ["activity", id] });
    },
  });
}

export function useActivity(id) {
  return useQuery({
    queryKey: ["activity", id],
    queryFn: async () => (await api.get(`/tickets/${id}/activity`)).data,
  });
}

export function useAgents(enabled) {
  return useQuery({
    queryKey: ["agents"],
    queryFn: async () => (await api.get("/users/agents")).data,
    enabled,
  });
}
```

- [ ] **Step 2: Create `src/components/TicketTable.jsx`**

```jsx
import { Link } from "react-router-dom";
import { Badge, EmptyState } from "./ui";

export default function TicketTable({ tickets }) {
  if (!tickets.length) return <EmptyState>No tickets found.</EmptyState>;
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-500 text-left">
          <tr>
            <th className="px-4 py-2">Title</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Priority</th>
            <th className="px-4 py-2">Category</th>
            <th className="px-4 py-2">Assignee</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((t) => (
            <tr key={t.id} className="border-t hover:bg-gray-50">
              <td className="px-4 py-2">
                <Link to={`/tickets/${t.id}`} className="text-blue-600 font-medium">{t.title}</Link>
              </td>
              <td className="px-4 py-2"><Badge value={t.status} /></td>
              <td className="px-4 py-2"><Badge value={t.priority} /></td>
              <td className="px-4 py-2 text-gray-600">{t.category.replace("_", " ")}</td>
              <td className="px-4 py-2 text-gray-600">{t.assigned_to?.full_name || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Create `src/components/Filters.jsx`**

```jsx
const STATUS = ["", "open", "in_progress", "resolved", "closed"];
const PRIORITY = ["", "low", "medium", "high", "critical"];
const CATEGORY = ["", "billing", "technical", "account_access", "feature_request", "general"];

export default function Filters({ value, onChange }) {
  const set = (k) => (e) => onChange({ ...value, [k]: e.target.value, page: 1 });
  const sel = "border rounded px-2 py-1.5 text-sm";
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      <input className={sel + " flex-1 min-w-[180px]"} placeholder="Search title or description…"
             value={value.q || ""} onChange={set("q")} />
      <select className={sel} value={value.status || ""} onChange={set("status")}>
        {STATUS.map((s) => <option key={s} value={s}>{s ? s.replace("_", " ") : "All statuses"}</option>)}
      </select>
      <select className={sel} value={value.priority || ""} onChange={set("priority")}>
        {PRIORITY.map((s) => <option key={s} value={s}>{s || "All priorities"}</option>)}
      </select>
      <select className={sel} value={value.category || ""} onChange={set("category")}>
        {CATEGORY.map((s) => <option key={s} value={s}>{s ? s.replace("_", " ") : "All categories"}</option>)}
      </select>
    </div>
  );
}
```

- [ ] **Step 4: Create `src/components/Pagination.jsx`**

```jsx
export default function Pagination({ page, pageSize, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
      <span>{total} ticket{total === 1 ? "" : "s"}</span>
      <div className="flex gap-2">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)}
                className="px-3 py-1 border rounded disabled:opacity-40">Prev</button>
        <span className="px-2 py-1">Page {page} / {pages}</span>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)}
                className="px-3 py-1 border rounded disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit (checkpoint)** — `feat: ticket hooks, table, filters, pagination`

---

### Task J6: Customer Dashboard + Agent Dashboard

**Files:**
- Create: `frontend/src/pages/CustomerDashboard.jsx`
- Create: `frontend/src/pages/AgentDashboard.jsx`

- [ ] **Step 1: Create `src/pages/CustomerDashboard.jsx`**

```jsx
import { useState } from "react";
import { useTickets, useCreateTicket } from "../lib/tickets";
import TicketTable from "../components/TicketTable";
import Pagination from "../components/Pagination";
import { Spinner, ErrorBox } from "../components/ui";

export default function CustomerDashboard() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useTickets({ page, page_size: 10 });
  const create = useCreateTicket();
  const [form, setForm] = useState({ title: "", description: "" });
  const [open, setOpen] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    await create.mutateAsync(form);
    setForm({ title: "", description: "" });
    setOpen(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">My Tickets</h1>
        <button onClick={() => setOpen(!open)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">
          {open ? "Cancel" : "New Ticket"}
        </button>
      </div>

      {open && (
        <form onSubmit={submit} className="bg-white p-4 rounded-lg shadow-sm mb-4 space-y-3">
          {create.isError && <ErrorBox message={create.error?.response?.data?.detail || "Failed to create"} />}
          <input className="w-full border rounded px-3 py-2" placeholder="Title" required
                 value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <textarea className="w-full border rounded px-3 py-2" placeholder="Describe your issue…" rows={4} required
                    value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <button disabled={create.isPending} className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50">
            {create.isPending ? "Submitting…" : "Submit ticket"}
          </button>
          <p className="text-xs text-gray-400">AI will auto-assign a category & priority.</p>
        </form>
      )}

      {isLoading ? <div className="flex justify-center p-12"><Spinner /></div>
        : isError ? <ErrorBox message="Failed to load tickets" />
        : <>
            <TicketTable tickets={data.items} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
          </>}
    </div>
  );
}
```

- [ ] **Step 2: Create `src/pages/AgentDashboard.jsx`**

```jsx
import { useState } from "react";
import { useTickets } from "../lib/tickets";
import api from "../lib/api";
import { useQuery } from "@tanstack/react-query";
import TicketTable from "../components/TicketTable";
import Filters from "../components/Filters";
import Pagination from "../components/Pagination";
import { Spinner, ErrorBox } from "../components/ui";

function AnalyticsBar() {
  const { data } = useQuery({ queryKey: ["analytics"], queryFn: async () => (await api.get("/analytics/summary")).data });
  if (!data) return null;
  const card = "bg-white rounded-lg shadow-sm px-4 py-3 flex-1 text-center";
  return (
    <div className="flex gap-3 mb-4">
      <div className={card}><div className="text-2xl font-semibold">{data.open}</div><div className="text-xs text-gray-500">Open</div></div>
      <div className={card}><div className="text-2xl font-semibold">{data.in_progress}</div><div className="text-xs text-gray-500">In progress</div></div>
      <div className={card}><div className="text-2xl font-semibold">{data.resolved}</div><div className="text-xs text-gray-500">Resolved</div></div>
      <div className={card}><div className="text-2xl font-semibold">{data.avg_resolution_hours ?? "—"}</div><div className="text-xs text-gray-500">Avg hrs to resolve</div></div>
    </div>
  );
}

export default function AgentDashboard() {
  const [filters, setFilters] = useState({ page: 1 });
  const params = { ...filters, page_size: 10 };
  Object.keys(params).forEach((k) => params[k] === "" && delete params[k]);
  const { data, isLoading, isError } = useTickets(params);

  return (
    <div>
      <h1 className="text-lg font-semibold mb-4">All Tickets</h1>
      <AnalyticsBar />
      <Filters value={filters} onChange={setFilters} />
      {isLoading ? <div className="flex justify-center p-12"><Spinner /></div>
        : isError ? <ErrorBox message="Failed to load tickets" />
        : <>
            <TicketTable tickets={data.items} />
            <Pagination page={filters.page || 1} pageSize={data.page_size} total={data.total}
                        onPage={(p) => setFilters({ ...filters, page: p })} />
          </>}
    </div>
  );
}
```

- [ ] **Step 3: Verify against running backend**

Run backend (`uvicorn app.main:app --reload`) + `python seed.py`, then `npm run dev`. Log in as `agent@demo.com` / `password123` and `customer@demo.com` / `password123`. Confirm dashboards load, create works, filters/search/pagination work.

- [ ] **Step 4: Commit (checkpoint)** — `feat: customer + agent dashboards`

---

### Task J7: Ticket Detail (info, agent controls, comments, activity timeline)

**Files:**
- Create: `frontend/src/pages/TicketDetail.jsx`

- [ ] **Step 1: Create `src/pages/TicketDetail.jsx`**

```jsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../lib/auth";
import {
  useTicket, useUpdateTicket, useComments, useAddComment, useActivity, useAgents,
} from "../lib/tickets";
import { Badge, Spinner, ErrorBox, EmptyState } from "../components/ui";

const STATUS = ["open", "in_progress", "resolved", "closed"];
const PRIORITY = ["low", "medium", "high", "critical"];

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAgent = user?.role === "agent";
  const { data: ticket, isLoading, isError } = useTicket(id);
  const update = useUpdateTicket(id);
  const { data: comments } = useComments(id);
  const addComment = useAddComment(id);
  const { data: activity } = useActivity(id);
  const { data: agents } = useAgents(isAgent);
  const [body, setBody] = useState("");

  if (isLoading) return <div className="flex justify-center p-12"><Spinner /></div>;
  if (isError) return <ErrorBox message="Failed to load ticket" />;

  const submitComment = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    await addComment.mutateAsync(body);
    setBody("");
  };

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <div className="md:col-span-2 space-y-6">
        <div className="bg-white rounded-lg shadow-sm p-5">
          <div className="flex items-center gap-2 mb-2">
            <Badge value={ticket.status} /><Badge value={ticket.priority} />
            <span className="text-xs text-gray-500">{ticket.category.replace("_", " ")}</span>
          </div>
          <h1 className="text-xl font-semibold">{ticket.title}</h1>
          <p className="text-gray-600 mt-2 whitespace-pre-wrap">{ticket.description}</p>
          <p className="text-xs text-gray-400 mt-3">Opened by {ticket.created_by.full_name}</p>
        </div>

        {isAgent && ticket.suggested_response && (
          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
            <p className="text-xs font-medium text-indigo-700 mb-1">🤖 AI suggested response</p>
            <p className="text-sm text-indigo-900">{ticket.suggested_response}</p>
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm p-5">
          <h2 className="font-medium mb-3">Comments</h2>
          <div className="space-y-3">
            {comments?.length ? comments.map((c) => (
              <div key={c.id} className="border-b pb-2">
                <p className="text-sm">{c.body}</p>
                <p className="text-xs text-gray-400">{c.author.full_name} · {new Date(c.created_at).toLocaleString()}</p>
              </div>
            )) : <EmptyState>No comments yet.</EmptyState>}
          </div>
          <form onSubmit={submitComment} className="mt-4 flex gap-2">
            <input className="flex-1 border rounded px-3 py-2 text-sm" placeholder="Add a comment…"
                   value={body} onChange={(e) => setBody(e.target.value)} />
            <button disabled={addComment.isPending} className="bg-blue-600 text-white px-4 rounded text-sm disabled:opacity-50">Send</button>
          </form>
        </div>
      </div>

      <div className="space-y-6">
        {isAgent && (
          <div className="bg-white rounded-lg shadow-sm p-5 space-y-3">
            <h2 className="font-medium">Manage</h2>
            <label className="block text-xs text-gray-500">Status
              <select className="w-full border rounded px-2 py-1.5 mt-1" value={ticket.status}
                      onChange={(e) => update.mutate({ status: e.target.value })}>
                {STATUS.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
              </select>
            </label>
            <label className="block text-xs text-gray-500">Priority
              <select className="w-full border rounded px-2 py-1.5 mt-1" value={ticket.priority}
                      onChange={(e) => update.mutate({ priority: e.target.value })}>
                {PRIORITY.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label className="block text-xs text-gray-500">Assignee
              <select className="w-full border rounded px-2 py-1.5 mt-1" value={ticket.assigned_to?.id || ""}
                      onChange={(e) => update.mutate({ assigned_to_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Unassigned</option>
                {agents?.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
              </select>
            </label>
            {update.isError && <ErrorBox message="Update failed" />}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm p-5">
          <h2 className="font-medium mb-3">Activity</h2>
          <ol className="space-y-2 text-sm text-gray-600">
            {activity?.length ? activity.map((e) => (
              <li key={e.id} className="flex gap-2">
                <span className="text-gray-300">•</span>
                <span>
                  <b>{e.event_type.replace("_", " ")}</b>
                  {e.old_value && <> from <i>{e.old_value}</i></>}
                  {e.new_value && <> to <i>{e.new_value}</i></>}
                  {e.actor && <> · {e.actor.full_name}</>}
                  <span className="block text-xs text-gray-400">{new Date(e.created_at).toLocaleString()}</span>
                </span>
              </li>
            )) : <EmptyState>No activity.</EmptyState>}
          </ol>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser** — open a ticket as agent, change status/priority/assignee, add a comment, watch the activity timeline update.

- [ ] **Step 3: Commit (checkpoint)** — `feat: ticket detail page with agent controls, comments, activity`

---

# PHASE K — Docs & Deployment

### Task K1: README.md

**Files:**
- Create: `README.md` (repo root)

- [ ] **Step 1: Write `README.md`** covering:
  - Project summary + features
  - Tech stack
  - **Prerequisites:** Python 3.11+, Node 18+, MySQL running locally
  - **Backend setup:** create MySQL DB (`CREATE DATABASE support_tickets;`), `cd backend`, `python -m venv .venv`, activate, `pip install -r requirements.txt`, copy `.env.example` → `.env` and fill `DATABASE_URL`, `JWT_SECRET`, `GEMINI_API_KEY`, run `python seed.py`, run `uvicorn app.main:app --reload`. Note `/docs` for Swagger.
  - **Environment variables table:** every var from `.env.example` with description.
  - **Frontend setup:** `cd frontend`, `npm install`, copy `.env.example` → `.env` (`VITE_API_URL`), `npm run dev`.
  - **Running tests:** `cd backend && pytest -v`.
  - **Deployment:** frontend → Vercel (set `VITE_API_URL` to deployed backend URL); backend → Render/Railway (set env vars, point `DATABASE_URL` at hosted MySQL, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
  - **Demo credentials** (from seed).
  - **Assumptions made** (e.g., role chosen at registration; tables auto-created via `create_all`; single suggested response generated at creation time).

- [ ] **Step 2: Commit (checkpoint)** — `docs: README`

---

### Task K2: ARCHITECTURE.md

**Files:**
- Create: `ARCHITECTURE.md` (repo root)

- [ ] **Step 1: Write `ARCHITECTURE.md`** with these sections (content drawn from the design spec):
  - **System Design:** overall topology (React SPA ↔ FastAPI ↔ MySQL); diagram (ASCII ok). Frontend architecture (Vite SPA, React Query, route-guarded by role). Backend architecture (layered: routers → services → repositories → models; deps injection).
  - **Database Design:** entity table, relationships (User 1—N Ticket as creator/assignee, Ticket 1—N Comment, Ticket 1—N ActivityEvent), and design decisions (enums in DB, audit table for activity history, `updated_at` used for resolution timing). **Document the MySQL-vs-SQLite-in-tests trade-off** and the deviation from the assignment's SQLite default.
  - **Authentication Strategy:** JWT bearer chosen; role in token; trade-offs (stateless, no server session store, can't revoke before expiry → mitigations: short expiry/rotation as future work). bcrypt for passwords.
  - **AI Integration:** Gemini (`gemini-2.0-flash`) via `google-genai`; `TriageProvider` strategy interface; prompting strategy (strict-JSON instruction, enum-constrained, parsed + validated); fallback handling (`SafeTriageProvider` wraps Gemini, catches all errors → `RuleBasedProvider`; no-key path uses rule-based directly). Why triage runs synchronously at creation (KISS) and the trade-off vs. async.
  - **SOLID/KISS notes:** brief mapping of each principle to the code.
  - **Future Improvements:** real-time (WebSockets/SSE), email/in-app notifications, SLA tracking/escalation, Alembic migrations, refresh-token rotation, full-text search, rate limiting, async triage queue, richer analytics, frontend tests (Vitest/RTL).

- [ ] **Step 2: Commit (checkpoint)** — `docs: ARCHITECTURE`

---

### Task K3: Deployment config

**Files:**
- Create: `backend/Procfile` (or `render.yaml`)
- Create: `frontend/vercel.json`

- [ ] **Step 1: Create `backend/Procfile`** (Railway/Render)

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 2: Create `frontend/vercel.json`** (SPA rewrite so client routes resolve)

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/" }]
}
```

- [ ] **Step 3: Deploy**
  - Backend: create Render/Railway service from `backend/`, add a hosted MySQL, set env vars (`DATABASE_URL`, `JWT_SECRET`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS=<vercel-url>`), deploy.
  - Frontend: import repo into Vercel, root `frontend/`, set `VITE_API_URL=<backend-url>`, deploy.
  - Smoke-test the live URLs; update README with the live links.

- [ ] **Step 4: Commit (checkpoint)** — `chore: deployment config + live URLs in README`

---

## Final Verification Checklist

- [ ] `cd backend && pytest -v` → all unit + integration tests pass.
- [ ] `uvicorn app.main:app --reload` boots; `/docs` shows all endpoints.
- [ ] `npm run dev` frontend connects; register/login works for both roles.
- [ ] Customer: create ticket → AI category/priority populated; sees only own tickets.
- [ ] Agent: sees all; search/filter/paginate; assign; change status/priority; sees AI suggested response.
- [ ] Comments + activity timeline update live.
- [ ] Analytics summary renders for agents, 403 for customers.
- [ ] README + ARCHITECTURE complete; live URLs added.
```
