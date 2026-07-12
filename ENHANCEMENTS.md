# 🛣️ ResolveAI — Enhancement Roadmap

> **Document Purpose**: Technical specifications for the next iteration of ResolveAI.
> Each enhancement includes the current gap, proposed solution, and implementation plan.

---

## Priority Overview

| Phase | Theme | Effort | Impact |
|-------|-------|--------|--------|
| **Phase 1** | Real-time Streaming & WebSockets | Medium | 🔥 Very High |
| **Phase 2** | Knowledge Base Upgrades | Medium | 🔥 Very High |
| **Phase 3** | Security & Multi-Tenancy | High | ⚡ High |
| **Phase 4** | Frontend UX Improvements | Medium | ⚡ High |
| **Phase 5** | Production & DevOps | High | ⚡ High |

---

## Phase 1 — Real-time Streaming & WebSockets

### 1.1 Streaming AI Responses (Server-Sent Events)

**Current State**
The AI triage pipeline (`POST /api/tickets/{id}/diagnose`) is a synchronous blocking call.
The frontend shows no progress while LangGraph runs — users see a frozen UI.

**Goal**
Stream LangGraph agent node transitions live to the frontend so users see:
```
→ Evaluator running...
→ Retrieving context from knowledge base... (3 chunks found)
→ Writer drafting response...
→ Auditor reviewing draft...
→ ✅ Resolved
```

**Implementation Plan**

Backend — add SSE streaming endpoint:
```python
# backend/app/api/routes/tickets.py
from fastapi.responses import StreamingResponse
import asyncio

@router.get("/{ticket_id}/diagnose/stream")
async def stream_triage(ticket_id: int, ...):
    async def event_generator():
        yield f"data: {json.dumps({'step': 'evaluator', 'status': 'running'})}\n\n"
        # run evaluator node...
        yield f"data: {json.dumps({'step': 'writer', 'status': 'running'})}\n\n"
        # run writer node...
        yield f"data: {json.dumps({'step': 'done', 'resolution': '...'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Frontend — consume SSE stream:
```typescript
// Replace fetch() with EventSource in Workspace.tsx
const es = new EventSource(`${API_BASE}/tickets/${id}/diagnose/stream`);
es.onmessage = (e) => {
  const data = JSON.parse(e.data);
  setAgentSteps(prev => [...prev, data]);
};
```

**Files to Modify**
- `backend/app/api/routes/tickets.py` — add `/diagnose/stream` SSE endpoint
- `backend/app/services/agent_service.py` — expose per-node async generator
- `frontend/src/pages/Workspace.tsx` — replace fetch with EventSource + step animation

**Effort**: 3–4 days

---

### 1.2 WebSocket Live Ticket Updates

**Current State**
The Dashboard polls for ticket updates only on page load. Status changes made by another user (e.g. an admin triaging a ticket) are invisible until refresh.

**Goal**
Push real-time ticket status updates to all connected clients via WebSocket.

**Implementation Plan**

```python
# backend/app/api/routes/ws.py  [NEW FILE]
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    async def broadcast(self, message: dict):
        for ws in self.active:
            await ws.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/tickets")
async def ticket_updates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        manager.active.remove(websocket)
```

Then broadcast after every status change in `tickets.py`:
```python
await manager.broadcast({"type": "ticket_updated", "ticket_id": ticket.id, "status": ticket.status})
```

**Files to Create/Modify**
- `backend/app/api/routes/ws.py` — [NEW] WebSocket connection manager
- `backend/app/main.py` — include WebSocket router
- `frontend/src/context/SocketContext.tsx` — [NEW] WebSocket context
- `frontend/src/pages/Dashboard.tsx` — subscribe to ticket updates

**Effort**: 2–3 days

---

## Phase 2 — Knowledge Base Upgrades

### 2.1 File Upload Ingestion (PDF, DOCX, TXT)

**Current State**
Documents can only be ingested via JSON body (`POST /api/ingest` with `title` + `content`).
Users must manually copy-paste document text.

**Goal**
Allow file uploads directly from the UI — upload a PDF/DOCX/TXT and have it automatically extracted, chunked, and embedded.

**Implementation Plan**

```python
# backend/app/api/routes/ingest.py — add file upload endpoint
from fastapi import UploadFile, File
import pypdf          # pip install pypdf
import docx           # pip install python-docx

@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    content = await file.read()

    if file.filename.endswith(".pdf"):
        text = extract_pdf(content)
    elif file.filename.endswith(".docx"):
        text = extract_docx(content)
    else:
        text = content.decode("utf-8")

    # same chunk → embed → store flow as existing ingest
```

**New Dependencies**
```
pypdf>=3.0.0
python-docx>=1.0.0
```

**Files to Create/Modify**
- `backend/app/api/routes/ingest.py` — add `POST /ingest/upload` endpoint
- `backend/app/services/file_extractor.py` — [NEW] PDF/DOCX text extraction
- `backend/requirements.txt` — add `pypdf`, `python-docx`
- `frontend/src/pages/Settings.tsx` — add file upload UI with drag-and-drop

**Effort**: 2–3 days

---

### 2.2 Knowledge Base Management UI

**Current State**
Documents ingested into the KB have no visibility or management. There is no way to view, search, or delete documents from the frontend.

**Goal**
Add a **Knowledge Base** page to the frontend with:
- List of all ingested documents (title, chunk count, date added)
- Search/filter
- Delete document (cascades to chunks)
- Preview document content

**Implementation Plan**

Backend:
```python
# backend/app/api/routes/ingest.py — add management endpoints
@router.get("/documents")          # list all documents
@router.get("/documents/{id}")     # get document + chunk count
@router.delete("/documents/{id}")  # delete document + chunks
```

Frontend:
```typescript
// frontend/src/pages/KnowledgeBase.tsx  [NEW]
// - Document list with pagination
// - Upload button → triggers file upload modal
// - Delete confirmation dialog
```

**Files to Create/Modify**
- `backend/app/api/routes/ingest.py` — add GET/DELETE document routes
- `frontend/src/pages/KnowledgeBase.tsx` — [NEW] KB management page
- `frontend/src/App.tsx` — add 'knowledge-base' to ViewState type
- `frontend/src/components/Header.tsx` — add KB nav link

**Effort**: 2–3 days

---

### 2.3 Improve Embedding Dimensions

**Current State**
The system truncates NIM embeddings from 4096 → 128 dimensions, losing significant semantic information. The `DocumentChunk.embedding` column is `Vector(128)`.

**Goal**
Upgrade to full 1536-dimension embeddings (OpenAI `text-embedding-3-small` native size) for richer semantic search.

**Implementation Plan**

1. Create a new Alembic migration to change the column size:
```python
# migrations/versions/xxxx_upgrade_embedding_dimensions.py
op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)")
```

2. Update the model:
```python
# backend/app/models/document.py
embedding = Column(Vector(1536), nullable=False)  # was Vector(128)
```

3. Update `embedding_service.py` — remove truncation, use full vector.

4. Re-embed all existing documents (provide migration script).

> ⚠️ **Breaking change** — requires re-ingesting all existing documents.

**Files to Modify**
- `backend/app/models/document.py` — Vector(128) → Vector(1536)
- `backend/app/services/embedding_service.py` — remove truncation logic
- `backend/migrations/versions/` — [NEW] migration for column resize
- `backend/scripts/reembed_all.py` — [NEW] re-embedding utility script

**Effort**: 1–2 days

---

## Phase 3 — Security & Multi-Tenancy

### 3.1 Organisation / Workspace Multi-Tenancy

**Current State**
All users share a single flat namespace. There is no concept of organisations — an admin sees ALL tickets from ALL users in the system.

**Goal**
Add an `Organisation` model so users belong to an org. Tickets, documents, and analytics are scoped per org. One user can be admin of their own org.

**Database Schema**

```python
# backend/app/models/organisation.py  [NEW]
class Organisation(Base):
    __tablename__ = "organisations"
    id         = Column(Integer, primary_key=True)
    name       = Column(String, nullable=False)
    slug       = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, ...)
    members    = relationship("User", back_populates="organisation")
    documents  = relationship("Document", back_populates="organisation")

# Add to User model:
organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
org_role        = Column(String, default="member")  # "owner", "admin", "member"
```

**Files to Create/Modify**
- `backend/app/models/organisation.py` — [NEW]
- `backend/app/models/user.py` — add `organisation_id`, `org_role`
- `backend/app/models/ticket.py` — add `organisation_id`
- `backend/app/models/document.py` — add `organisation_id`
- `backend/app/api/routes/auth.py` — accept `organisation_slug` on register
- All query endpoints — add `organisation_id` filter to every DB query
- `backend/migrations/versions/` — [NEW] add organisations table migration

**Effort**: 5–7 days

---

### 3.2 API Rate Limiting

**Current State**
No rate limiting exists. The AI endpoints (`/diagnose`, `/query`) call external LLM APIs on every request — a user could spam them and run up API costs.

**Goal**
Add per-user rate limiting on expensive AI endpoints.

**Implementation Plan**

```python
# pip install slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# backend/app/api/routes/tickets.py
@router.post("/{ticket_id}/diagnose")
@limiter.limit("10/minute")   # max 10 AI calls per minute per IP
async def run_triage_diagnose_pipeline(...):
    ...
```

**New Dependency**: `slowapi>=0.1.9`

**Files to Modify**
- `backend/app/main.py` — attach SlowAPI middleware
- `backend/app/api/routes/tickets.py` — add `@limiter.limit` to `/diagnose`
- `backend/app/api/routes/query.py` — add `@limiter.limit` to `/query`
- `backend/requirements.txt` — add `slowapi`

**Effort**: 1 day

---

### 3.3 Password Change & Token Refresh

**Current State**
Users cannot change their password after registration. JWT tokens have a fixed 24-hour expiry with no refresh mechanism — users are simply logged out.

**Goal**
Add `POST /auth/change-password` and `POST /auth/refresh` endpoints.

**Implementation Plan**

```python
# backend/app/api/routes/auth.py

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
def change_password(payload: PasswordChangeRequest, current_user=Depends(get_current_user), db=Depends(get_db)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(401, "Current password is incorrect.")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully."}

@router.post("/refresh")
def refresh_token(current_user=Depends(get_current_user)):
    new_token = create_access_token(subject=current_user.email)
    return {"access_token": new_token, "token_type": "bearer"}
```

**Files to Modify**
- `backend/app/api/routes/auth.py` — add `change-password` and `refresh` endpoints
- `frontend/src/context/AuthContext.tsx` — add auto-refresh logic before token expiry
- `frontend/src/pages/Settings.tsx` — add password change form

**Effort**: 1–2 days

---

### 3.4 Email Notifications

**Current State**
No notifications are sent when tickets are resolved, escalated, or clarification is needed. Users must manually check the dashboard.

**Goal**
Send email notifications on key ticket status changes.

**Implementation Plan**

```python
# backend/app/services/email_service.py  [NEW]
import smtplib
from email.mime.text import MIMEText

async def send_ticket_resolved_email(to_email: str, ticket_title: str, resolution: str):
    msg = MIMEText(f"Your ticket '{ticket_title}' has been resolved.\n\n{resolution}")
    msg["Subject"] = f"✅ Ticket Resolved: {ticket_title}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    # send via SMTP...

# Called in tickets.py after resolution:
await send_ticket_resolved_email(ticket.user.email, ticket.title, response_text)
```

**New Config Variables** (add to `.env.example`):
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@resolveai.com
```

**Files to Create/Modify**
- `backend/app/services/email_service.py` — [NEW]
- `backend/app/core/config.py` — add SMTP settings
- `backend/app/api/routes/tickets.py` — call email service on Resolved/Escalated/Clarify
- `backend/.env.example` — add SMTP config template

**Effort**: 1–2 days

---

## Phase 4 — Frontend UX Improvements

### 4.1 React Router — URL-based Navigation

**Current State**
Navigation is state-based (`useState<ViewState>`). URLs don't change when navigating — you can't bookmark the workspace for ticket #42, share a link, or use the browser back button.

**Goal**
Migrate to React Router v7 for proper URL-based navigation:
```
/                   → Dashboard
/tickets/:id        → Workspace for a specific ticket
/knowledge-base     → KB management page
/settings           → User settings
```

**Implementation Plan**

`react-router-dom` is already installed. The migration replaces manual state with routes:

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/tickets/:id" element={<Workspace />} />
      <Route path="/knowledge-base" element={<KnowledgeBase />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  </BrowserRouter>
);
```

**Files to Modify**
- `frontend/src/App.tsx` — replace ViewState with BrowserRouter + Routes
- `frontend/src/pages/Dashboard.tsx` — replace `onSelectProblem(id)` with `navigate('/tickets/:id')`
- `frontend/src/pages/Workspace.tsx` — read `id` from `useParams()` instead of props
- `frontend/src/components/Header.tsx` — use NavLink instead of onNavigate callback
- `frontend/vite.config.ts` — add `historyApiFallback: true` for SPA routing

**Effort**: 2 days

---

### 4.2 Paginated Ticket List

**Current State**
`GET /api/tickets/` returns all tickets as a flat array. If a user has 500 tickets, all 500 are loaded at once.

**Goal**
Add server-side pagination with `page` and `limit` query params. Frontend shows paginated list with Previous/Next controls.

**Implementation Plan**

```python
# backend/app/api/routes/tickets.py
@router.get("/")
def list_tickets(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    ...
):
    offset = (page - 1) * limit
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status)
    total = query.count()
    tickets = query.offset(offset).limit(limit).all()

    return {
        "items": [...],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit)
    }
```

**Files to Modify**
- `backend/app/api/routes/tickets.py` — add pagination + status filter query params
- `frontend/src/pages/Dashboard.tsx` — add pagination controls and status filter dropdown

**Effort**: 1–2 days

---

### 4.3 Advanced Analytics Dashboard

**Current State**
Analytics shows basic counts (`status_counts`, `category_counts`), resolution rate, and last 5 activity logs.

**Goal**
Add time-series charts and deeper metrics:
- Tickets created per day (last 30 days) — line chart
- Average resolution time per category — bar chart
- Escalation rate trend — area chart
- Top 5 most common ticket categories — pie chart

**Implementation Plan**

```python
# backend/app/api/routes/analytics.py — add time-series endpoint
from sqlalchemy import func

@router.get("/timeseries")
def get_timeseries(days: int = 30, db=Depends(get_db), current_user=...):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    daily = (
        db.query(
            func.date(Ticket.created_at).label("date"),
            func.count(Ticket.id).label("count")
        )
        .filter(Ticket.created_at >= cutoff)
        .group_by(func.date(Ticket.created_at))
        .all()
    )
    return [{"date": str(row.date), "count": row.count} for row in daily]
```

**Files to Modify**
- `backend/app/api/routes/analytics.py` — add `/analytics/timeseries` and `/analytics/resolution-time`
- `frontend/src/pages/Dashboard.tsx` — wire new Recharts graphs (LineChart, BarChart, PieChart)

**Effort**: 2–3 days

---

### 4.4 Ticket Attachment Support

**Current State**
Tickets only have `title` and `description` text fields. Customers cannot attach screenshots, error logs, or supporting files.

**Goal**
Allow file attachments on tickets (images, logs, PDFs — max 10MB).

**Database Change**

```python
# backend/app/models/attachment.py  [NEW]
class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    id         = Column(Integer, primary_key=True)
    ticket_id  = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    filename   = Column(String, nullable=False)
    file_path  = Column(String, nullable=False)
    mime_type  = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, ...)
    ticket     = relationship("Ticket", back_populates="attachments")
```

**Files to Create/Modify**
- `backend/app/models/attachment.py` — [NEW]
- `backend/app/api/routes/tickets.py` — `POST /tickets/{id}/attachments`, `GET /tickets/{id}/attachments/{file}`
- `backend/app/models/ticket.py` — add `attachments` relationship
- `backend/migrations/versions/` — [NEW] add attachments table
- `frontend/src/pages/Workspace.tsx` — add file upload + attachment preview

**Effort**: 3–4 days

---

## Phase 5 — Production & DevOps

### 5.1 Full Docker Compose Stack

**Current State**
`docker-compose.yml` only starts the PostgreSQL container. The backend and frontend must be started manually.

**Goal**
One `docker-compose up` command starts the entire stack: DB + Backend + Frontend.

**New `docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: resolve_ai
    ports:
      - "5432:5432"
    volumes:
      - resolveai_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    depends_on:
      postgres:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - backend

volumes:
  resolveai_pgdata:
```

**Files to Create/Modify**
- `docker-compose.yml` — rewrite to include all 3 services
- `backend/Dockerfile` — [NEW] Python FastAPI container
- `frontend/Dockerfile` — [NEW] Nginx + React build container
- `frontend/nginx.conf` — [NEW] Nginx SPA routing config

**Effort**: 2 days

---

### 5.2 Automated Testing Suite

**Current State**
There are manual test scripts (`test_e2e_real.py`, `test_login.py`, `test_req.py`) but no automated test framework. CI cannot validate PRs.

**Goal**
Add `pytest` unit + integration tests covering the core pipeline.

**Test Structure**

```
backend/tests/
├── conftest.py          # DB fixtures, test client setup
├── test_auth.py         # register, login, token refresh
├── test_tickets.py      # CRUD, triage pipeline (mock LLM)
├── test_ingest.py       # document ingestion, chunking
├── test_retrieval.py    # pgvector similarity search
└── test_agent.py        # LangGraph node unit tests
```

**New Dependencies**
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0      # async test client for FastAPI
```

**Files to Create**
- `backend/tests/` — [NEW] full test directory
- `backend/tests/conftest.py` — SQLite in-memory test DB fixture
- `backend/tests/test_auth.py`, `test_tickets.py`, etc.
- `.github/workflows/ci.yml` — [NEW] GitHub Actions CI on every PR

**Effort**: 4–5 days

---

### 5.3 GitHub Actions CI/CD Pipeline

**Goal**
Automatically run tests and linting on every pull request. Auto-deploy on merge to `main`.

```yaml
# .github/workflows/ci.yml  [NEW]
name: CI
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "18" }
      - run: cd frontend && npm ci && npm run lint && npm run build
```

**Files to Create**
- `.github/workflows/ci.yml` — [NEW]
- `.github/workflows/deploy.yml` — [NEW] (optional deploy step)

**Effort**: 1 day

---

### 5.4 Logging & Observability

**Current State**
Logging uses basic `logging.getLogger()` with no structured output. No request tracing, error aggregation, or performance metrics exist.

**Goal**
Add structured JSON logging, request ID tracing, and a Prometheus metrics endpoint.

**Implementation Plan**

```python
# backend/app/core/logging.py  [NEW]
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

# Middleware to attach request_id to every log
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
    return response
```

**New Dependencies**
```
structlog>=24.0.0
prometheus-fastapi-instrumentator>=7.0.0
```

**Files to Create/Modify**
- `backend/app/core/logging.py` — [NEW] structured logging config
- `backend/app/main.py` — attach logging middleware + Prometheus instrumentator
- `backend/requirements.txt` — add `structlog`, `prometheus-fastapi-instrumentator`

**Effort**: 1–2 days

---

## ⚡ Quick-Win Enhancements (< 1 day each)

These are small standalone improvements requiring minimal effort:

| # | Enhancement | Where | Impact |
|---|-------------|-------|--------|
| QW-1 | Add `updated_at` field to `DocumentChunk` model | `models/document.py` | Debugging |
| QW-2 | Fix `settings.py` L24 — `has_openai_key` incorrectly checks `NVIDIA_NIM_API_KEY` | `routes/settings.py` | Accuracy |
| QW-3 | Add `GET /api/tickets/?status=` filter param | `routes/tickets.py` | Usability |
| QW-4 | Add ticket search by keyword (`?search=`) | `routes/tickets.py` | Usability |
| QW-5 | Pin all package versions in `requirements.txt` | `requirements.txt` | Stability |
| QW-6 | Add `@app.exception_handler(Exception)` global handler | `app/main.py` | Reliability |
| QW-7 | Move hardcoded chunk size (500/100) to config | `config.py` + `chunking.py` | Flexibility |
| QW-8 | Add token auto-refresh in `AuthContext.tsx` before expiry | `context/AuthContext.tsx` | UX |
| QW-9 | Add `Content-Disposition` header to export endpoint | `routes/tickets.py` | UX |
| QW-10 | Add loading skeleton components in Dashboard | `pages/Dashboard.tsx` | UX |

---

## 📅 Recommended Next Sprint (2 Weeks)

Based on user impact vs. effort:

**Week 1**
- [ ] QW-1 through QW-6 (quick wins — 1 day total)
- [ ] Phase 1.1 — Streaming AI responses (3 days)
- [ ] Phase 4.1 — React Router migration (2 days)

**Week 2**
- [ ] Phase 2.1 — File upload ingestion (3 days)
- [ ] Phase 3.2 — Rate limiting (1 day)
- [ ] Phase 3.3 — Password change + token refresh (2 days)
- [ ] Phase 5.3 — GitHub Actions CI (1 day)
