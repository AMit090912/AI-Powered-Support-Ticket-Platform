# Architecture

A support ticket app. Customers raise tickets, agents resolve them, and an AI tags each new
ticket with a category, priority, and a draft reply.

**Stack:** FastAPI + SQLAlchemy + MySQL on the backend, React (Vite + Tailwind) on the
frontend, JWT for auth, Google Gemini for the AI.

## System design

The frontend and backend are separate. React is just the UI — it calls the backend over REST
and shows what comes back. The backend holds all the logic and talks to MySQL. Gemini is only
called when a ticket is created.

```
React (Vercel)  →  FastAPI (Render)  →  MySQL
                        ↓ on create
                   Gemini  (falls back to keyword rules if it fails)
```

The backend is split into layers so each part has one job:

- **routers** – handle the HTTP request and response
- **services** – the actual rules: permissions, when to log activity, calling the AI
- **repositories** – the database queries
- **models / schemas** – the DB tables and the request/response shapes

Services never touch the database or Gemini directly — those are passed in. I did that mainly so
I can test the rules with fakes, and so changing the database or AI provider doesn't break the
logic.

On the frontend: React Router for pages, React Query for data fetching (it gives me caching and
loading/error states), and one axios client that attaches the JWT to every request and sends you
to login on a 401. A `ProtectedRoute` decides what customers vs agents can see.

## Database

Four tables: **User, Ticket, Comment, ActivityEvent**.

- A user creates many tickets, and an agent can be assigned many — so a ticket links to User
  twice (creator and assignee).
- Comments and activity events belong to a ticket.

A few decisions worth calling out:

- Status, priority, category and role are **enums**, so invalid values can't be saved.
- **ActivityEvent** is a separate table that records each change (what changed, from what, to
  what, by whom). That's the activity history — simpler than comparing old copies of a ticket.
- The AI's suggested reply is saved on the ticket once at creation, not regenerated every time.

On **MySQL vs SQLite**: the brief said SQLite, but I used MySQL. Since everything goes through
SQLAlchemy, the tests run on in-memory SQLite (fast, no server needed) while the real app runs on
MySQL. There's a small risk the two behave differently, so I stuck to standard queries.

## Authentication

JWT. On login you get a signed token holding your user id and role, and the frontend sends it on
every request. Passwords are hashed with bcrypt, never stored as plain text.

Permissions are checked in two places: at the route level for agent-only endpoints, and inside
the services for finer rules like "a customer can only see their own tickets."

I chose JWT because it's stateless — no session store to manage, and it fits a separate frontend
cleanly. The trade-off is you can't cancel a token before it expires (so I keep them
short-lived), and keeping it in `localStorage` is simple but exposed to XSS. A production version
would add refresh tokens and store it in a secure cookie.

## AI integration

When a ticket is created, Gemini reads the title and description and returns a category, a
priority, and a draft reply for the agent.

It's wired behind one interface, `TriageProvider`, with two implementations: `GeminiProvider`
(the real AI) and `RuleBasedProvider` (keyword matching). A `SafeTriageProvider` wraps the real
one and falls back to the rule-based one if anything goes wrong. The ticket service only knows
about the interface, so swapping providers doesn't change it.

**Prompt:** I ask Gemini to return only JSON with `category`, `priority`, and
`suggested_response`, restricted to the allowed values, then I validate the reply against those
values before saving.

**Fallback:** the AI can never block ticket creation. No API key → use the rule-based provider.
AI errors or returns junk → catch it and use the rule-based provider. So you always get a
sensible result, with or without a working key. The model used is `gemini-2.0-flash`.

It runs synchronously when a ticket is created, which is simplest. At higher scale I'd move it to
a background job so creating a ticket stays instant.

## Testing

54 tests. Unit tests check the rules using fake repositories and a fake AI provider. Integration
tests hit the real API (on SQLite) and cover login, ticket create/list/update, search, filtering,
pagination, permissions, comments, and activity.

## If I had more time

Database migrations (Alembic), refresh tokens with cookie storage, real-time updates over
WebSockets, email/in-app notifications, SLA tracking, moving the AI call to a background job,
full-text search, and frontend tests.
