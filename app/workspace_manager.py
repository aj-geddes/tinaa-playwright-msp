#!/usr/bin/env python3
"""
TINAA Workspace Manager

Handles project creation, repository cloning, and workspace management
for multiple Playwright testing projects.
"""

import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiofiles

from app.git_auth import git_authenticator

logger = logging.getLogger("tinaa.workspace_manager")


class WorkspaceManager:
    """Manages TINAA workspace with multiple projects"""

    def __init__(self, workspace_path: str | None = None):
        if workspace_path is None:
            import tempfile

            workspace_path = os.path.join(tempfile.gettempdir(), "tinaa_workspace")
        self.workspace_path = Path(workspace_path)
        self.projects_path = self.workspace_path / "projects"
        self.templates_path = self.workspace_path / "templates"
        self.shared_path = self.workspace_path / "shared"

        # Ensure workspace structure exists
        self._initialize_workspace()

    def _initialize_workspace(self):
        """Initialize the workspace directory structure"""
        directories = [
            self.projects_path,
            self.templates_path,
            self.shared_path,
            self.shared_path / "utilities",
            self.shared_path / "fixtures",
            self.shared_path / "resources",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")

    async def create_project(
        self,
        name: str,
        description: str = "",
        template: str = "basic-web-testing",
        repository_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new project in the workspace

        Args:
            name: Project name
            description: Project description
            template: Template to use for project structure
            repository_url: Optional repository to clone

        Returns:
            Project information dictionary
        """
        project_id = str(uuid.uuid4())
        project_path = self.projects_path / project_id

        try:
            # Create project directory
            project_path.mkdir(parents=True, exist_ok=True)

            # If repository URL provided, clone it
            if repository_url:
                await self._clone_repository(repository_url, project_path)
            else:
                # Use template to create project structure
                await self._create_from_template(template, project_path)

            # Create TINAA-specific configuration
            tinaa_config = {
                "id": project_id,
                "name": name,
                "description": description,
                "template": template,
                "repository_url": repository_url,
                "created_at": datetime.now().isoformat(),
                "workspace_path": str(project_path),
                "ai_context": {
                    "project_type": "web-testing",
                    "test_patterns": [],
                    "insights": [],
                },
            }

            await self._save_project_config(project_path, tinaa_config)

            # Initialize project structure
            await self._initialize_project_structure(project_path, tinaa_config)

            logger.info(f"Created project {name} with ID {project_id}")

            return {
                "success": True,
                "project_id": project_id,
                "name": name,
                "path": str(project_path),
                "config": tinaa_config,
            }

        except Exception as e:
            logger.error(f"Failed to create project {name}: {e!s}")
            # Cleanup on failure
            if project_path.exists():
                shutil.rmtree(project_path, ignore_errors=True)

            return {"success": False, "error": str(e)}

    async def create_project_from_url(
        self, url: str, name: str | None = None
    ) -> dict[str, Any]:
        """
        Create a project by analyzing a URL and generating appropriate test structure

        Args:
            url: URL to analyze and create tests for
            name: Optional project name (will be generated from URL if not provided)

        Returns:
            Project information dictionary
        """
        try:
            # Parse URL to generate project name
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")

            if not name:
                name = f"tests-{domain.replace('.', '-')}"

            # Create project with URL-specific template
            project_result = await self.create_project(
                name=name,
                description=f"Auto-generated tests for {url}",
                template="url-based-testing",
            )

            if not project_result["success"]:
                return project_result

            project_path = Path(project_result["path"])

            # Analyze URL and generate initial test structure
            url_analysis = await self._analyze_url(url)

            # Generate initial test files based on URL analysis
            await self._generate_url_tests(project_path, url, url_analysis)

            # Update project config with URL analysis
            config_path = project_path / ".tinaa" / "config.json"
            async with aiofiles.open(config_path) as f:
                config = json.loads(await f.read())

            config["target_url"] = url
            config["url_analysis"] = url_analysis
            config["ai_context"]["project_type"] = "url-testing"

            async with aiofiles.open(config_path, "w") as f:
                await f.write(json.dumps(config, indent=2))

            logger.info(f"Created URL-based project for {url}")

            return {**project_result, "target_url": url, "url_analysis": url_analysis}

        except Exception as e:
            logger.error(f"Failed to create project from URL {url}: {e!s}")
            return {"success": False, "error": str(e)}

    async def _clone_repository(self, repository_url: str, project_path: Path):
        """Clone a git repository to the project path using authenticated git"""
        try:
            # Use git authenticator for secure cloning
            clone_result = await git_authenticator.clone_repository(
                repository_url=repository_url,
                destination_path=str(project_path),
                auth_type="auto",  # Auto-detect available authentication
            )

            if not clone_result.get("success"):
                raise Exception(
                    f"Git clone failed: {clone_result.get('error', 'Unknown error')}"
                )

            logger.info(
                f"Successfully cloned repository {repository_url} using {clone_result.get('auth_method', 'unknown')} authentication"
            )

            # Return clone information for potential use in project config
            return clone_result

        except Exception as e:
            logger.error(f"Failed to clone repository {repository_url}: {e!s}")
            raise

    async def _create_from_template(self, template: str, project_path: Path):
        """Create project structure from template"""
        template_configs = {
            "basic-web-testing": {
                "directories": [
                    "src",
                    "tests",
                    "tests/pages",
                    "tests/fixtures",
                    "tests/utils",
                    "reports",
                    "screenshots",
                ],
                "files": {
                    "package.json": self._get_package_json_template(),
                    "playwright.config.ts": self._get_playwright_config_template(),
                    "tests/example.spec.ts": self._get_example_test_template(),
                    "tests/pages/base.page.ts": self._get_base_page_template(),
                    ".gitignore": self._get_gitignore_template(),
                    "README.md": self._get_readme_template(),
                },
            },
            "url-based-testing": {
                "directories": [
                    "src",
                    "tests",
                    "tests/pages",
                    "tests/scenarios",
                    "tests/utils",
                    "reports",
                    "screenshots",
                ],
                "files": {
                    "package.json": self._get_package_json_template(),
                    "playwright.config.ts": self._get_playwright_config_template(),
                    "tests/utils/url-analyzer.ts": self._get_url_analyzer_template(),
                    "tests/pages/analyzed.page.ts": self._get_analyzed_page_template(),
                    ".gitignore": self._get_gitignore_template(),
                    "README.md": self._get_url_readme_template(),
                },
            },
            "e2e-workflow": {
                "directories": [
                    "src",
                    "tests/e2e",
                    "tests/integration",
                    "tests/unit",
                    "tests/pages",
                    "tests/fixtures",
                    "tests/utils",
                    "workflows",
                    "reports",
                ],
                "files": {
                    "package.json": self._get_package_json_template(),
                    "playwright.config.ts": self._get_playwright_config_template(),
                    "tests/e2e/user-journey.spec.ts": self._get_user_journey_template(),
                    ".gitignore": self._get_gitignore_template(),
                    "README.md": self._get_e2e_readme_template(),
                },
            },
        }

        config = template_configs.get(template, template_configs["basic-web-testing"])

        # Create directories
        for directory in config["directories"]:
            (project_path / directory).mkdir(parents=True, exist_ok=True)

        # Create files
        for file_path, content in config["files"].items():
            file_full_path = project_path / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_full_path, "w") as f:
                await f.write(content)

    async def _initialize_project_structure(
        self, project_path: Path, config: dict[str, Any]
    ):
        """Initialize TINAA-specific project structure"""
        tinaa_dir = project_path / ".tinaa"
        tinaa_dir.mkdir(exist_ok=True)

        # Create subdirectories
        subdirs = ["playbooks", "reports", "ai-context", "templates"]
        for subdir in subdirs:
            (tinaa_dir / subdir).mkdir(exist_ok=True)

        # Create initial playbook
        initial_playbook = {
            "id": str(uuid.uuid4()),
            "name": "Initial Project Setup",
            "description": "Basic project validation and setup verification",
            "steps": [
                {
                    "id": "setup-1",
                    "action": "navigate",
                    "parameters": {"url": "https://example.com"},
                    "description": "Navigate to target URL",
                },
                {
                    "id": "setup-2",
                    "action": "screenshot",
                    "parameters": {"full_page": True},
                    "description": "Take initial screenshot",
                },
            ],
            "created_at": datetime.now().isoformat(),
            "status": "draft",
        }

        playbook_path = tinaa_dir / "playbooks" / "initial-setup.json"
        async with aiofiles.open(playbook_path, "w") as f:
            await f.write(json.dumps(initial_playbook, indent=2))

    async def _save_project_config(self, project_path: Path, config: dict[str, Any]):
        """Save project configuration to .tinaa/config.json"""
        tinaa_dir = project_path / ".tinaa"
        tinaa_dir.mkdir(exist_ok=True)

        config_path = tinaa_dir / "config.json"
        async with aiofiles.open(config_path, "w") as f:
            await f.write(json.dumps(config, indent=2))

    async def _analyze_url(self, url: str) -> dict[str, Any]:
        """Analyze a URL to determine testing approach"""
        # This would integrate with AI in the future for intelligent analysis
        # For now, provide basic analysis

        parsed_url = urlparse(url)

        analysis = {
            "domain": parsed_url.netloc,
            "protocol": parsed_url.scheme,
            "path": parsed_url.path,
            "suggested_tests": [
                "page_load_test",
                "navigation_test",
                "form_interaction_test",
                "responsive_design_test",
            ],
            "estimated_complexity": "medium",
            "recommended_patterns": ["page_object_model", "data_driven_testing"],
            "potential_elements": [
                "navigation_menu",
                "forms",
                "buttons",
                "links",
                "images",
            ],
        }

        return analysis

    async def _generate_url_tests(
        self, project_path: Path, url: str, analysis: dict[str, Any]
    ):
        """Generate initial test files based on URL analysis"""

        # Generate main test file
        main_test_content = f"""
import {{ test, expect }} from '@playwright/test';

test.describe('{analysis["domain"]} - Automated Tests', () => {{
  const BASE_URL = '{url}';

  test('Page loads successfully', async ({{ page }}) => {{
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/.+/);
    
    // Take screenshot for visual verification
    await page.screenshot({{ 
      path: 'screenshots/page-load.png',
      fullPage: true 
    }});
  }});

  test('Navigation elements are present', async ({{ page }}) => {{
    await page.goto(BASE_URL);
    
    // Check for common navigation elements
    const nav = page.locator('nav, .nav, .navigation, header');
    if (await nav.count() > 0) {{
      await expect(nav.first()).toBeVisible();
    }}
  }});

  test('Responsive design check', async ({{ page, context }}) => {{
    // Test mobile viewport
    await page.setViewportSize({{ width: 375, height: 667 }});
    await page.goto(BASE_URL);
    await page.screenshot({{ path: 'screenshots/mobile-view.png' }});
    
    // Test desktop viewport
    await page.setViewportSize({{ width: 1920, height: 1080 }});
    await page.goto(BASE_URL);
    await page.screenshot({{ path: 'screenshots/desktop-view.png' }});
  }});
}});
"""

        test_file_path = (
            project_path / "tests" / f"{analysis['domain'].replace('.', '-')}.spec.ts"
        )
        async with aiofiles.open(test_file_path, "w") as f:
            await f.write(main_test_content)

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all projects in the workspace"""
        projects = []

        if not self.projects_path.exists():
            return projects

        for project_dir in self.projects_path.iterdir():
            if project_dir.is_dir():
                config_path = project_dir / ".tinaa" / "config.json"
                if config_path.exists():
                    try:
                        async with aiofiles.open(config_path) as f:
                            config = json.loads(await f.read())
                            projects.append(config)
                    except Exception as e:
                        logger.warning(f"Failed to read config for {project_dir}: {e}")

        return projects

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project information by ID"""
        project_path = self.projects_path / project_id
        config_path = project_path / ".tinaa" / "config.json"

        if not config_path.exists():
            return None

        try:
            async with aiofiles.open(config_path) as f:
                return json.loads(await f.read())
        except Exception as e:
            logger.error(f"Failed to read project {project_id}: {e}")
            return None

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project from the workspace"""
        project_path = self.projects_path / project_id

        if not project_path.exists():
            return False

        try:
            shutil.rmtree(project_path)
            logger.info(f"Deleted project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False

    # Template methods for file generation
    def _get_package_json_template(self) -> str:
        return """{{
  "name": "tinaa-playwright-project",
  "version": "1.0.0",
  "description": "TINAA generated Playwright testing project",
  "main": "index.js",
  "scripts": {{
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "test:ui": "playwright test --ui",
    "report": "playwright show-report"
  }},
  "devDependencies": {{
    "@playwright/test": "^1.46.0",
    "@types/node": "^20.0.0"
  }},
  "author": "TINAA",
  "license": "MIT"
}}"""

    def _get_playwright_config_template(self) -> str:
        return """import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', {{ outputFile: 'reports/test-results.json' }}]
  ],
  use: {{
    baseURL: process.env.BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  }},
  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
    {{
      name: 'firefox',
      use: {{ ...devices['Desktop Firefox'] }},
    }},
    {{
      name: 'webkit',
      use: {{ ...devices['Desktop Safari'] }},
    }},
    {{
      name: 'Mobile Chrome',
      use: {{ ...devices['Pixel 5'] }},
    }},
  ],
}});"""

    def _get_example_test_template(self) -> str:
        return """import {{ test, expect }} from '@playwright/test';

test('basic example test', async ({{ page }}) => {{
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
  
  // Take a screenshot
  await page.screenshot({{ path: 'screenshots/example.png' }});
}});"""

    def _get_base_page_template(self) -> str:
        return """import {{ Page }} from '@playwright/test';

export class BasePage {{
  constructor(public readonly page: Page) {{}}

  async goto(path: string = '') {{
    await this.page.goto(path);
  }}

  async takeScreenshot(name: string) {{
    await this.page.screenshot({{ 
      path: `screenshots/${{name}}.png`,
      fullPage: true 
    }});
  }}
}}"""

    def _get_gitignore_template(self) -> str:
        return """# Dependencies
node_modules/

# Test results
test-results/
playwright-report/
playwright/.cache/

# Screenshots and videos
screenshots/
videos/
reports/

# Environment variables
.env
.env.local

# IDE
.vscode/
.idea/

# OS generated files
.DS_Store
Thumbs.db"""

    def _get_readme_template(self) -> str:
        return """# TINAA Playwright Project

This project was generated by TINAA (Testing Intelligence Network Automation Assistant).

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Install Playwright browsers:
   ```bash
   npx playwright install
   ```

3. Run tests:
   ```bash
   npm test
   ```

## Project Structure

- `tests/` - Test files
- `tests/pages/` - Page Object Model classes
- `tests/fixtures/` - Test fixtures and data
- `tests/utils/` - Utility functions
- `reports/` - Test reports
- `screenshots/` - Screenshots from tests

## TINAA Integration

This project includes TINAA-specific configuration in the `.tinaa/` directory:

- `config.json` - Project configuration
- `playbooks/` - Test playbooks and scenarios
- `reports/` - TINAA-generated reports
- `ai-context/` - AI analysis and insights

## Commands

- `npm test` - Run all tests
- `npm run test:headed` - Run tests in headed mode
- `npm run test:debug` - Run tests in debug mode
- `npm run test:ui` - Open Playwright UI
- `npm run report` - Show test report"""

    def _get_url_analyzer_template(self) -> str:
        return """import {{ Page }} from '@playwright/test';

export class UrlAnalyzer {{
  constructor(private page: Page) {{}}

  async analyzePageStructure() {{
    return {{
      title: await this.page.title(),
      url: this.page.url(),
      forms: await this.countElements('form'),
      links: await this.countElements('a'),
      buttons: await this.countElements('button'),
      inputs: await this.countElements('input'),
      images: await this.countElements('img'),
      headings: await this.countElements('h1, h2, h3, h4, h5, h6')
    }};
  }}

  private async countElements(selector: string): Promise<number> {{
    return await this.page.locator(selector).count();
  }}
}}"""

    def _get_analyzed_page_template(self) -> str:
        return """import {{ Page }} from '@playwright/test';
import {{ BasePage }} from './base.page';

export class AnalyzedPage extends BasePage {{
  constructor(page: Page, private url: string) {{
    super(page);
  }}

  async goto() {{
    await this.page.goto(this.url);
  }}

  async analyzeAndTest() {{
    // Navigate to the URL
    await this.goto();
    
    // Basic checks
    await this.page.waitForLoadState('networkidle');
    
    // Take initial screenshot
    await this.takeScreenshot('initial-load');
    
    return {{
      loaded: true,
      title: await this.page.title(),
      url: this.page.url()
    }};
  }}
}}"""

    def _get_url_readme_template(self) -> str:
        return """# URL-Based Testing Project

This project was automatically generated by TINAA to test a specific URL.

## Target URL Analysis

The project includes:
- Automated page structure analysis
- Responsive design testing
- Basic functionality verification
- Screenshot capture for visual validation

## Generated Tests

- Page load verification
- Element presence checks
- Responsive design validation
- Basic interaction testing

## Next Steps

1. Review the generated tests in `tests/`
2. Customize tests based on your specific requirements
3. Add more detailed test scenarios using TINAA's playbook builder
4. Use TINAA's AI assistant for test optimization"""

    def _get_user_journey_template(self) -> str:
        return """import {{ test, expect }} from '@playwright/test';

test.describe('User Journey Tests', () => {{
  test('complete user workflow', async ({{ page }}) => {{
    // This is a template for end-to-end user journey testing
    // Customize based on your application's user flows
    
    await page.goto('/');
    await expect(page).toHaveTitle(/.+/);
    
    // Add your user journey steps here
    // Example:
    // 1. Login
    // 2. Navigate to feature
    // 3. Perform actions
    // 4. Verify results
    // 5. Logout
  }});
}});"""

    def _get_e2e_readme_template(self) -> str:
        return """# E2E Workflow Testing Project

This project is set up for comprehensive end-to-end workflow testing.

## Structure

- `tests/e2e/` - End-to-end test scenarios
- `tests/integration/` - Integration tests
- `tests/unit/` - Unit tests
- `workflows/` - Defined user workflows and journeys

## Workflow Testing

This project includes templates for:
- User journey testing
- Cross-browser compatibility
- Integration testing
- Performance testing"""
