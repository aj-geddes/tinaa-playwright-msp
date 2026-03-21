"""Documentation API routes for TINAA MSP.

Serves the built-in documentation system. Markdown files are stored under
tinaa/frontend/static/docs/ and organised into three sections:
user, admin, and operations.

Routes:
    GET /docs/manifest       — Returns the documentation manifest (section + page listing)
    GET /docs/{section}/{page} — Returns a single documentation page as markdown
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()

DOCS_DIR = Path(__file__).parent.parent.parent / "frontend" / "static" / "docs"


@router.get(
    "/docs/manifest",
    summary="Get documentation manifest",
    description="Returns the documentation manifest listing all sections and pages.",
)
async def get_docs_manifest() -> dict:
    """Return the documentation manifest (section and page listing)."""
    manifest_path = DOCS_DIR / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Documentation manifest not found")
    return json.loads(manifest_path.read_text())


@router.get(
    "/docs/{section}/{page}",
    summary="Get documentation page",
    description="Returns a documentation page as markdown text.",
    response_class=PlainTextResponse,
)
async def get_doc_page(section: str, page: str) -> PlainTextResponse:
    """Return a single documentation page as markdown.

    Args:
        section: Documentation section — one of ``user``, ``admin``, ``operations``.
        page:    Page identifier, e.g. ``getting-started``.

    Raises:
        HTTPException 400: If section or page contains ``..`` (path traversal attempt).
        HTTPException 404: If the requested page does not exist.
    """
    if ".." in section or ".." in page:
        raise HTTPException(status_code=400, detail="Invalid path")

    file_path = DOCS_DIR / section / f"{page}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Page not found: {section}/{page}")

    return PlainTextResponse(file_path.read_text(), media_type="text/markdown")
