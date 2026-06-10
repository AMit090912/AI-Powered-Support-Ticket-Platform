# Architecture

AI-powered support ticket platform. This document explains the system design, database
design, authentication strategy, AI integration, how SOLID/KISS shaped the code, and what
I would improve with more time.

---

## 1. System Design

### Overall topology

```
┌──────────────┐      HTTPS / JSON      ┌──────────────────────────┐        ┌──────────┐
│  React SPA   │ ─────────────────────► │   FastAPI backend         │ ─────► │  MySQL   │
│  (Vercel)    │ ◄───── JWT bearer ──── │  (Render / Railway)       │ ◄───── │          │
└──────────────┘                        │  routers→services→repos    │        └──────────┘
                                         │  + AI TriageProvider       │
                                         └───────────┬───────────────┘
                                                     │ (on ticket create)
                                                     ▼
                                            Google Gemini API
                                         (fallback: rule-based, in-process)
```

A decoupled SPA talks to a stateless REST API. The API owns all business rules and
persistence; the frontend only renders state and calls endpoints. The backend is a
long-running server (not serverless) so it keeps a real SQLAlchemy connection pool to MySQL.

### Frontend architecture

- **React + Vite + Tailwind**, with **React Router** for routing and **React Query** for all
  server state (fetching, caching, loading/error states, cache invalidation on mutations).
- A single **`apiClient`** (axios) attaches the JWT from `localStorage` on every request and,
  on a `401`, clears the token and redirects to `/login`.
- An **`AuthProvider`** context exposes `login`/`register`/`logout` and the current user
  (loaded from `/auth/me`). **`ProtectedRoute`** guards pages and enforces role (`customer`
  vs `agent`), redirecting appropriately.
- Pages: Login, Register, Customer Dashboard (own tickets + create), Agent Dashboard (all
  tickets + search/filter/pagination + analytics widget), Ticket Detail (info, comments,
  activity timeline, and agent-only status/priority/assignee controls + AI suggested response).
- Loading (`Spinner`), error (`ErrorBox`), and empty (`EmptyState`) states are used throughout.

### Backend architecture (layered)

```
app/
  core/         config (pydantic-settings/.env), database (engine/session), security (JWT, bcrypt)
  models/       SQLAlchemy ORM + enums
  schemas/      Pydantic request/response DTOs (validation + serialization)
  repositories/ data access (one class per aggregate)
  services/     business logic + RBAC + activity logging
  ai/           TriageProvider interface, GeminiProvider, RuleBasedProvider, factory
  api/          deps.py (DI wiring, auth guards) + routers/ (thin HTTP controllers)
  main.py       app factory, CORS, global domain→HTTP exception handlers
```

Each layer has a single responsibility and depends only on the layer beneath it through a
narrow interface:

- **Routers** parse/validate HTTP, call a service, and shape the response. No business logic.
- **Services** hold all rules (who can do what, when to log activity, how to triage). They
  depend on **repository** and **provider abstractions** injected via FastAPI dependencies —
  never on a concrete `Session` or the Gemini SDK directly. This is what makes them unit-testable.
- **Repositories** encapsulate all SQLAlchemy queries; swapping the query layer or database
  doesn't touch services.
- **Domain exceptions** (`NotFoundError`, `ForbiddenError`, `ConflictError`) are raised by
  services and mapped to HTTP status codes (404/403/409) by global handlers in `main.py`,
  keeping HTTP concerns out of the service layer.

---

## 2. Database Design

### Entities

- **User** — `id, email (unique), hashed_password, full_name, role(customer|agent), created_at`
- **Ticket** — `id, title, description, status, priority, category, suggested_response,
  created_by_id → User, assigned_to_id → User (nullable), created_at, updated_at`
- **Comment** — `id, ticket_id → Ticket, author_id → User, body, created_at`
- **ActivityEvent** — `id, ticket_id → Ticket, actor_id → User (nullable),
  event_type, old_value, new_value, created_at`

### Relationships

```
User 1───N Ticket   (as creator,  created_by_id)
User 1───N Ticket   (as assignee, assigned_to_id, nullable)
Ticket 1───N Comment
Ticket 1───N ActivityEvent
User 1───N Comment / ActivityEvent (author/actor)
```

`Ticket` declares **two** relationships to `User` (creator and assignee) with explicit
`foreign_keys=` to disambiguate the join.

### Design decisions

- **Enums in the schema** (`status`, `priority`, `category`, `role`, `event_type`) make
  invalid states unrepresentable at both the API (Pydantic) and DB level. Each enum member's
  name equals its value, so storage is stable and human-readable.
- **Dedicated `ActivityEvent` table** powers the required activity history / audit trail. It
  records old→new transitions, so the timeline is reconstructable without diffing snapshots.
- **`suggested_response` stored on the ticket** (generated once at creation) rather than
  recomputed — cheaper and deterministic for display.
- **`updated_at` (auto `onupdate`)** approximates resolution time for analytics (creation →
  resolving update).
- **Indexes** on `email`, `title`, `status`, `priority`, `category`, `created_by_id`,
  `assigned_to_id`, and `ticket_id` to support the search/filter/list queries.

### Database choice & trade-off (MySQL vs SQLite)

The original brief's tech-stack line listed **SQLite**; per instruction this implementation
uses **MySQL**. Because all data access goes through SQLAlchemy with no raw, dialect-specific
SQL, the application is portable across both. We exploit this in the test suite: **integration
tests run against in-memory SQLite** (fast, hermetic, no server needed) while **production runs
on MySQL**.

- **Benefit:** fast CI with zero infra; identical ORM code paths in tests and prod.
- **Risk:** a MySQL-only behavior (e.g., a dialect-specific function or collation) could pass
  in SQLite but fail in MySQL. Mitigated by keeping queries to portable SQLAlchemy constructs.
  A production-hardening step would add a CI job running the same integration tests against a
  real MySQL container.

---

## 3. Authentication Strategy

### Approach: JWT bearer tokens

- On register, the password is hashed with **bcrypt** (passlib). On login, credentials are
  verified and a signed **JWT** is returned containing `sub` (user id) and `role`.
- The frontend stores the token and sends it as `Authorization: Bearer <token>`.
- A `get_current_user` dependency decodes/validates the token and loads the user; a
  `require_agent` dependency gates agent-only endpoints. **Authorization is enforced in two
  places:** route dependencies for coarse role checks, and the service layer for per-resource
  ownership (e.g., a customer may only see their own tickets).

### Trade-offs

- **Stateless** — no server-side session store; the API scales horizontally and fits a
  decoupled SPA naturally. JWT also avoids CSRF concerns that cookie sessions carry.
- **Cost:** tokens can't be revoked before expiry. Mitigated here with a bounded lifetime
  (`ACCESS_TOKEN_EXPIRE_MINUTES`). Production would add refresh-token rotation and a revocation
  list (or short-lived access tokens + refresh endpoint).
- **Token storage:** kept in `localStorage` for simplicity. This is XSS-exposed; a hardened
  version would use an httpOnly cookie with CSRF protection, or in-memory tokens + silent refresh.

---

## 4. AI Integration

### Provider / model

Google **Gemini** (`gemini-2.0-flash` by default) via the `google-genai` SDK.

### Design — Strategy pattern behind an interface

```
TriageProvider (ABC)            triage(title, description) -> TriageResult{category, priority, suggested_response}
 ├── GeminiProvider             calls Gemini, parses & validates JSON against the enums
 └── RuleBasedProvider          deterministic keyword matching + templated response

SafeTriageProvider(primary)     wraps any provider; on ANY exception → RuleBasedProvider
get_triage_provider(key, model) returns Gemini when a key is set, else RuleBasedProvider
```

The `TicketService` depends only on the `TriageProvider` interface, so the provider can be
swapped (or stubbed in tests) with no service changes — this is the Open/Closed and
Dependency-Inversion principles in practice.

### Prompting strategy

Gemini is prompted to return **only a JSON object** with exactly `category`, `priority`, and
`suggested_response`, where `category`/`priority` must be one of the allowed enum values. The
response is stripped of markdown code fences, JSON-parsed, and each field is **validated against
the Python enums** (`Category(...)`, `Priority(...)`). Any missing key, bad JSON, or
out-of-range value raises a `ValueError`.

### Fallback handling

Triage **never blocks ticket creation**. Two layers of safety:

1. **No key / SDK init failure** → `get_triage_provider` returns `RuleBasedProvider` directly.
2. **Runtime failure** (timeout, network, malformed/invalid response) → `SafeTriageProvider`
   catches it and falls back to `RuleBasedProvider`, which maps keywords to a category/priority
   and returns a templated suggested response.

This means the platform produces a sensible category, priority, and draft response **with or
without** a working Gemini key — satisfying the "reasonable fallback mechanism" requirement.

### Why synchronous triage

Triage runs inline during `POST /tickets` for simplicity (KISS) and immediate feedback. The
trade-off is added latency on creation and coupling to provider availability — both bounded by
the fallback. At higher scale this would move to an async job/queue (see Future Improvements).

---

## 5. SOLID / KISS in this codebase

- **S**ingle Responsibility — routers (HTTP), services (rules), repositories (persistence),
  schemas (validation) are separate; one class/file per concern.
- **O**pen/Closed — new AI providers or repositories can be added without modifying services.
- **L**iskov — `GeminiProvider` and `RuleBasedProvider` are interchangeable behind `TriageProvider`.
- **I**nterface Segregation — repositories expose only the methods their service needs.
- **D**ependency Inversion — services receive abstractions (repos, provider) via FastAPI DI;
  no service constructs a `Session` or the Gemini client itself.
- **KISS** — one service per aggregate, four tables, synchronous triage with a fallback,
  `create_all` instead of migrations at this scale. No event bus, CQRS, or microservices.

---

## 6. Future Improvements

If given more time, in rough priority order:

1. **Migrations** — replace `create_all` with Alembic for safe schema evolution.
2. **Auth hardening** — refresh-token rotation, token revocation, httpOnly-cookie storage,
   rate limiting on auth endpoints.
3. **Real-time updates** — WebSockets/SSE so agents see new tickets and comment activity live.
4. **Notifications** — email/in-app notifications on assignment, status change, and new comments.
5. **SLA tracking** — ticket aging, due-by timers, and escalation indicators by priority.
6. **Async AI triage** — move Gemini calls to a background task/queue; show "triaging…" then
   update, removing provider latency from the creation path. Add prompt/response logging and
   re-triage on demand.
7. **Richer analytics** — time-series of volume/resolution, per-agent load, first-response time.
8. **Search** — MySQL full-text (or OpenSearch) instead of `LIKE` for scale and relevance.
9. **Frontend tests** — Vitest + React Testing Library for components and hooks.
10. **CI** — run the integration suite against a real MySQL container in addition to SQLite,
    plus linting and a build gate.
