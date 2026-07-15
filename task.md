# ResolveAI Sprint — Task Tracker

## Workstream 1 — Quick Wins
- [x] QW-1: Add `updated_at` to `DocumentChunk` model
- [x] QW-2: Fix `has_openai_key` / `has_nvidia_key` in settings route
- [x] QW-3: Add `?status=` filter to ticket list
- [x] QW-4: Add `?search=` keyword search to ticket list
- [x] QW-5: Pin `requirements.txt` versions
- [x] QW-6: Add global exception handler to `main.py`

## Workstream 2 — React Router Migration
- [x] Update `App.tsx` — BrowserRouter + Routes
- [x] Update `Dashboard.tsx` — useNavigate
- [x] Update `Workspace.tsx` — useParams
- [x] Update `Header.tsx` — NavLink

## Workstream 3 — SSE Streaming AI Triage
- [x] Refactor `agent_service.py` — async generator
- [x] Add `/diagnose/stream` SSE endpoint to `tickets.py`
- [x] Update `Workspace.tsx` — EventSource + step timeline UI

## Workstream 4 — Rate Limiting
- [x] Refine / fix standard custom rate limiter bucket state in `rate_limiter.py`
- [x] Ensure correct rate limiter routing integration
- [x] Support rate limiting on `/diagnose` and `/query` endpoints

## Workstream 5 — Password Change + Token Refresh
- [x] Add `POST /auth/change-password` endpoint
- [x] Add `POST /auth/refresh` endpoint
- [x] Add password change form to `Settings.tsx`
- [x] Add token auto-refresh to `AuthContext.tsx`

## Workstream 6 — File Upload Ingestion
- [x] Create `file_extractor.py` service
- [x] Add `POST /ingest/upload` endpoint
- [x] Add `pypdf` + `python-docx` to `requirements.txt`
- [x] Add file upload UI to `Settings.tsx`

## Workstream 7 — GitHub Actions CI
- [x] Create `backend/tests/conftest.py`
- [x] Create `backend/tests/test_auth.py`
- [x] Create `backend/tests/test_tickets.py`
- [x] Create `.github/workflows/ci.yml`
