# 🤖 ResolveAI — AI Support Ticket Triage System

**ResolveAI** is a production-grade AI support ticket resolver powered by a **LangGraph multi-agent triage pipeline** and a **pgvector RAG (Retrieval-Augmented Generation)** knowledge base. It automatically triages incoming customer support tickets — resolving, clarifying, or escalating them — and continuously improves by logging every resolution back into the knowledge base.

---

## ✨ Key Features

- **Multi-Agent Triage (LangGraph)** — `Evaluator → Writer → Auditor` critique loop with automatic retry on low-quality drafts
- **pgvector RAG Store** — 128-dimensional semantic embeddings stored in PostgreSQL for real-time similarity search
- **Self-Improving Memory Loop** — Resolved tickets are vectorized and indexed back into the knowledge base automatically
- **NVIDIA NIM Integration** — Uses NVIDIA NIM LLMs and embeddings; falls back to deterministic offline mocks when no API key is set
- **OpenAI Fallback** — Secondary LLM fallback via OpenAI GPT-4o-mini
- **JWT Authentication** — Secure register/login with bcrypt password hashing and role-based access (admin/user)
- **React + Vite Frontend** — Glassmorphic dark-theme dashboard with ticket management, AI workspace, and analytics
- **Zero-Dependency Offline Mode** — Fully runnable without any paid API keys using deterministic mock responses

---

## 🏗️ Architecture

```
Browser (localhost:5173)
        │
        │ fetch() — REST API
        ▼
FastAPI Backend (localhost:8000)
        │
        ├── /api/auth/*          JWT register / login / me
        ├── /api/ingest          Ingest documents into Knowledge Base
        ├── /api/query           Direct RAG + LangGraph triage
        ├── /api/tickets/*       Full ticket CRUD + AI triage pipeline
        └── /api/analytics       Dashboard metrics
                │
                ▼
        LangGraph Agent Pipeline
        ┌─────────────────────────────────────┐
        │  Evaluator Node                      │
        │    ↓ (Answer / Clarify / Escalate)  │
        │  Writer Node  ←──────────────────┐  │
        │    ↓                             │  │
        │  Auditor Node ──(Retry, max 2)───┘  │
        │    ↓ (Pass)                         │
        │   END                               │
        └─────────────────────────────────────┘
                │
                ▼
        PostgreSQL + pgvector (Docker)
        ┌────────────────────┐
        │ users              │
        │ tickets            │
        │ clarification_qs   │
        │ ticket_activity_logs│
        │ documents          │
        │ document_chunks    │ ← 128-dim Vector(128) embeddings
        └────────────────────┘
```

---

## 📁 Project Structure

```
resolve-ai/
├── docker-compose.yml          # PostgreSQL + pgvector container
│
├── backend/                    # FastAPI Python backend
│   ├── run.py                  # Uvicorn entrypoint → localhost:8000
│   ├── requirements.txt        # Python dependencies
│   ├── alembic.ini             # Alembic migration config
│   ├── .env.example            # Template — copy to .env and fill in values
│   ├── migrations/             # Alembic migration files
│   ├── scripts/                # Seeding and utility scripts
│   └── app/
│       ├── main.py             # FastAPI app factory + CORS + routers
│       ├── core/
│       │   ├── config.py       # Pydantic settings (reads .env)
│       │   ├── database.py     # SQLAlchemy engine + session factory
│       │   └── security.py     # JWT creation + bcrypt password hashing
│       ├── models/             # SQLAlchemy ORM models
│       ├── schemas/            # Pydantic request/response schemas
│       ├── api/
│       │   ├── deps.py         # get_current_user auth dependency
│       │   └── routes/
│       │       ├── auth.py     # POST /auth/register, /auth/login, GET /auth/me
│       │       ├── tickets.py  # Full ticket lifecycle + AI diagnose pipeline
│       │       ├── ingest.py   # POST /ingest — add documents to KB
│       │       ├── query.py    # POST /query — RAG + LangGraph triage
│       │       ├── analytics.py# GET /analytics — dashboard metrics
│       │       └── settings.py # User settings
│       └── services/
│           ├── agent_service.py    # LangGraph 3-node agent graph
│           ├── llm_service.py      # NVIDIA NIM LLM gateway + mock fallback
│           ├── embedding_service.py# NIM embeddings + deterministic fallback
│           ├── retrieval_service.py# pgvector cosine similarity search
│           ├── ai_service.py       # OpenAI-backed problem solver
│           └── chunking.py         # Sliding-window text chunking
│
└── frontend/                   # React + Vite + TypeScript
    ├── vite.config.ts
    ├── .env.example            # Template — copy to .env
    └── src/
        ├── App.tsx             # Auth gate + state-based view router
        ├── index.css           # Global CSS design system (glassmorphism)
        ├── context/
        │   ├── AuthContext.tsx # JWT token state, login/register/logout
        │   └── ToastContext.tsx# Global toast notifications
        ├── components/
        │   └── Header.tsx      # Navigation bar
        └── pages/
            ├── Auth.tsx        # Login / Register
            ├── Dashboard.tsx   # Ticket list + status metrics
            ├── Workspace.tsx   # Ticket detail + AI pipeline UI
            └── Settings.tsx    # User settings
```

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker Desktop | Latest |

---

### Step 1 — Start the Database

```bash
cd resolve-ai
docker-compose up -d
```

This starts a **PostgreSQL 16 + pgvector** container on port `5432`.

---

### Step 2 — Backend Setup

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
# → Edit .env and fill in SECRET_KEY (required) and any API keys

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
python run.py
```

**Backend running at:** `http://127.0.0.1:8000`
**Interactive API docs:** `http://127.0.0.1:8000/docs`

---

### Step 3 — Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

**Frontend running at:** `http://localhost:5173`

---

### Step 4 — Verify It Works

1. Open `http://localhost:5173` → ResolveAI login page
2. Click **Register** and create an account
3. Log in → Dashboard loads
4. Click **New Ticket** and submit a support query
5. Click **Run AI Diagnosis** → LangGraph agent triages the ticket
6. View the resolution, clarification request, or escalation result

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ Yes | — | JWT signing key — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL` | No | `postgresql://postgres:postgres@localhost:5432/resolve_ai` | PostgreSQL connection string |
| `NVIDIA_NIM_API_KEY` | No | _(empty)_ | NVIDIA NIM API key for real LLM + embeddings. Runs in mock mode if not set |
| `OPENAI_API_KEY` | No | _(empty)_ | OpenAI API key (used by `ai_service.py` for problem-solver flow) |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed frontend origins |

> **Tip:** Generate a strong secret key:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `http://localhost:8000/api` | Backend API base URL |

---

## 🧠 LangGraph Agent Pipeline

The triage pipeline is a 5-node `StateGraph` compiled with LangGraph:

```
            ┌──────────────┐
            │   Evaluator  │  Reads query + RAG context
            │              │  → Decides: Answer / Clarify / Escalate
            └──────┬───────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
    [Writer]   [Clarify]  [Escalate]
        │          │          │
        ▼        [END]      [END]
    [Auditor]
        │
        ├── Passed → [END]
        └── Failed (max 2 retries) → [Writer]
```

- **Evaluator** — Categorizes the query into `Answer`, `Clarify`, or `Escalate`
- **Writer** — Drafts a complete support resolution using the retrieved KB context
- **Auditor** — Validates the draft for hallucinations and completeness; retries up to 2 times
- **Clarify** — Asks a polite follow-up question for vague queries
- **Escalate** — Notifies the customer they're being escalated to a human agent

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and receive JWT token |
| `GET` | `/api/auth/me` | Get current authenticated user |

### Tickets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tickets/` | Create a new support ticket |
| `GET` | `/api/tickets/` | List tickets (admin: all, user: own) |
| `GET` | `/api/tickets/{id}` | Get ticket details, logs, clarifications |
| `DELETE` | `/api/tickets/{id}` | Delete a ticket |
| `POST` | `/api/tickets/{id}/diagnose` | Run AI triage pipeline on ticket |
| `POST` | `/api/tickets/{id}/clarify/generate` | Generate a clarification question |
| `POST` | `/api/tickets/{id}/clarify/answer` | Submit clarification answers |
| `GET` | `/api/tickets/{id}/similar` | Get pgvector similarity matches |
| `GET` | `/api/tickets/{id}/activity` | Get audit activity logs |
| `GET` | `/api/tickets/{id}/export` | Export ticket as Markdown report |

### Knowledge Base

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest` | Ingest a document into the KB (chunks + embeds) |
| `POST` | `/api/query` | Run a direct RAG + LangGraph query |

---

## 🔧 Scripts & Utilities

```bash
# Seed the knowledge base with initial policy documents
python scripts/seed_documents.py

# Verify RAG retrieval is working correctly
python verify_rag.py

# Run end-to-end integration tests
python test_e2e_real.py
```

---

## 🐳 Docker

The `docker-compose.yml` starts only the database. The backend and frontend run locally.

```bash
# Start PostgreSQL + pgvector
docker-compose up -d

# Stop and remove container
docker-compose down

# Stop and also delete all data volumes
docker-compose down -v
```

---

## 🔒 Security Notes

- **Never commit `.env`** to version control. It is listed in `.gitignore`.
- Rotate your `SECRET_KEY` before any production deployment.
- The default `docker-compose.yml` uses `postgres/postgres` credentials — change these for any non-local environment.
- All ticket routes are protected by JWT authentication. Admins can access all tickets; users can only access their own.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI |
| ORM | SQLAlchemy + Alembic |
| Database | PostgreSQL 16 + pgvector |
| AI Agents | LangGraph |
| LLM / Embeddings | NVIDIA NIM (`meta/llama-3-70b-instruct`) |
| LLM Fallback | OpenAI GPT-4o-mini |
| Auth | JWT (`python-jose`) + bcrypt (`passlib`) |
| Frontend | React 19 + TypeScript + Vite |
| UI Icons | Lucide React |
| Charts | Recharts |
| Container | Docker + Docker Compose |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
