# AI-Powered Support Ticket Platform — Design Spec

**Date:** 2026-06-09
**Status:** Approved

## 1. Purpose & Scope

A production-minded full-stack support ticket platform. Customers create and track
support tickets; support agents triage, assign, update, and resolve them. On creation,
an LLM auto-generates the ticket's **category**, **priority**, and a **suggested response**
draft for agents.

This is a Fullstack Engineer internship assignment. **The backend and its interaction with
the frontend is the primary focus.** The frontend is intentionally lean: simple, modern,
responsive — no heavy design work.

### Success criteria
- Customers and agents can authenticate (JWT) with role-based access.
- Full ticket lifecycle: create → triage → assign → status updates → comments → close.
- AI triage works against Gemini with a deterministic fallback.
- Search, filtering, and pagination on the ticket list.
- Clean layered backend following SOLID + KISS.
- Unit + integration tests for every feature/method.
- Deployable; documented in README.md and ARCHITECTURE.md.

## 2. Tech Stack & Topology

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend | Python FastAPI | Long-running server (deploy Render/Railway) |
| ORM | SQLAlchemy 2.x + PyMySQL | DB-agnostic; enables SQLite in tests |
| Database | MySQL | Local for dev; `DATABASE_URL` for prod |
| Auth | JWT (bearer) | Role encoded in token claims |
| AI | Google Gemini (`google-genai`) | Rule-based fallback provider |
| Frontend | React + Vite + Tailwind + React Query | SPA → Vercel |
| Python env | `venv` virtual environment | isolated deps via `requirements.txt` |
| Config | `.env` file via `pydantic-settings` | all env vars read from `.env` (with `.env.example` committed) |

**Deviation from assignment:** The assignment's tech-stack line specified SQLite; per
explicit instruction we use **MySQL** instead. SQLAlchemy keeps the code portable, which
also lets the test suite run against in-memory SQLite without a running MySQL. This
deviation and its trade-offs are documented in ARCHITECTURE.md.

**Topology:** React SPA on Vercel calls the FastAPI REST API (long-running server with a
real connection pool) which talks to MySQL. Vercel serverless was rejected for the backend
because a stateful API + MySQL pool fits a long-running server better.

## 3. Backend Architecture (layered, SOLID/KISS)

```
app/
  core/         config (pydantic-settings), security (JWT, bcrypt), dependencies
  models/       SQLAlchemy ORM: User, Ticket, Comment, ActivityEvent
  schemas/      Pydantic request/response DTOs
  repositories/ data access: UserRepository, TicketRepository, CommentRepository, ActivityRepository
  services/     business logic: AuthService, TicketService, CommentService, AnalyticsService
  ai/           TriageProvider (interface) -> GeminiProvider + RuleBasedProvider
  api/routers/  thin HTTP controllers: auth, tickets, comments, users, analytics
  api/deps.py   FastAPI dependency wiring (db session, current user, role guards)
  main.py       app factory, router registration, CORS, global error handlers
```

**SOLID application:**
- **SRP** — routers handle HTTP only; services hold business rules; repositories own
  persistence; schemas own (de)serialization/validation.
- **OCP / DIP** — AI triage sits behind a `TriageProvider` abstract interface (Strategy
  pattern). `GeminiProvider` is the default; `RuleBasedProvider` is both the production
  fallback and the test double. Adding/swapping a provider requires no service changes.
- **LSP** — both providers honor the same `triage(title, description) -> TriageResult` contract.
- **ISP** — narrow interfaces; repositories expose only the methods their service needs.
- **DIP** — services depend on repository/provider abstractions injected via FastAPI deps,
  not on concrete SQLAlchemy/Gemini classes. This is what makes services unit-testable with mocks.

**KISS:** no event bus, no CQRS, no microservices. One service, four tables, one synchronous
triage call with a fallback.

**Environment & config:**
- The backend runs inside a Python **`venv`** virtual environment; dependencies are pinned in
  `requirements.txt`. README documents `python -m venv .venv` + activation + install.
- **All** runtime configuration (DB `DATABASE_URL`, `JWT_SECRET`, `GEMINI_API_KEY`, token
  expiry, CORS origins) is read from a **`.env`** file via `pydantic-settings` `Settings`.
  A committed `.env.example` documents every variable; the real `.env` is git-ignored.

## 4. Data Model

### User
| field | type | notes |
|-------|------|-------|
| id | int PK | |
| email | varchar unique | login identity |
| hashed_password | varchar | bcrypt |
| full_name | varchar | |
| role | enum(`customer`,`agent`) | RBAC |
| created_at | datetime | |

### Ticket
| field | type | notes |
|-------|------|-------|
| id | int PK | |
| title | varchar | |
| description | text | |
| status | enum(`open`,`in_progress`,`resolved`,`closed`) | default `open` |
| priority | enum(`low`,`medium`,`high`,`critical`) | AI-set, agent-overridable |
| category | enum(`billing`,`technical`,`account_access`,`feature_request`,`general`) | AI-set |
| created_by_id | FK->User | the customer |
| assigned_to_id | FK->User nullable | the agent |
| suggested_response | text nullable | AI draft, agent-facing |
| created_at | datetime | |
| updated_at | datetime | auto-updated |

### Comment
| field | type | notes |
|-------|------|-------|
| id | int PK | |
| ticket_id | FK->Ticket | |
| author_id | FK->User | |
| body | text | |
| created_at | datetime | |

### ActivityEvent (audit trail / activity history)
| field | type | notes |
|-------|------|-------|
| id | int PK | |
| ticket_id | FK->Ticket | |
| actor_id | FK->User nullable | nullable for system events |
| event_type | enum(`created`,`status_changed`,`assigned`,`priority_changed`,`category_changed`,`commented`) | |
| old_value | varchar nullable | |
| new_value | varchar nullable | |
| created_at | datetime | |

**Relationships:** User 1—N Ticket (as creator), User 1—N Ticket (as assignee),
Ticket 1—N Comment, Ticket 1—N ActivityEvent.

**Access rules:** customers may read/act only on tickets where `created_by_id == self`.
Agents may read/act on all tickets. Enforced in the service layer + a role dependency.

## 5. AI Triage

On `POST /tickets`, `TicketService` calls the injected `TriageProvider`:

```
triage(title, description) -> TriageResult{ category, priority, suggested_response }
```

- **GeminiProvider**: sends a structured prompt instructing the model to return strict JSON
  with `category`, `priority`, `suggested_response`. Response parsed and **validated against
  the enums**; out-of-range values are coerced/rejected.
- **Fallback**: on missing API key, timeout, network error, or invalid/unparseable JSON, the
  service falls back to `RuleBasedProvider` — keyword matching maps text → category and
  priority, plus a templated suggested response. Triage failure never blocks ticket creation.

Agents can later override category/priority/status via `PATCH /tickets/:id`; each override is
recorded as an ActivityEvent.

## 6. API Surface (REST)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | public | create user (role chosen at register) |
| POST | `/auth/login` | public | returns JWT |
| GET | `/auth/me` | any | current user |
| POST | `/tickets` | customer/agent | create + AI triage |
| GET | `/tickets` | any | list: search `q`, filters `status/priority/category/assignee`, `page`/`page_size` |
| GET | `/tickets/:id` | owner/agent | detail |
| PATCH | `/tickets/:id` | agent (status/priority/category/assignment) | update; logs activity |
| POST | `/tickets/:id/comments` | owner/agent | add comment (logs activity) |
| GET | `/tickets/:id/comments` | owner/agent | list comments |
| GET | `/tickets/:id/activity` | owner/agent | activity timeline |
| GET | `/users/agents` | agent | assignee dropdown |
| GET | `/analytics/summary` | agent | open counts, by-category, avg resolution time |

**List semantics:** customers' `GET /tickets` is implicitly scoped to their own tickets;
agents see all and may use every filter. Response envelope: `{ items, total, page, page_size }`.

**Errors:** consistent JSON error shape `{ detail }`; 401 auth, 403 RBAC, 404 not found,
422 validation (FastAPI default), 400 domain errors.

## 7. Testing (pytest)

- **Unit tests** — services tested in isolation with **mocked repositories** and a **stub
  TriageProvider**. Covers business rules, RBAC decisions, activity logging, status/priority
  transitions, fallback selection logic.
- **Integration tests** — full API via FastAPI `TestClient` against **in-memory SQLite**
  (SQLAlchemy dialect-portable). Covers auth flow, JWT, ticket CRUD, search/filter/pagination,
  RBAC at the HTTP boundary, comments, activity endpoint.
- **AI provider tests** — `RuleBasedProvider` tested directly; `GeminiProvider` tested with a
  mocked client (success path + malformed-JSON → fallback path).
- **Trade-off documented:** tests use SQLite while prod uses MySQL. Acceptable because all DB
  access goes through SQLAlchemy with no raw MySQL-specific SQL. Noted in ARCHITECTURE.md.

## 8. Frontend (lean, modern)

- **Pages:** Login, Register, Customer Dashboard (my tickets + create form), Ticket Detail
  (info + comments + activity timeline), Agent Dashboard (all tickets + search + filters +
  assign + status update), light Analytics widget.
- **Infra:** React Router; a thin `apiClient` (fetch wrapper) with a JWT auth interceptor and
  token persistence; **React Query** for fetching with built-in loading/error/empty states;
  Tailwind for clean styling. Pagination controls on list views.
- **States:** explicit loading skeletons/spinners, empty states, and inline error handling
  for failed requests, validation errors (422 field mapping), and auth failures (redirect to login).

## 9. Bonus Features

**Included:** Audit trail / activity history (also required for the detail page) and a light
analytics summary endpoint + dashboard widget.

**Deferred (documented in ARCHITECTURE.md → Future Improvements):** real-time updates
(WebSockets/SSE), email/in-app notifications, automated SLA tracking/escalation.

## 10. Deliverables

1. Git repository
2. Live deployed URL (frontend Vercel, backend Render/Railway)
3. ARCHITECTURE.md (system/DB/auth/AI design + trade-offs + future work)
4. README.md (setup, env vars, local dev, deployment, assumptions)
