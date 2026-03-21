"""Unit tests for TINAA frontend routes.

Covers:
- setup_frontend imports and exposes the correct symbols
- serve_frontend returns the index.html FileResponse
- Static files mount path is correct
- Router is included into the app
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Tests for the routes module
# ---------------------------------------------------------------------------


class TestSetupFrontend:
    """setup_frontend correctly mounts static files and registers routes."""

    def test_setup_frontend_is_importable(self):
        """setup_frontend can be imported from tinaa.frontend.routes."""
        from tinaa.frontend.routes import setup_frontend

        assert callable(setup_frontend)

    def test_router_is_importable(self):
        """router is an APIRouter instance exposed from tinaa.frontend.routes."""
        from fastapi import APIRouter

        from tinaa.frontend.routes import router

        assert isinstance(router, APIRouter)

    def test_setup_frontend_mounts_static_and_includes_router(self):
        """setup_frontend calls app.mount for /static and app.include_router."""
        from tinaa.frontend.routes import setup_frontend

        mock_app = MagicMock()
        setup_frontend(mock_app)

        # Static files must be mounted at /static
        mount_calls = [str(call) for call in mock_app.mount.call_args_list]
        assert any("/static" in c for c in mount_calls), (
            f"Expected /static mount, got: {mount_calls}"
        )

        # Router must be included
        assert mock_app.include_router.called, "Expected include_router to be called"

    def test_frontend_dir_exists(self):
        """The FRONTEND_DIR referenced by routes.py must exist on disk."""
        from tinaa.frontend.routes import FRONTEND_DIR

        assert FRONTEND_DIR.exists(), f"FRONTEND_DIR does not exist: {FRONTEND_DIR}"
        assert FRONTEND_DIR.is_dir(), f"FRONTEND_DIR is not a directory: {FRONTEND_DIR}"

    def test_templates_dir_exists(self):
        """templates/ sub-directory must exist within FRONTEND_DIR."""
        from tinaa.frontend.routes import FRONTEND_DIR

        templates_dir = FRONTEND_DIR / "templates"
        assert templates_dir.exists(), f"templates dir not found: {templates_dir}"

    def test_index_html_exists(self):
        """index.html must exist inside the templates directory."""
        from tinaa.frontend.routes import FRONTEND_DIR

        index_path = FRONTEND_DIR / "templates" / "index.html"
        assert index_path.exists(), f"index.html not found: {index_path}"

    def test_static_dir_exists(self):
        """static/ sub-directory must exist within FRONTEND_DIR."""
        from tinaa.frontend.routes import FRONTEND_DIR

        static_dir = FRONTEND_DIR / "static"
        assert static_dir.exists(), f"static dir not found: {static_dir}"


class TestServeFrontend:
    """serve_frontend returns a FileResponse pointing to index.html."""

    def test_serve_frontend_returns_file_response(self):
        """GET / returns 200 and serves index.html via TestClient."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from tinaa.frontend.routes import FRONTEND_DIR, router

        # We need the static dir and index.html to exist for FileResponse
        index_path = FRONTEND_DIR / "templates" / "index.html"
        assert index_path.exists(), f"index.html must exist: {index_path}"

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_serve_frontend_content_type_html(self):
        """serve_frontend response has HTML content type."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from tinaa.frontend.routes import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/")
        assert "text/html" in response.headers.get("content-type", "")

    def test_serve_frontend_contains_spa_shell(self):
        """index.html content includes the SPA shell markers."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from tinaa.frontend.routes import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/")
        body = response.text

        assert "TINAA" in body, "Expected TINAA branding in index.html"
        assert "main-content" in body, "Expected main-content element in index.html"
        assert "app.js" in body, "Expected app.js script tag in index.html"


class TestFrontendFileStructure:
    """All expected static files must exist on disk."""

    def _frontend_dir(self) -> Path:
        from tinaa.frontend.routes import FRONTEND_DIR

        return FRONTEND_DIR

    def test_app_css_exists(self):
        assert (self._frontend_dir() / "static" / "css" / "app.css").exists()

    def test_app_js_exists(self):
        assert (self._frontend_dir() / "static" / "js" / "app.js").exists()

    def test_api_js_exists(self):
        assert (self._frontend_dir() / "static" / "js" / "api.js").exists()

    def test_nav_component_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "components" / "nav.js"
        ).exists()

    def test_header_component_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "components" / "header.js"
        ).exists()

    def test_quality_score_component_exists(self):
        assert (
            self._frontend_dir()
            / "static"
            / "js"
            / "components"
            / "quality-score.js"
        ).exists()

    def test_metric_card_component_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "components" / "metric-card.js"
        ).exists()

    def test_product_card_component_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "components" / "product-card.js"
        ).exists()

    def test_alert_banner_component_exists(self):
        assert (
            self._frontend_dir()
            / "static"
            / "js"
            / "components"
            / "alert-banner.js"
        ).exists()

    def test_playbook_list_component_exists(self):
        assert (
            self._frontend_dir()
            / "static"
            / "js"
            / "components"
            / "playbook-list.js"
        ).exists()

    def test_test_run_table_component_exists(self):
        assert (
            self._frontend_dir()
            / "static"
            / "js"
            / "components"
            / "test-run-table.js"
        ).exists()

    def test_endpoint_status_component_exists(self):
        assert (
            self._frontend_dir()
            / "static"
            / "js"
            / "components"
            / "endpoint-status.js"
        ).exists()

    def test_docs_viewer_component_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "components" / "docs-viewer.js"
        ).exists()

    def test_dashboard_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "dashboard.js"
        ).exists()

    def test_product_detail_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "product-detail.js"
        ).exists()

    def test_playbooks_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "playbooks.js"
        ).exists()

    def test_metrics_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "metrics.js"
        ).exists()

    def test_test_runs_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "test-runs.js"
        ).exists()

    def test_alerts_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "alerts.js"
        ).exists()

    def test_settings_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "settings.js"
        ).exists()

    def test_docs_page_exists(self):
        assert (
            self._frontend_dir() / "static" / "js" / "pages" / "docs.js"
        ).exists()


class TestFrontendInitPy:
    """__init__.py package marker must exist."""

    def test_init_py_exists(self):
        from tinaa.frontend.routes import FRONTEND_DIR

        assert (FRONTEND_DIR / "__init__.py").exists()


class TestIndexHtmlAccessibility:
    """index.html must contain required accessibility markers."""

    def _get_index_content(self) -> str:
        from tinaa.frontend.routes import FRONTEND_DIR

        return (FRONTEND_DIR / "templates" / "index.html").read_text()

    def test_has_skip_to_content_link(self):
        content = self._get_index_content()
        assert "skip" in content.lower(), "Expected skip-to-content link"

    def test_has_lang_attribute(self):
        content = self._get_index_content()
        assert 'lang="en"' in content, "Expected lang=en on html element"

    def test_has_viewport_meta(self):
        content = self._get_index_content()
        assert "viewport" in content, "Expected viewport meta tag"

    def test_has_main_role(self):
        content = self._get_index_content()
        assert 'role="main"' in content or "<main" in content, (
            "Expected main landmark element"
        )

    def test_has_dark_mode_class(self):
        content = self._get_index_content()
        assert 'class="dark"' in content or "dark" in content, (
            "Expected dark mode class on html"
        )

    def test_has_tailwind_cdn(self):
        content = self._get_index_content()
        assert "tailwindcss.com" in content or "cdn.tailwindcss.com" in content, (
            "Expected Tailwind CDN script"
        )
