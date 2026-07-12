from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.rate_limiter import RateLimiter
from app.api.routes import auth, ingest, tickets, query, analytics, settings as settings_router

app = FastAPI(
    title="ResolveAI - AI Support Ticket Resolver",
    description="Support Ticket Resolver backend with RAG and agentic LangGraph triage.",
    version="2.0.0"
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

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(tickets.router, prefix="/api/tickets")
app.include_router(tickets.router, prefix="/api/problems")
app.include_router(query.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to ResolveAI Support Ticket Resolver API Service."}
