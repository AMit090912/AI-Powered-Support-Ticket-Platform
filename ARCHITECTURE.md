# Architecture — AI-Powered Support Ticket Platform

This document explains how the project is built and, more importantly, **why** each decision
was made. It's written to be easy to follow even if you haven't seen the code yet.

**What the app does:** Customers raise support tickets and track them. Support agents see all
tickets, search and filter them, assign them, change their status, and reply. When a customer
creates a ticket, an AI model automatically reads it and fills in the **category**, the
**priority**, and a **suggested reply** for the agent — so agents spend less time sorting and
more time solving.

**Two user roles:**
- **Customer** — creates tickets, views their own tickets, adds comments.
- **Agent** — views all tickets, searches/filters, assigns, updates status/priority, comments, closes.

---

## 1. Tech Stack (and why)

| Layer | Choice | Why I picked it |
|-------|--------|-----------------|
| Backend | **Python + FastAPI** | Fast to build, automatic input validation, and free interactive API docs (Swagger). |
| Database access | **SQLAlchemy ORM** | Lets us talk to the database with Python objects instead of raw SQL, and keeps the code database-agnostic. |
| Database | **MySQL** | Reliable relational database; the assignment asked for it. |
| Auth | **JWT (JSON Web Tokens)** | Stateless login that fits a separate frontend + backend cleanly. |
| AI | **Google Gemini** (`gemini-2.0-flash`) | Good, fast model for short classification tasks; with a non-AI fallback. |
| Frontend | **React + Vite + Tailwind** | Modern, quick to build, and a clean way to consume the REST API. |
| Data fetching | **React Query** | Handles loading/error states and caching for us so the UI code stays simple. |

The focus of the project is the **backend and how it serves the frontend**, so the frontend is
intentionally clean and simple rather than heavily designed.

---

## 2. System Design

### 2.1 The big picture

```
┌──────────────┐     HTTPS / JSON      ┌────────────────────────────┐       ┌──────────┐
│  React app   │ ───── requests ─────► │      FastAPI backend        │ ────► │  MySQL   │
│  (Vercel)    │ ◄──── JSON + JWT ──── │  routers → services → repos │ ◄──── │ database │
└──────────────┘                       │      + AI triage layer      │       └──────────┘
                                        └─────────────┬──────────────┘
                                                      │  (only when a ticket is created)
                                                      ▼
                                             Google Gemini API
                                       (falls back to rule-based if it fails)
```

The system has three parts that each do one job:
1. **The frontend** (React) only shows screens and calls the backend. It contains **no
   business rules** — it just asks the backend for data and displays it.
2. **The backend** (FastAPI) holds all the logic: who is allowed to do what, how tickets are
   created and updated, and when to call the AI.
3. **The database** (MySQL) stores everything permanently.

They talk over plain HTTP using JSON. This separation means I can change the frontend without
touching the backend, and vice versa.

### 2.2 How a request actually flows (example: creating a ticket)

1. The customer fills in a title + description and clicks **Submit**.
2. The React app sends `POST /tickets` with the customer's **JWT** in the header.
3. The backend checks the token to confirm who the user is.
4. The **ticket service** asks the **AI layer** to classify the ticket (category, priority,
   suggested reply).
5. The service saves the ticket through the **repository** (the database layer) and writes an
   "activity" record saying the ticket was created.
6. The backend returns the saved ticket as JSON; React shows it in the list.

### 2.3 Frontend architecture

The React app is organized into small, focused pieces:

- **Pages** — Login, Register, Customer Dashboard, Agent Dashboard, Ticket Detail.
- **Components** — reusable UI like the ticket table, filters, pagination, badges, and the
  loading/error/empty states.
- **`lib/` (the glue)**:
  - `api.js` — one shared connection to the backend. It automatically attaches the login
    token to every request, and if the backend says "not logged in" (401), it sends the user
    back to the login page.
  - `auth.jsx` — keeps track of who's logged in (login, register, logout) and remembers the
    token so a refresh doesn't log you out.
  - `tickets.js` — small **React Query** hooks for loading tickets, comments, activity, etc.
    React Query gives us caching and automatic loading/error states for free, and refreshes
    the screen automatically after a change (e.g., after an agent changes a status).
- **Routing & roles** — a `ProtectedRoute` wrapper checks if you're logged in and sends
  customers to their dashboard and agents to theirs. Agent-only controls (assign, change
  status, AI suggestion) simply don't render for customers.
- **States everywhere** — every screen handles three cases: still **loading** (spinner),
  **error** (message box), and **empty** (friendly "nothing here yet" text).

### 2.4 Backend architecture (layered)

The backend is split into layers, where **each layer has one job** and only talks to the layer
directly below it:

```
app/
  core/         settings (.env), database connection, security (JWT + password hashing)
  models/       database tables (SQLAlchemy) + the fixed lists of values (enums)
  schemas/      the shapes of requests/responses (validation done here)
  repositories/ all the database queries live here
  services/     the actual business rules + permission checks + activity logging
  ai/           the triage providers (Gemini + rule-based) behind one interface
  api/          deps.py (wiring + login guards) and routers/ (the HTTP endpoints)
  main.py       starts the app, sets up CORS, and turns errors into clean HTTP responses
```

Here's what each layer does, in plain terms:

- **Routers** are the "front desk." They receive the HTTP request, hand it to a service, and
  send back the response. They contain **no logic** of their own.
- **Services** are the "brain." They decide things like *"can this user view this ticket?"*,
  *"should we log an activity event?"*, and *"call the AI now."* All the real rules live here.
- **Repositories** are the "filing clerks." They're the only place that runs database queries.
  If we ever changed databases, only this layer would need attention.
- **Schemas** define exactly what a valid request and response look like, so bad input is
  rejected automatically before it reaches the logic.

**Why bother with layers?** Two reasons:
1. **It's easy to test.** Because services don't talk to the database directly (they receive a
   repository), I can test the rules with a fake repository — no real database needed.
2. **Changes stay contained.** A change in how we store data doesn't ripple into the rules, and
   a change in the rules doesn't ripple into the HTTP code.

**Errors:** services raise simple errors like `NotFoundError`, `ForbiddenError`, and
`ConflictError`. A central handler turns those into the right HTTP codes (404, 403, 409) with a
consistent JSON message, so the HTTP details stay out of the business logic.

---

## 3. Database Design

### 3.1 The four tables

- **User** — `id, email (unique), hashed_password, full_name, role (customer/agent), created_at`
- **Ticket** — `id, title, description, status, priority, category, suggested_response,
  created_by (User), assigned_to (User, can be empty), created_at, updated_at`
- **Comment** — `id, ticket_id, author (User), body, created_at`
- **ActivityEvent** — `id, ticket_id, actor (User), event_type, old_value, new_value, created_at`

### 3.2 How they relate

```
User  1 ──── N  Ticket      (a user creates many tickets)
User  1 ──── N  Ticket      (an agent can be assigned many tickets)
Ticket 1 ──── N  Comment    (a ticket has many comments)
Ticket 1 ──── N  ActivityEvent  (a ticket has a history of events)
```

In words: one user can create many tickets, and an agent can be assigned many tickets — so a
ticket points at a User **twice** (once as the creator, once as the assignee). Each ticket also
has many comments and many activity events.

### 3.3 Design decisions (and why)

- **Fixed value lists (enums).** Status, priority, category, role, and event type are
  restricted to a known set of values. This makes invalid data impossible — you can't save a
  ticket with priority "banana." It's enforced both in the API and in the database.
- **A separate "ActivityEvent" table for history.** Instead of trying to figure out what
  changed by comparing old copies of a ticket, every meaningful change writes one row that says
  *what changed, from what, to what, and who did it.* The activity timeline on the ticket page
  is just these rows shown in order. This is the audit-trail / activity-history feature.
- **The AI's suggested reply is saved on the ticket.** It's generated once when the ticket is
  created and stored, rather than re-asking the AI every time the page opens — cheaper and
  consistent.
- **`updated_at` is used to estimate resolution time** in the analytics (time from "created" to
  the update that resolved it). It's an approximation, which is fine for a summary dashboard.
- **Indexes** are added on the columns we search and filter by (email, title, status, priority,
  category, who created it, who it's assigned to) so those queries stay fast.

### 3.4 Why MySQL — and an honest trade-off

The assignment asked for MySQL, so that's what production uses. Because all database access
goes through SQLAlchemy (no hand-written MySQL-specific SQL), the same code also works on
**SQLite**. I used that to my advantage: the **automated tests run on an in-memory SQLite
database** so they're fast and need no database server, while the **real app runs on MySQL**.

- **Benefit:** tests are quick and need zero setup; the exact same code paths are exercised.
- **Risk:** in theory something could behave differently on MySQL vs SQLite. I avoided that by
  sticking to standard SQLAlchemy features. The proper next step (noted below) is to also run
  the tests against a real MySQL in CI.

---

## 4. Authentication Strategy

### 4.1 Approach chosen: JWT (token-based login)

Step by step:
1. **Register** — the password is never stored as plain text. It's run through **bcrypt**
   (a one-way hashing function) and only the hash is saved.
2. **Login** — the backend checks the email + password and, if correct, returns a **JWT**: a
   signed token that contains the user's id and role.
3. **Every request after that** — the frontend sends the token in the `Authorization` header.
   The backend verifies the signature, reads who the user is, and proceeds.

**Permissions are checked in two places:**
- **Route level** — some endpoints (like the agent analytics) require the `agent` role.
- **Service level** — finer rules, like *"a customer can only open their own tickets,"* are
  checked inside the service where we have both the user and the ticket. This is what prevents
  one customer from reading another customer's ticket by guessing an id.

### 4.2 Why JWT (vs server-side sessions)

- It's **stateless** — the server doesn't have to remember logged-in users, which keeps things
  simple and easy to scale, and fits a separate frontend + backend naturally.
- It avoids some cookie/CSRF complexity.

### 4.3 Trade-offs (being honest)

- **You can't instantly cancel a token** before it expires. I limit the damage by giving tokens
  a fixed lifetime. A production version would add refresh tokens and a way to revoke them.
- **The token is stored in the browser's `localStorage`**, which is simple but exposed if the
  site had a script-injection (XSS) bug. A hardened version would use a secure `httpOnly`
  cookie instead.

---

## 5. AI Integration

### 5.1 What the AI does

When a ticket is created, the AI reads the title + description and returns three things:
1. **Category** — billing / technical / account access / feature request / general
2. **Priority** — low / medium / high / critical
3. **Suggested response** — a short draft reply the agent can send

### 5.2 Provider / model

**Google Gemini**, model `gemini-2.0-flash`, through the official `google-genai` library. Flash
is a fast, lightweight model — perfect for a quick "read this and classify it" task.

### 5.3 How it's designed (so it's easy to change)

All AI logic sits behind a single, simple interface:

```
TriageProvider  ── triage(title, description) → { category, priority, suggested_response }
   ├── GeminiProvider      → calls the real AI
   └── RuleBasedProvider   → no AI; matches keywords (the backup plan)

SafeTriageProvider(primary) → tries the primary, falls back to RuleBasedProvider on ANY error
```

The ticket logic only knows about the `TriageProvider` interface — it has **no idea** whether
it's talking to Gemini or the backup. This means I can swap in a different AI provider (or a
test stub) by changing one line, without touching the ticket code. (This is the "Strategy
pattern.")

### 5.4 Prompting strategy

I ask Gemini to reply with **only a JSON object** containing exactly the three fields, and I
tell it the category and priority **must** be one of the allowed values. When the reply comes
back, the code strips any markdown formatting, parses the JSON, and **double-checks** each value
against the allowed list. If anything is wrong — bad JSON, a missing field, an unexpected
value — it's treated as a failure.

### 5.5 Fallback handling (the important part)

**The AI can never break ticket creation.** There are two safety nets:
1. **No API key, or the AI library won't start** → the app simply uses the rule-based backup
   from the start.
2. **The AI call fails or returns junk** → a wrapper catches the error and uses the rule-based
   backup for that ticket.

The rule-based backup is just keyword matching: words like "refund" or "invoice" → billing;
"urgent" or "outage" → critical priority; and each category has a ready-made reply. It's not as
smart as the AI, but it's instant and always works — so the customer always gets a sensible
category, priority, and draft reply, **with or without** a working AI key.

### 5.6 Why the AI runs immediately (not in the background)

I call the AI right when the ticket is created so the agent sees the triage straight away, and
because it keeps the design simple. The downside is it adds a little time to ticket creation and
depends on the AI being up — but the fallback keeps that under control. For a high-traffic
system I'd move this to a background job (see Future Improvements).

---

## 6. Design Principles in Plain English (SOLID & KISS)

I tried to keep the code clean using a few well-known ideas:

- **Each piece does one thing** — routers handle HTTP, services hold rules, repositories handle
  the database, schemas handle validation. (Single Responsibility)
- **Easy to extend, hard to break** — I can add a new AI provider or a new query without
  rewriting existing logic. (Open/Closed)
- **Swappable parts** — Gemini and the rule-based provider are interchangeable because they
  share the same interface. (Liskov / interchangeability)
- **Depend on interfaces, not concrete things** — services receive their database and AI
  helpers from outside instead of creating them, which is exactly what makes them testable.
  (Dependency Inversion)
- **KISS (Keep It Simple)** — no over-engineering. One service per area, four tables, a
  straightforward synchronous AI call with a fallback. I only added structure where it earns
  its keep (like the AI interface).

---

## 7. Testing

There are **54 automated tests** in two groups:

- **Unit tests** — test the business rules in isolation using fake repositories and a fake AI
  provider. Fast, and they pinpoint exactly which rule broke.
- **Integration tests** — start the whole API and make real requests against an in-memory
  database. These cover login, ticket create/list/update, search, filtering, pagination,
  permission rules, comments, and activity.

This mix gives confidence that both the individual rules **and** the full request flow work.

---

## 8. Error Handling & Validation

- **Bad input** (missing fields, too-short password, wrong types) is rejected automatically by
  the schema layer with a clear `422` error — before it reaches any logic.
- **Business errors** become clean HTTP responses: not found → `404`, not allowed → `403`,
  duplicate email → `409`.
- **The frontend** shows these gracefully: form errors inline, a friendly message on failure,
  and an automatic redirect to login if the session expired.

---

## 9. Future Improvements

If I had more time, in rough priority order:

1. **Database migrations** (Alembic) instead of auto-creating tables on startup, so the schema
   can change safely over time.
2. **Stronger auth** — refresh tokens, the ability to revoke a token, storing the token in a
   secure cookie, and rate-limiting the login endpoint.
3. **Real-time updates** (WebSockets) so agents see new tickets and comments without refreshing.
4. **Notifications** — email or in-app alerts on assignment, status change, and new comments.
5. **SLA tracking** — ticket aging and escalation flags for high-priority tickets.
6. **Background AI triage** — move the AI call off the creation path so creating a ticket is
   instant, then update it when the AI responds.
7. **Better search** — full-text search instead of simple "contains" matching, for scale.
8. **Frontend tests** — add component/hook tests with Vitest + React Testing Library.
9. **CI pipeline** — run the test suite (including against a real MySQL) and linting on every
   push.

---

*In short: a clean, layered backend that holds all the rules and talks to the frontend over a
simple REST API, an AI triage feature that's useful but can never break the app, and a lean,
modern frontend — built to be correct, tested, and easy to understand.*
