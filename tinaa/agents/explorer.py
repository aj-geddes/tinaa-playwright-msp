"""
ExplorerAgent — explores codebases to build application models.
"""

from __future__ import annotations

import os
from typing import Any

from tinaa.agents.base import AgentTask, BaseAgent

# ---------------------------------------------------------------------------
# Framework fingerprints
# ---------------------------------------------------------------------------

# Files whose presence is strong evidence of a specific frontend framework.
_FRONTEND_SIGNALS: list[tuple[str, str]] = [
    ("next.config.js", "nextjs"),
    ("next.config.ts", "nextjs"),
    ("next.config.mjs", "nextjs"),
    ("angular.json", "angular"),
    (".angular-cli.json", "angular"),
    ("nuxt.config.js", "nuxtjs"),
    ("nuxt.config.ts", "nuxtjs"),
    ("svelte.config.js", "svelte"),
    ("svelte.config.ts", "svelte"),
    ("astro.config.mjs", "astro"),
    ("astro.config.ts", "astro"),
    ("vite.config.ts", "vite"),
    ("vite.config.js", "vite"),
    ("vue.config.js", "vue"),
]

# Files whose presence is strong evidence of a specific backend framework.
_BACKEND_SIGNALS: list[tuple[str, str]] = [
    ("manage.py", "django"),
    ("Gemfile", "rails"),
    ("mix.exs", "phoenix"),
    ("go.mod", "go"),
    ("Cargo.toml", "actix"),
    ("pom.xml", "spring"),
    ("build.gradle", "spring"),
    ("artisan", "laravel"),
    ("composer.json", "laravel"),
]

# Path fragments that hint at vue without a config file.
_VUE_PATH_HINTS = (".vue",)
_REACT_PATH_HINTS = (".jsx", ".tsx", "App.tsx", "App.jsx")
_EXPRESS_PATH_HINTS = ("server.js", "server.ts", "app.js", "app.ts")
_FLASK_PATH_HINTS = ("app.py", "wsgi.py", "run.py", "application.py")
_FASTAPI_PATH_HINTS = ("main.py", "asgi.py")

# Auth-related path fragments for journey inference.
_AUTH_PATH_HINTS = ("login", "signin", "sign-in", "auth", "logout", "register", "signup")


class ExplorerAgent(BaseAgent):
    """Explores codebases to build application models used by other agents."""

    def __init__(self) -> None:
        super().__init__("explorer")

    # ------------------------------------------------------------------
    # BaseAgent._run dispatch
    # ------------------------------------------------------------------

    async def _run(self, task: AgentTask) -> Any:
        action = task.action

        if action == "explore_codebase":
            return await self.explore_codebase(
                task.params.get("repo_path", ""),
                task.params.get("framework"),
            )

        if action == "analyze_diff":
            return await self.analyze_diff(
                task.params.get("changed_files", []),
                task.params.get("app_model", {}),
            )

        if action == "discover_routes":
            return await self._discover_routes(task.params.get("repo_path", ""))

        if action == "discover_apis":
            return await self._discover_apis(task.params.get("repo_path", ""))

        if action == "discover_forms":
            return await self._discover_forms(task.params.get("repo_path", ""))

        raise ValueError(f"ExplorerAgent has no handler for action '{action}'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def explore_codebase(self, repo_path: str, framework: str | None = None) -> dict:
        """Explore a codebase and build an application model.

        Returns a structured dict describing routes, endpoints, forms,
        auth flows, user journeys, and test coverage metadata.
        """
        self.logger.info("Exploring codebase at %s", repo_path)

        file_listing = self._list_files(repo_path)

        if framework:
            detected = await self._build_framework_from_hint(framework)
        else:
            detected = await self.detect_framework(file_listing)

        routes = self._infer_routes(file_listing)
        api_endpoints = self._infer_api_endpoints(file_listing)
        forms = self._infer_forms(file_listing)
        auth_flows = self._infer_auth_flows(file_listing)
        user_journeys = self._build_user_journeys(routes, auth_flows)
        static_assets = self._count_static_assets(file_listing)
        test_coverage = self._assess_test_coverage(file_listing)

        return {
            "framework": detected,
            "routes": routes,
            "api_endpoints": api_endpoints,
            "forms": forms,
            "auth_flows": auth_flows,
            "user_journeys": user_journeys,
            "static_assets": static_assets,
            "test_coverage": test_coverage,
        }

    async def analyze_diff(self, changed_files: list[dict], app_model: dict) -> dict:
        """Identify affected journeys and risk level from a set of changed files."""
        if not changed_files:
            return {
                "affected_routes": [],
                "affected_endpoints": [],
                "affected_journeys": [],
                "risk_level": "low",
                "suggested_tests": [],
            }

        routes = app_model.get("routes", [])
        journeys = app_model.get("user_journeys", [])

        changed_paths = [f.get("path", "") for f in changed_files]
        total_lines = sum(f.get("additions", 0) + f.get("deletions", 0) for f in changed_files)

        affected_routes = self._match_affected_routes(changed_paths, routes)
        affected_endpoints = self._match_affected_endpoints(changed_paths)
        affected_journeys = self._match_affected_journeys(changed_paths, affected_routes, journeys)
        risk_level = self._compute_risk_level(
            changed_files, total_lines, affected_routes, affected_journeys
        )
        suggested_tests = self._suggest_tests(affected_routes, affected_journeys, risk_level)

        return {
            "affected_routes": affected_routes,
            "affected_endpoints": affected_endpoints,
            "affected_journeys": affected_journeys,
            "risk_level": risk_level,
            "suggested_tests": suggested_tests,
        }

    async def detect_framework(self, file_listing: list[str]) -> dict:
        """Detect frontend and backend frameworks from a file listing.

        Uses presence of characteristic files to determine framework.
        Returns: {"frontend": str, "backend": str, "detected": bool}
        """
        basenames = {os.path.basename(p) for p in file_listing}

        frontend = "unknown"
        for filename, fw in _FRONTEND_SIGNALS:
            if filename in basenames:
                frontend = fw
                break

        # Vue without a vue.config.js but with .vue files
        if frontend == "unknown" and any(p.endswith(".vue") for p in file_listing):
            frontend = "vue"

        # React: package.json present but no next/angular/vue/nuxt/svelte/astro
        if (
            frontend == "unknown"
            and "package.json" in basenames
            and any(p.endswith((".jsx", ".tsx")) for p in file_listing)
        ):
            frontend = "react"

        backend = "unknown"
        for filename, fw in _BACKEND_SIGNALS:
            if filename in basenames:
                backend = fw
                break

        # Flask: app.py or wsgi.py without Django's manage.py
        if (
            backend == "unknown"
            and any(
                os.path.basename(p) in ("app.py", "wsgi.py", "run.py", "application.py")
                for p in file_listing
            )
            and "requirements.txt" in basenames
        ):
            backend = "flask"

        # FastAPI / generic Python backend: main.py with requirements.txt
        if backend == "unknown" and "main.py" in basenames and "requirements.txt" in basenames:
            backend = "fastapi"

        # Express: server.js or app.js present in a Node project
        if (
            backend == "unknown"
            and "package.json" in basenames
            and any(
                os.path.basename(p) in ("server.js", "server.ts", "app.js") for p in file_listing
            )
        ):
            backend = "express"

        detected = frontend != "unknown" or backend != "unknown"
        return {"frontend": frontend, "backend": backend, "detected": detected}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _list_files(self, repo_path: str) -> list[str]:
        """Walk the repo and return relative file paths, capped at 5000 files."""
        if not repo_path or not os.path.isdir(repo_path):
            return []

        result: list[str] = []
        skip_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
        }
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for filename in filenames:
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, repo_path)
                result.append(rel)
                if len(result) >= 5000:
                    return result
        return result

    async def _build_framework_from_hint(self, framework: str) -> dict:
        """Build a framework dict from a user-supplied hint."""
        lower = framework.lower()
        frontend_frameworks = {
            "nextjs",
            "react",
            "vue",
            "angular",
            "svelte",
            "nuxtjs",
            "astro",
        }
        backend_frameworks = {
            "django",
            "flask",
            "fastapi",
            "express",
            "rails",
            "phoenix",
            "laravel",
            "spring",
            "actix",
            "go",
        }
        if lower in frontend_frameworks:
            return {"frontend": lower, "backend": "unknown", "detected": True}
        if lower in backend_frameworks:
            return {"frontend": "unknown", "backend": lower, "detected": True}
        return {"frontend": lower, "backend": "unknown", "detected": True}

    def _infer_routes(self, file_listing: list[str]) -> list[dict]:
        """Heuristically infer page routes from file paths."""
        routes: list[dict] = []
        route_extensions = (".tsx", ".jsx", ".vue", ".html", ".py", ".rb")
        page_dirs = ("pages", "views", "routes", "app", "src/pages", "src/views")

        for filepath in file_listing:
            norm = filepath.replace("\\", "/")
            if not any(norm.endswith(ext) for ext in route_extensions):
                continue
            if not any(norm.startswith(d + "/") or f"/{d}/" in norm for d in page_dirs):
                continue

            name = os.path.splitext(os.path.basename(filepath))[0]
            if name in ("__init__", "index", "base", "layout", "_app", "_document"):
                path = "/"
            else:
                path = f"/{name.lower().replace('_', '-')}"

            routes.append(
                {
                    "path": path,
                    "component": name,
                    "file": filepath,
                    "methods": ["GET"],
                }
            )

        return routes

    def _infer_api_endpoints(self, file_listing: list[str]) -> list[dict]:
        """Heuristically infer API endpoints from file paths."""
        endpoints: list[dict] = []
        api_dirs = ("api", "routers", "routes", "controllers", "handlers")
        api_extensions = (".py", ".js", ".ts", ".rb")

        for filepath in file_listing:
            norm = filepath.replace("\\", "/")
            if not any(f"/{d}/" in norm or norm.startswith(d + "/") for d in api_dirs):
                continue
            if not any(norm.endswith(ext) for ext in api_extensions):
                continue

            name = os.path.splitext(os.path.basename(filepath))[0]
            endpoints.append(
                {
                    "path": f"/api/{name.lower()}",
                    "method": "GET",
                    "file": filepath,
                    "handler": name,
                }
            )

        return endpoints

    def _infer_forms(self, file_listing: list[str]) -> list[dict]:
        """Heuristically infer forms from file paths that contain form-related keywords."""
        forms: list[dict] = []
        form_keywords = ("login", "register", "signup", "contact", "checkout", "form", "submit")

        for filepath in file_listing:
            norm = filepath.replace("\\", "/").lower()
            basename = os.path.basename(norm)
            if any(kw in basename for kw in form_keywords):
                name = os.path.splitext(os.path.basename(filepath))[0]
                forms.append(
                    {
                        "page": f"/{name.lower()}",
                        "fields": [],
                        "action": "submit",
                        "file": filepath,
                    }
                )

        return forms

    def _infer_auth_flows(self, file_listing: list[str]) -> list[dict]:
        """Detect auth-related files and synthesise auth flow descriptors."""
        auth_flows: list[dict] = []
        for filepath in file_listing:
            norm = filepath.replace("\\", "/").lower()
            if any(hint in norm for hint in _AUTH_PATH_HINTS):
                auth_flows.append(
                    {
                        "type": "form",
                        "login_page": "/login",
                        "fields": ["email", "password"],
                    }
                )
                break  # one auth flow is enough for the model

        return auth_flows

    def _build_user_journeys(self, routes: list[dict], auth_flows: list[dict]) -> list[dict]:
        """Build high-level user journey descriptors from routes and auth flows."""
        journeys: list[dict] = []

        if auth_flows:
            journeys.append(
                {
                    "name": "User Authentication",
                    "steps": ["navigate to login", "fill credentials", "submit", "assert redirect"],
                    "priority": "critical",
                }
            )

        for route in routes[:5]:  # cap at 5 auto-generated journeys
            name = route["component"].replace("_", " ").replace("-", " ").title()
            journeys.append(
                {
                    "name": f"Visit {name}",
                    "steps": [f"navigate to {route['path']}", "assert page loaded"],
                    "priority": "medium",
                }
            )

        return journeys

    def _count_static_assets(self, file_listing: list[str]) -> dict:
        """Count static asset files."""
        js_count = sum(1 for f in file_listing if f.endswith((".js", ".jsx", ".ts", ".tsx")))
        css_count = sum(1 for f in file_listing if f.endswith((".css", ".scss", ".sass", ".less")))
        image_count = sum(
            1
            for f in file_listing
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"))
        )
        return {"js_files": js_count, "css_files": css_count, "images": image_count}

    def _assess_test_coverage(self, file_listing: list[str]) -> dict:
        """Identify existing test infrastructure."""
        test_files = [
            f
            for f in file_listing
            if os.path.basename(f).startswith("test_")
            or os.path.basename(f).endswith(
                ("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js")
            )
        ]
        framework = "unknown"
        basenames = {os.path.basename(f) for f in file_listing}
        if "pytest.ini" in basenames or "conftest.py" in basenames:
            framework = "pytest"
        elif "jest.config.js" in basenames or "jest.config.ts" in basenames:
            framework = "jest"
        elif "vitest.config.ts" in basenames or "vitest.config.js" in basenames:
            framework = "vitest"

        return {
            "existing_tests": len(test_files),
            "test_framework": framework,
            "coverage_percent": None,
        }

    def _match_affected_routes(self, changed_paths: list[str], routes: list[dict]) -> list[str]:
        """Find routes whose source file appears in the changed paths."""
        affected: list[str] = []
        for route in routes:
            route_file = route.get("file", "")
            if any(route_file in cp or cp in route_file for cp in changed_paths):
                affected.append(route["path"])
        return affected

    def _match_affected_endpoints(self, changed_paths: list[str]) -> list[str]:
        """Infer API endpoint paths from changed file names."""
        endpoints: list[str] = []
        for path in changed_paths:
            norm = path.replace("\\", "/")
            if "/api/" in norm or "/routes/" in norm or "/controllers/" in norm:
                name = os.path.splitext(os.path.basename(path))[0]
                endpoints.append(f"/api/{name}")
        return endpoints

    def _match_affected_journeys(
        self,
        changed_paths: list[str],
        affected_routes: list[str],
        journeys: list[dict],
    ) -> list[str]:
        """Return journey names that overlap with affected routes."""
        affected: list[str] = []
        for journey in journeys:
            steps_text = " ".join(str(s) for s in journey.get("steps", []))
            for route in affected_routes:
                if route in steps_text:
                    affected.append(journey["name"])
                    break
            # Also match on auth keywords in changed paths
            for cp in changed_paths:
                norm = cp.lower()
                if (
                    any(hint in norm for hint in _AUTH_PATH_HINTS)
                    and ("auth" in journey["name"].lower() or "login" in journey["name"].lower())
                    and journey["name"] not in affected
                ):
                    affected.append(journey["name"])
        return affected

    def _compute_risk_level(
        self,
        changed_files: list[dict],
        total_lines: int,
        affected_routes: list[str],
        affected_journeys: list[str],
    ) -> str:
        """Compute a simple risk level based on change size and affected scope."""
        high_risk_keywords = ("auth", "login", "payment", "security", "token", "secret")
        has_high_risk_file = any(
            any(kw in f.get("path", "").lower() for kw in high_risk_keywords) for f in changed_files
        )

        if has_high_risk_file or len(affected_journeys) >= 3 or total_lines >= 200:
            return "high"
        if len(affected_routes) >= 2 or total_lines >= 50:
            return "medium"
        return "low"

    def _suggest_tests(
        self,
        affected_routes: list[str],
        affected_journeys: list[str],
        risk_level: str,
    ) -> list[str]:
        """Build a list of test suggestion strings."""
        suggestions: list[str] = []
        for route in affected_routes:
            suggestions.append(f"smoke test for {route}")
        for journey in affected_journeys:
            suggestions.append(f"regression test for '{journey}'")
        if risk_level == "high":
            suggestions.append("full regression suite")
        return suggestions

    # Stub methods for direct route/api/form discovery tasks

    async def _discover_routes(self, repo_path: str) -> list[dict]:
        return self._infer_routes(self._list_files(repo_path))

    async def _discover_apis(self, repo_path: str) -> list[dict]:
        return self._infer_api_endpoints(self._list_files(repo_path))

    async def _discover_forms(self, repo_path: str) -> list[dict]:
        return self._infer_forms(self._list_files(repo_path))
