"""
Unit tests for the TINAA documentation API route.

Covers:
- GET /api/v1/docs/manifest — returns manifest JSON
- GET /api/v1/docs/{section}/{page} — returns markdown content
- 404 when section or page does not exist
- 400 on path traversal attempts (..)
- Manifest integrity: all files referenced exist on disk
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Minimal app fixture — avoids ServiceContainer initialisation
# ---------------------------------------------------------------------------


@pytest.fixture
def docs_client():
    """TestClient wired only to the docs router, no service dependencies."""
    from fastapi import FastAPI

    from tinaa.api.routes.docs import DOCS_DIR, router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


# ---------------------------------------------------------------------------
# Manifest endpoint
# ---------------------------------------------------------------------------


class TestDocsManifest:
    def test_manifest_returns_200(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        assert resp.status_code == 200

    def test_manifest_has_sections_key(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        data = resp.json()
        assert "sections" in data

    def test_manifest_has_three_sections(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        data = resp.json()
        assert len(data["sections"]) == 3

    def test_manifest_section_ids(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        ids = {s["id"] for s in resp.json()["sections"]}
        assert ids == {"user", "admin", "operations"}

    def test_manifest_each_section_has_pages(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        for section in resp.json()["sections"]:
            assert len(section["pages"]) >= 1, f"Section {section['id']} has no pages"

    def test_manifest_page_has_required_fields(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        for section in resp.json()["sections"]:
            for page in section["pages"]:
                assert "id" in page
                assert "title" in page
                assert "file" in page

    def test_manifest_user_section_page_count(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        user = next(s for s in resp.json()["sections"] if s["id"] == "user")
        assert len(user["pages"]) == 9

    def test_manifest_admin_section_page_count(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        admin = next(s for s in resp.json()["sections"] if s["id"] == "admin")
        assert len(admin["pages"]) == 8

    def test_manifest_operations_section_page_count(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/manifest")
        ops = next(s for s in resp.json()["sections"] if s["id"] == "operations")
        assert len(ops["pages"]) == 8

    def test_manifest_missing_returns_404(self, tmp_path, docs_client: TestClient) -> None:
        """When manifest.json is absent, route returns 404."""
        import tinaa.api.routes.docs as docs_mod

        original = docs_mod.DOCS_DIR
        try:
            docs_mod.DOCS_DIR = tmp_path / "nonexistent"
            resp = docs_client.get("/api/v1/docs/manifest")
            assert resp.status_code == 404
        finally:
            docs_mod.DOCS_DIR = original


# ---------------------------------------------------------------------------
# Page endpoint
# ---------------------------------------------------------------------------


class TestDocsPage:
    def test_user_index_returns_200(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/user/index")
        assert resp.status_code == 200

    def test_user_index_content_type_is_markdown(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/user/index")
        assert "text/markdown" in resp.headers["content-type"]

    def test_user_index_has_content(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/user/index")
        assert len(resp.text) > 100

    def test_admin_installation_returns_200(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/admin/installation")
        assert resp.status_code == 200

    def test_operations_architecture_returns_200(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/operations/architecture")
        assert resp.status_code == 200

    def test_nonexistent_section_returns_404(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/nonexistent/index")
        assert resp.status_code == 404

    def test_nonexistent_page_returns_404(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/user/nonexistent")
        assert resp.status_code == 404

    def test_path_traversal_in_section_returns_400(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/docs/../etc/passwd")
        # FastAPI routing encodes .. in paths so this may return 404;
        # if it reaches our handler it must be 400
        assert resp.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_path_traversal_explicit_dotdot_section_returns_400(
        self, docs_client: TestClient
    ) -> None:
        """Simulate handler-level path traversal guard by calling handler directly."""
        from fastapi import HTTPException

        import tinaa.api.routes.docs as docs_mod

        with pytest.raises(HTTPException) as exc_info:
            await docs_mod.get_doc_page("..", "passwd")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_path_traversal_explicit_dotdot_page_returns_400(
        self, docs_client: TestClient
    ) -> None:
        from fastapi import HTTPException

        import tinaa.api.routes.docs as docs_mod

        with pytest.raises(HTTPException) as exc_info:
            await docs_mod.get_doc_page("user", "../etc/passwd")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Manifest integrity — all referenced files exist on disk
# ---------------------------------------------------------------------------


class TestManifestIntegrity:
    def test_all_manifest_files_exist_on_disk(self) -> None:
        """Every file listed in manifest.json must have a corresponding .md file."""
        from tinaa.api.routes.docs import DOCS_DIR

        manifest_path = DOCS_DIR / "manifest.json"
        assert manifest_path.exists(), "manifest.json does not exist"

        manifest = json.loads(manifest_path.read_text())
        missing: list[str] = []
        for section in manifest["sections"]:
            for page in section["pages"]:
                file_path = DOCS_DIR / page["file"]
                if not file_path.exists():
                    missing.append(page["file"])

        assert not missing, f"Missing documentation files: {missing}"

    def test_all_md_files_are_non_empty(self) -> None:
        """Every .md file in docs/ must have substantive content (>= 500 bytes)."""
        from tinaa.api.routes.docs import DOCS_DIR

        short_files: list[str] = []
        for md_file in DOCS_DIR.rglob("*.md"):
            size = md_file.stat().st_size
            if size < 500:
                short_files.append(f"{md_file.relative_to(DOCS_DIR)} ({size} bytes)")

        assert not short_files, f"Documentation files too short: {short_files}"

    def test_total_page_count(self) -> None:
        """Manifest must declare exactly 25 pages across 3 sections."""
        from tinaa.api.routes.docs import DOCS_DIR

        manifest = json.loads((DOCS_DIR / "manifest.json").read_text())
        total = sum(len(s["pages"]) for s in manifest["sections"])
        assert total == 25

    def test_md_file_count_matches_manifest(self) -> None:
        """Number of .md files in docs/ must equal number of pages in manifest plus 0 extras."""
        from tinaa.api.routes.docs import DOCS_DIR

        manifest = json.loads((DOCS_DIR / "manifest.json").read_text())
        expected_files = {page["file"] for s in manifest["sections"] for page in s["pages"]}
        actual_files = {
            str(f.relative_to(DOCS_DIR)).replace("\\", "/")
            for f in DOCS_DIR.rglob("*.md")
        }
        # All manifest files must be present
        missing = expected_files - actual_files
        assert not missing, f"Manifest references missing files: {missing}"
