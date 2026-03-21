"""FastAPI routes to serve the TINAA MSP frontend SPA.

Mounts the static directory at /static and serves index.html for all
non-API paths so the client-side router can handle navigation.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

router = APIRouter()

# Absolute path to the frontend package directory (this file's parent).
FRONTEND_DIR = Path(__file__).parent


@router.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the SPA shell (index.html) for the root path."""
    return FileResponse(FRONTEND_DIR / "templates" / "index.html")


def setup_frontend(app) -> None:  # type: ignore[type-arg]
    """Mount frontend static files and register the root route.

    Call this after all API routes have been registered so that the
    wildcard / route does not shadow any /api/* paths.

    Args:
        app: The FastAPI application instance.
    """
    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIR / "static"),
        name="static",
    )
    app.include_router(router)
