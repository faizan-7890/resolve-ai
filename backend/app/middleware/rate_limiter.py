"""
Rate limiting middleware for ResolveAI.
Protects endpoints from abuse by limiting requests per IP/user.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import time
from typing import Dict, Tuple


class RateLimitConfig:
    """Configuration for rate limiting rules"""
    
    # Endpoint-specific limits (requests per minute)
    ENDPOINT_LIMITS = {
        "/api/ingest": 10,  # Document ingestion (resource-heavy)
        "/api/query": 30,  # Query endpoint (moderate load)
        "/api/auth/register": 5,  # Registration (abuse prevention)
        "/api/auth/login": 15,  # Login attempts
        "/api/tickets": 20,  # Ticket operations
        "default": 100,  # Default limit for other endpoints
    }
    
    # Time window in seconds
    WINDOW_SIZE = 60
    
    # Burst allowance (requests before throttling kicks in)
    BURST_SIZE = 2


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware using in-memory token bucket algorithm.
    Tracks requests per IP address.
    """
    
    def __init__(self, app):
        super().__init__(app)
        # {ip_address: {endpoint: token_count}}
        self.token_buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        # {ip_address: {endpoint: last_update_timestamp}}
        self.last_update: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    async def dispatch(self, request: Request, call_next):
        """Process request and apply rate limiting"""
        
        # Extract client IP (handle proxies)
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for certain paths
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get rate limit for this endpoint
        limit = self._get_rate_limit(request.url.path)
        
        # Check rate limit
        is_allowed = await self._check_rate_limit(client_ip, request.url.path, limit)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit info to response headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Window"] = str(RateLimitConfig.WINDOW_SIZE)
        
        return response

    async def _check_rate_limit(self, client_ip: str, endpoint: str, limit: int) -> bool:
        """
        Check if request is allowed using token bucket algorithm.
        Returns True if request is allowed, False otherwise.
        """
        current_time = time.time()
        
        # Initialize if client/endpoint is new
        is_new = (client_ip not in self.token_buckets) or (endpoint not in self.token_buckets[client_ip])
        
        if is_new:
            self.token_buckets[client_ip][endpoint] = float(limit)
            self.last_update[client_ip][endpoint] = current_time
            tokens = float(limit)
            elapsed = 0.0
        else:
            tokens = self.token_buckets[client_ip][endpoint]
            last_time = self.last_update[client_ip][endpoint]
            elapsed = max(0.0, current_time - last_time)
            
        refill_rate = limit / RateLimitConfig.WINDOW_SIZE  # tokens per second
        new_tokens = min(limit, tokens + (elapsed * refill_rate))
        
        if new_tokens >= 1:
            self.token_buckets[client_ip][endpoint] = new_tokens - 1
            self.last_update[client_ip][endpoint] = current_time
            return True
            
        return False

    def _get_rate_limit(self, path: str) -> int:
        """Get rate limit for a given endpoint path"""
        # Check exact match first
        if path in RateLimitConfig.ENDPOINT_LIMITS:
            return RateLimitConfig.ENDPOINT_LIMITS[path]
        
        # Check prefix match
        for endpoint_prefix, limit in RateLimitConfig.ENDPOINT_LIMITS.items():
            if endpoint_prefix != "default" and path.startswith(endpoint_prefix):
                return limit
        
        # Return default
        return RateLimitConfig.ENDPOINT_LIMITS["default"]

