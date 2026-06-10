# AI-Powered Support Ticket Platform

A full-stack support ticket platform where **customers** create and track tickets and
**support agents** triage, assign, and resolve them. When a ticket is created, an LLM
(Google Gemini, with a deterministic fallback) automatically generates the ticket's
**category**, **priority**, and a **suggested response** draft for agents.

- **Backend:** Python + FastAPI, layered (routers → services → repositories → SQLAlchemy models)
- **Database:** MySQL (via SQLAlchemy + PyMySQL)
- **Frontend:** React + Vite + Tailwind + React Query
- **Auth:** JWT bearer tokens with `customer` / `agent` roles
- **AI:** Google Gemini with a rule-based fallback provider

See [ARCHITECTURE.md](./ARCHITECTURE.md) for design decisions and trade-offs.

## Live Demo

| | URL |
|---|---|
| **Frontend** (Vercel) | https://ticket-tau.vercel.app |
| **Backend API** (Render) | https://ai-powered-support-ticket-platform.onrender.com |
| **API docs** (Swagger) | https://ai-powered-support-ticket-platform.onrender.com/docs |
| **Repository** | https://github.com/AMit090912/AI-Powered-Support-Ticket-Platform |

**Demo accounts** (password `password123`):
- Agent — `agent@demo.com` · Customer — `customer@demo.com`

> ⚠️ The backend is on Render's free tier and **sleeps after ~15 min idle** — the first
> request may take 30–60s to wake. Reload once and it's responsive.

---

## Features

- Register / login (JWT), role-based access (customer vs agent)
- Customers: create tickets, view & comment on their own tickets
- Agents: view all tickets, search, filter, assign, change status/priority, comment, close
- **AI triage** on ticket creation → category + priority + suggested response (Gemini, with fallback)
- Search (title/description), filter (status/priority/category/assignee), pagination
- **Audit trail / activity history** per ticket (created, status/priority/category changes, assignment, comments)
- **Analytics summary** for agents (open counts, by-category, by-priority, avg resolution time)
- Graceful error handling and loading/empty states throughout the UI

---

## Project structure

```
backend/        FastAPI app (app/), tests (tests/), seed.py
frontend/       React + Vite SPA (src/)
ARCHITECTURE.md System / DB / auth / AI design + trade-offs
docs/           Design spec and implementation plan
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (built/tested on Node 22)
- **MySQL 8+** running locally (or a hosted MySQL connection string)

---

## Backend — local setup

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the MySQL database
#    mysql -u root -p
#    CREATE DATABASE support_tickets CHARACTER SET utf8mb4;

# 4. Configure environment
cp .env.example .env        # (Windows: copy .env.example .env)
#    Edit .env — set DATABASE_URL, JWT_SECRET, and GEMINI_API_KEY

# 5. (Optional) seed demo data
python seed.py

# 6. Run the API
uvicorn app.main:app --reload
```

- API runs at `http://localhost:8000`
- Interactive API docs (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

> **Tables are auto-created** at startup via SQLAlchemy `create_all` (assignment scale).
> A production deployment would use Alembic migrations instead — see ARCHITECTURE.md.

### Environment variables (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | yes | `sqlite:///./dev.db` | SQLAlchemy URL. MySQL example: `mysql+pymysql://root:password@localhost:3306/support_tickets` |
| `JWT_SECRET` | yes | `change-me` | Secret used to sign JWTs. Use a long random string in production. |
| `JWT_ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `1440` | Access token lifetime (minutes) |
| `GEMINI_API_KEY` | no | _(empty)_ | Google Gemini API key. **If empty, the rule-based fallback is used** (no failure). |
| `GEMINI_MODEL` | no | `gemini-2.0-flash` | Gemini model id |
| `CORS_ORIGINS` | no | `http://localhost:5173` | Comma-separated allowed frontend origins |

### Running the backend without MySQL (quick demo)

The code is DB-agnostic. To try it without MySQL, set `DATABASE_URL=sqlite:///./dev.db`
in `.env` and run as above. (Tests already run against in-memory SQLite — see below.)

---

## Frontend — local setup

```bash
cd frontend
npm install
cp .env.example .env        # (Windows: copy .env.example .env)
#    Ensure VITE_API_URL points at the backend (default http://localhost:8000)
npm run dev
```

- App runs at `http://localhost:5173`
- Build for production: `npm run build` (output in `frontend/dist/`)

---

## Running the tests

```bash
cd backend
.venv\Scripts\python.exe -m pytest        # Windows
# or, with the venv activated:  pytest
```

- **53 tests** total: 29 unit (services, security, AI providers — repositories/services tested
  with mocks) + 24 integration (full API via FastAPI `TestClient` against in-memory SQLite).
- No running MySQL is required for tests — see the DB trade-off in ARCHITECTURE.md.

---

## Demo credentials (after `python seed.py`)

| Role | Email | Password |
|------|-------|----------|
| Agent | `agent@demo.com` | `password123` |
| Customer | `customer@demo.com` | `password123` |

The seed also creates three sample tickets for the demo customer.

---

## Deployment

**Topology:** React SPA on **Vercel** → FastAPI backend on **Render/Railway** → hosted MySQL.

### Backend (Render / Railway)
1. Create a service from the `backend/` directory.
2. Provision a managed MySQL instance; copy its connection string.
3. Set environment variables: `DATABASE_URL` (hosted MySQL), `JWT_SECRET`, `GEMINI_API_KEY`,
   `GEMINI_MODEL`, `CORS_ORIGINS=<your-vercel-url>`.
4. Start command (also in `backend/Procfile`):
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Frontend (Vercel)
1. Import the repo into Vercel; set the project root to `frontend/`.
2. Set `VITE_API_URL=<your-backend-url>`.
3. Deploy. `frontend/vercel.json` rewrites all routes to `/` so client-side routing works.

**Live URLs:**
- Frontend: https://ticket-tau.vercel.app
- Backend: https://ai-powered-support-ticket-platform.onrender.com

---

## Assumptions made

- **Role at registration:** users self-select `customer` or `agent` at registration. A real
  system would gate agent creation behind an admin; kept open here for easy evaluation.
- **MySQL instead of SQLite:** the original brief listed SQLite; per instruction we use MySQL.
  SQLAlchemy keeps the code portable, so the test suite runs against in-memory SQLite while
  production uses MySQL. (See ARCHITECTURE.md for the trade-off.)
- **Schema management:** tables are created via `create_all` at startup for simplicity at this
  scale. Production would use Alembic migrations.
- **AI triage is synchronous** at ticket-creation time and never blocks creation: any Gemini
  failure (no key, timeout, bad JSON) falls back to the deterministic rule-based provider.
- **One suggested response** is generated once at creation and stored; it is shown only to agents.
- **`updated_at`** is used to approximate resolution time in analytics (time from creation to
  the resolving/closing update).
