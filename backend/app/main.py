import json
import logging
import time
import uuid
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.middleware.rate_limiter import RateLimiter
from app.api.routes import auth, ingest, tickets, query, analytics, settings as settings_router, ws

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ResolveAI - AI Support Ticket Resolver",
    description="Support Ticket Resolver backend with RAG and agentic LangGraph triage.",
    version="2.0.0",
)

# Parse CORS origins from comma-separated config value
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

# Set up CORS middleware with restricted methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Add rate limiting middleware
app.add_middleware(RateLimiter)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Attach a correlation request ID and emit structured request timing logs."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        json.dumps({
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        })
    )
    return response


# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(tickets.router, prefix="/api/tickets")
app.include_router(ws.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path),
        },
    )


@app.get("/")
def read_root():
    return {"message": "Welcome to ResolveAI Support Ticket Resolver API Service."}


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Readiness probe verifying database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.error("Health check database failure: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable"},
        )
