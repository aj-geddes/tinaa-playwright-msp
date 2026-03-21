"""TINAA MSP FastAPI application factory."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure the TINAA MSP FastAPI application.

    Registers:
    - CORS middleware (permissive defaults; tighten per environment in production).
    - Request logging middleware with X-Response-Time header injection.
    - API key authentication middleware (enforced only when TINAA_API_KEY_REQUIRED=true).
    - All route modules under /api/v1.
    - WebSocket endpoint at /ws/{client_id}.
    """
    app = FastAPI(
        title="TINAA MSP API",
        description=(
            "Testing Intelligence Network Automation Assistant — Managed Service Platform"
        ),
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # ------------------------------------------------------------------ CORS
    _cors_origins = [
        origin.strip()
        for origin in os.environ.get(
            "TINAA_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
        ).split(",")
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    # ------------------------------------------------------ Custom middleware
    from tinaa.api.middleware import APIKeyMiddleware, RequestLoggingMiddleware

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(APIKeyMiddleware)

    # ----------------------------------------------------------- Route modules
    from tinaa.api.routes import (
        docs,
        health,
        metrics,
        playbooks,
        products,
        quality,
        test_runs,
        webhooks,
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(products.router, prefix="/api/v1", tags=["Products"])
    app.include_router(playbooks.router, prefix="/api/v1", tags=["Playbooks"])
    app.include_router(test_runs.router, prefix="/api/v1", tags=["Test Runs"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
    app.include_router(quality.router, prefix="/api/v1", tags=["Quality"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
    app.include_router(docs.router, prefix="/api/v1", tags=["Documentation"])

    # ------------------------------------------------------------ WebSocket
    from tinaa.api.websocket import setup_websocket

    setup_websocket(app)

    # ---------------------------------------------------------- Frontend SPA
    # Must be registered last so that the catch-all / route does not shadow
    # any /api/* or /health paths registered above.
    from tinaa.frontend.routes import setup_frontend

    setup_frontend(app)

    return app


def main():
    """Entry point for the tinaa API server."""
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8765)
