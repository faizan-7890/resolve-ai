# ResolveAI: AI Support Ticket Triage Resolver

ResolveAI is a production-grade customer support ticket triage workspace. It ingests company FAQs, policies, and documents, matches incoming support queries against a **PostgreSQL + pgvector** vector store, and utilizes a **LangGraph state workflow** to automatically answer, clarify, or escalate tickets.

Resolved tickets automatically feed back into the document store, creating a self-improving knowledge base.

---

## Key Features

1. **pgvector RAG Retrieval**: Computes similarity scores using 128-dimensional dense vectors to fetch relevant knowledge base documents.
2. **LangGraph Agentic Triage**: Multi-node StateGraph routing:
   - **Answer**: Automatically resolves the ticket with context-bounded facts and indexes the resolved case back into the database.
   - **Clarify**: Asks targeted questions to gather details when queries are ambiguous.
   - **Escalate**: Prompts manual senior agent reviews for complex or out-of-scope issues.
3. **Database Audit Trails**: Chronological activity logs recording all state transitions.
4. **Resilient Local Fallbacks**: High-performance local text-matching heuristics if NVIDIA NIM APIs are offline.
5. **Modern Glassmorphic React UI**: Sticky navigation, interactive dashboard metric boards, and responsive ticket workspace feeds.

---

## Repository Structure

```
resolve-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # REST API Routers
│   │   ├── core/            # Configuration & Database setup
│   │   ├── models/          # SQLAlchemy Models (User, Doc, Ticket, Logs)
│   │   ├── services/        # Chunking, Embeddings, pgvector, LangGraph Agent
│   │   └── main.py          # FastAPI server entrypoint
│   ├── migrations/          # Alembic database migrations
│   ├── scripts/             # Data seed script (seed_docs.py)
│   ├── run.py               # Uvicorn dev-server launcher
│   └── test_e2e_real.py     # E2E integration test pipeline
├── frontend/
│   ├── src/                 # React source code (components, pages, context)
│   └── package.json         # React NPM configurations
└── docker-compose.yml       # PostgreSQL database container configuration
```

---

## Quick Start Guide

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

---

### Step 1: Spin Up PostgreSQL Database
From the root folder `Projects/resolve-ai`, start the database container:
```bash
docker compose up -d
```
This launches a PostgreSQL 16 container pre-installed with the `pgvector` extension.

---

### Step 2: Set Up Backend Services
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Setup environment variables:
   Create a `.env` file in the `backend` directory (refer to `.env.example`):
   ```ini
   SECRET_KEY=dev-local-secret-key-not-for-production
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/resolve_ai
   NVIDIA_NIM_API_KEY=your_key_here
   ```
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Seed database with policies and test accounts:
   ```bash
   python scripts/seed_docs.py
   ```
   *Seeded accounts: `test@resolve.ai` / `testpassword123` (Standard) and `admin@resolve.ai` / `adminpassword123` (Admin).*

7. Launch FastAPI server:
   ```bash
   python run.py
   ```
   The backend API will be available at [http://localhost:8000](http://localhost:8000).

---

### Step 3: Set Up React Frontend
1. Navigate to the `frontend` directory:
   ```bash
   cd ../frontend
   ```
2. Install npm modules:
   ```bash
   npm install
   ```
3. Set up environment variables:
   Create a `.env` file:
   ```ini
   VITE_API_BASE=http://localhost:8000/api
   ```
4. Start the frontend:
   ```bash
   npm run dev
   ```
   The application will be accessible in your browser at [http://localhost:5173](http://localhost:5173).

---

## Testing & Verification

You can verify the backend RAG ingestion and LangGraph triage flow end-to-end:

1. Activate your virtual environment in `backend/`.
2. Run the integration test suite:
   ```bash
   python test_e2e_real.py
   ```
This test automatically verifies:
- Registration & login flow.
- Knowledge document ingestion, chunking, and embedding generation.
- Ticket workspace creation.
- Running the RAG triage pipeline and getting the correct routing output (`Answer`, `Clarify`, or `Escalate`).
- Logging resolutions back to the database as new searchable knowledge.
