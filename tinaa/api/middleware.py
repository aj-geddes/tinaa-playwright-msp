"""API middleware for authentication, logging, and error handling."""

import logging
import os
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Public endpoints that never require an API key.
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/",
        "/api/docs",
        "/api/redoc",
        "/api/v1/webhooks/github",
        "/openapi.json",
    }
)

# Set of accepted API keys (populated from environment / tests).
VALID_API_KEYS: set[str] = set(filter(None, os.environ.get("TINAA_API_KEYS", "").split(",")))

# When True the middleware enforces key presence on protected routes.
API_KEY_REQUIRED: bool = os.environ.get("TINAA_API_KEY_REQUIRED", "false").lower() == "true"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing and inject X-Response-Time header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate API key for non-public endpoints.

    Checks X-API-Key header or Authorization: Bearer <token>.
    Skips validation for /health, /api/docs, /api/redoc, /api/v1/webhooks/github.
    When API_KEY_REQUIRED is False (default) the middleware allows all requests
    so the service works out of the box without configuration.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Always allow public paths.
        if path in PUBLIC_PATHS or path.startswith("/api/docs") or path.startswith("/api/redoc"):
            return await call_next(request)

        # If enforcement is disabled, pass through.
        if not API_KEY_REQUIRED:
            return await call_next(request)

        # Attempt to extract key from headers.
        api_key = request.headers.get("X-API-Key")
        if api_key is None:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                api_key = auth[len("Bearer ") :]

        if api_key and api_key in VALID_API_KEYS:
            return await call_next(request)

        return Response(
            content='{"detail":"Unauthorized"}',
            status_code=401,
            media_type="application/json",
        )
