#!/usr/bin/env python3
"""
TINAA Workspace Management MCP Tools

Comprehensive MCP tools for workspace and project management with proper FastMCP 2.8.0 documentation.
"""

import logging
from typing import Any

from fastmcp import Context, FastMCP

from app.git_auth import git_authenticator
from app.workspace_manager import WorkspaceManager

logger = logging.getLogger("tinaa.workspace_mcp_tools")

# Initialize workspace MCP server
workspace_mcp = FastMCP("TINAA Workspace Management")

# Global workspace manager (lazy initialization)
workspace_manager = None

def get_workspace_manager():
    """Get or create workspace manager instance"""
    global workspace_manager
    if workspace_manager is None:
        workspace_manager = WorkspaceManager()
    return workspace_manager


@workspace_mcp.tool()
async def create_project(
    project_name: str,
    description: str = "",
    template: str = "basic-web-testing",
    repository_url: str | None = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Create a new Playwright testing project in TINAA's workspace with intelligent setup.

    Creates a new project directory with proper structure, configuration files, and optional
    repository cloning. Supports multiple project templates and automatic setup.

    Args:
        project_name: Name for the new project (e.g., "My E-commerce Tests")
        description: Optional description of what this project tests (e.g., "Testing user registration and checkout flows")
        template: Project template to use - "basic-web-testing" (standard Playwright setup), "url-based-testing" (URL analysis), or "e2e-workflow" (comprehensive E2E)
        repository_url: Optional Git repository URL to clone as project base (supports GitHub, GitLab with authentication)
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if project creation succeeded
        - project_id: Unique identifier for the created project
        - name: Project name
        - path: Absolute file system path to the project directory
        - config: Project configuration including TINAA-specific settings
        - template_used: The template that was applied
        - repository_info: Git repository information if cloned
        - error: Error message if creation failed

    The created project includes:
        - package.json with Playwright dependencies
        - playwright.config.ts with optimized settings
        - Test directory structure (tests/, tests/pages/, tests/utils/)
        - Example test files and Page Object Model templates
        - .tinaa/ directory with TINAA-specific configuration
        - Initial playbook for project validation

    Example:
        >>> project = await create_project(
        ...     project_name="My Store Tests",
        ...     description="E-commerce testing suite",
        ...     template="e2e-workflow",
        ...     repository_url="https://github.com/myorg/test-templates"
        ... )
        >>> print(project["project_id"])
        "abc123-def456-ghi789"
    """
    if ctx:
        await ctx.info(f"Creating project: {project_name}")

    try:
        result = await get_workspace_manager().create_project(
            name=project_name,
            description=description,
            template=template,
            repository_url=repository_url,
        )

        if ctx and result.get("success"):
            await ctx.success(f"Project '{project_name}' created successfully")
        elif ctx:
            await ctx.error(
                f"Failed to create project: {result.get('error', 'Unknown error')}"
            )

        return result

    except Exception as e:
        logger.error(f"Error creating project: {e!s}")
        if ctx:
            await ctx.error(f"Error creating project: {e!s}")
        return {"success": False, "error": str(e)}


@workspace_mcp.tool()
async def create_project_from_url(
    url: str, project_name: str | None = None, ctx: Context = None
) -> dict[str, Any]:
    """
    Automatically create a Playwright testing project by analyzing a target URL.

    TINAA analyzes the provided URL to understand the application structure, then generates
    an appropriate project with initial tests tailored to the discovered elements and functionality.

    Args:
        url: Target URL to analyze and create tests for (e.g., "https://myapp.com", "https://shop.example.com")
        project_name: Optional custom name for the project (auto-generated from URL if not provided)
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if project creation succeeded
        - project_id: Unique identifier for the created project
        - name: Project name (generated or provided)
        - path: Absolute file system path to the project directory
        - target_url: The URL that was analyzed
        - url_analysis: Analysis results including detected elements and suggested tests
        - generated_tests: List of automatically generated test files
        - recommendations: AI-powered recommendations for additional testing
        - error: Error message if creation failed

    URL Analysis includes:
        - Page structure and navigation elements
        - Forms and interactive elements
        - Performance characteristics
        - Accessibility considerations
        - Recommended test scenarios

    Example:
        >>> project = await create_project_from_url(
        ...     url="https://shop.example.com",
        ...     project_name="Shop E2E Tests"
        ... )
        >>> print(project["url_analysis"]["suggested_tests"])
        ["page_load_test", "navigation_test", "form_interaction_test", "responsive_design_test"]
    """
    if ctx:
        await ctx.info(f"Analyzing URL and creating project: {url}")

    try:
        result = await get_workspace_manager().create_project_from_url(
            url=url, name=project_name
        )

        if ctx and result.get("success"):
            await ctx.success(f"Project created from URL analysis: {url}")
        elif ctx:
            await ctx.error(
                f"Failed to create project from URL: {result.get('error', 'Unknown error')}"
            )

        return result

    except Exception as e:
        logger.error(f"Error creating project from URL: {e!s}")
        if ctx:
            await ctx.error(f"Error creating project from URL: {e!s}")
        return {"success": False, "error": str(e)}


@workspace_mcp.tool()
async def list_projects(ctx: Context = None) -> list[dict[str, Any]]:
    """
    Retrieve a list of all projects in TINAA's workspace with their status and metadata.

    Returns comprehensive information about all projects including configuration,
    last activity, test results, and current status.

    Args:
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        List of project dictionaries, each containing:
        - id: Unique project identifier
        - name: Project name
        - description: Project description
        - created_at: ISO timestamp of creation
        - workspace_path: File system path to project
        - template: Template used for project creation
        - repository_url: Git repository URL if applicable
        - ai_context: AI analysis and insights for the project
        - last_activity: Timestamp of last test execution or modification
        - test_count: Number of test files in the project
        - status: Current status ("active", "archived", "error")

    Use this to:
        - Get an overview of all testing projects
        - Find projects by name or characteristics
        - Monitor project activity and health
        - Identify projects that need attention

    Example:
        >>> projects = await list_projects()
        >>> for project in projects:
        ...     print(f"{project['name']}: {project['test_count']} tests")
        "My Store Tests: 15 tests"
        "API Integration Tests: 8 tests"
        "Mobile App Tests: 22 tests"
    """
    if ctx:
        await ctx.info("Retrieving all projects from workspace")

    try:
        projects = await get_workspace_manager().list_projects()

        if ctx:
            await ctx.info(f"Found {len(projects)} projects in workspace")

        return projects

    except Exception as e:
        logger.error(f"Error listing projects: {e!s}")
        if ctx:
            await ctx.error(f"Error listing projects: {e!s}")
        return []


@workspace_mcp.tool()
async def get_project(project_id: str, ctx: Context = None) -> dict[str, Any] | None:
    """
    Retrieve detailed information about a specific project including configuration and status.

    Gets comprehensive project information including files, configuration, test results,
    and AI-generated insights for a specific project.

    Args:
        project_id: Unique identifier of the project to retrieve
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Project dictionary containing:
        - id: Unique project identifier
        - name: Project name and description
        - workspace_path: File system path to project directory
        - configuration: TINAA and Playwright configuration settings
        - file_structure: Overview of project files and directories
        - test_files: List of test files with metadata
        - recent_results: Recent test execution results
        - ai_insights: AI-generated project analysis and recommendations
        - repository_info: Git repository information if applicable
        - None if project not found

    Use this to:
        - Get detailed project information for debugging
        - Review project structure and configuration
        - Access AI insights and recommendations
        - Check test execution history

    Example:
        >>> project = await get_project("abc123-def456-ghi789")
        >>> print(f"Project: {project['name']}")
        "Project: My Store Tests"
        >>> print(f"Test files: {len(project['test_files'])}")
        "Test files: 15"
    """
    if ctx:
        await ctx.info(f"Retrieving project: {project_id}")

    try:
        project = await get_workspace_manager().get_project(project_id)

        if project and ctx:
            await ctx.success(f"Retrieved project: {project.get('name', 'Unknown')}")
        elif ctx:
            await ctx.error(f"Project not found: {project_id}")

        return project

    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e!s}")
        if ctx:
            await ctx.error(f"Error getting project: {e!s}")
        return None


@workspace_mcp.tool()
async def delete_project(project_id: str, ctx: Context = None) -> dict[str, Any]:
    """
    Permanently delete a project and all its files from TINAA's workspace.

    Removes the project directory, all test files, configuration, and metadata.
    This action cannot be undone, so use with caution.

    Args:
        project_id: Unique identifier of the project to delete
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if deletion succeeded
        - project_id: The ID of the deleted project
        - message: Confirmation or error message
        - error: Error details if deletion failed

    Warning:
        This permanently removes all project files, tests, and configuration.
        Make sure to backup any important data before deletion.

    Example:
        >>> result = await delete_project("abc123-def456-ghi789")
        >>> print(result["message"])
        "Project deleted successfully"
    """
    if ctx:
        await ctx.info(f"Deleting project: {project_id}")

    try:
        success = await get_workspace_manager().delete_project(project_id)

        if success:
            result = {
                "success": True,
                "project_id": project_id,
                "message": "Project deleted successfully",
            }
            if ctx:
                await ctx.success(f"Project {project_id} deleted successfully")
        else:
            result = {
                "success": False,
                "project_id": project_id,
                "error": "Project not found or could not be deleted",
            }
            if ctx:
                await ctx.error(f"Failed to delete project {project_id}")

        return result

    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e!s}")
        if ctx:
            await ctx.error(f"Error deleting project: {e!s}")
        return {"success": False, "project_id": project_id, "error": str(e)}


@workspace_mcp.tool()
async def get_workspace_status(ctx: Context = None) -> dict[str, Any]:
    """
    Get comprehensive status and statistics about TINAA's workspace and all projects.

    Provides workspace-wide metrics including storage usage, project counts, recent activity,
    and system health information.

    Args:
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - workspace_path: Absolute path to workspace directory
        - total_projects: Total number of projects
        - active_projects: Number of active (non-archived) projects
        - storage_usage: Disk space usage statistics
        - recent_activity: List of recent project activities
        - available_templates: List of available project templates
        - system_health: Overall system status and warnings
        - git_status: Git authentication status
        - ai_status: AI provider connectivity status

    Use this to:
        - Monitor workspace health and usage
        - Check system capacity and performance
        - Identify recent activity across all projects
        - Verify AI and Git integration status

    Example:
        >>> status = await get_workspace_status()
        >>> print(f"Total projects: {status['total_projects']}")
        "Total projects: 25"
        >>> print(f"Storage used: {status['storage_usage']['used_gb']}GB")
        "Storage used: 15.2GB"
    """
    if ctx:
        await ctx.info("Retrieving workspace status and statistics")

    try:
        # Get basic project statistics
        projects = await get_workspace_manager().list_projects()
        total_projects = len(projects)
        active_projects = len([p for p in projects if p.get("status") != "archived"])

        # Get workspace information
        workspace_info = {
            "workspace_path": str(get_workspace_manager().workspace_path),
            "total_projects": total_projects,
            "active_projects": active_projects,
            "available_templates": [
                "basic-web-testing",
                "url-based-testing",
                "e2e-workflow",
            ],
            "recent_projects": sorted(
                projects, key=lambda x: x.get("created_at", ""), reverse=True
            )[:5],
            "system_health": "healthy",  # This could be enhanced with actual health checks
            "timestamp": "2024-01-01T00:00:00Z",  # Current timestamp
        }

        # Add Git status
        try:
            git_status = await git_authenticator.validate_git_credentials()
            workspace_info["git_status"] = git_status
        except Exception as e:
            workspace_info["git_status"] = {"valid": False, "error": str(e)}

        if ctx:
            await ctx.success(
                f"Workspace status retrieved: {total_projects} projects, {active_projects} active"
            )

        return workspace_info

    except Exception as e:
        logger.error(f"Error getting workspace status: {e!s}")
        if ctx:
            await ctx.error(f"Error getting workspace status: {e!s}")
        return {
            "error": str(e),
            "workspace_path": str(get_workspace_manager().workspace_path),
            "total_projects": 0,
            "active_projects": 0,
        }


@workspace_mcp.tool()
async def clone_repository(
    repository_url: str,
    destination_name: str | None = None,
    branch: str | None = None,
    auth_type: str = "auto",
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Clone a Git repository into TINAA's workspace with secure authentication.

    Clones a repository using available authentication methods (PAT or GitHub App),
    creating a new project structure with the cloned code as the base.

    Args:
        repository_url: Git repository URL to clone (e.g., "https://github.com/owner/repo")
        destination_name: Optional name for the project (auto-generated from repo name if not provided)
        branch: Optional specific branch to clone (defaults to repository's default branch)
        auth_type: Authentication method - "auto" (detect available), "pat" (Personal Access Token), or "github_app" (GitHub App)
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if clone succeeded
        - repository_url: The original repository URL
        - destination_path: Local path where repository was cloned
        - branch: Branch that was cloned
        - commit_hash: Latest commit hash
        - commit_message: Latest commit message
        - author: Latest commit author
        - auth_method: Authentication method used
        - cloned_at: Timestamp of clone operation
        - error: Error message if clone failed

    Supports:
        - GitHub and GitLab repositories
        - Private repositories with proper authentication
        - Shallow clones for efficiency
        - Branch-specific cloning

    Example:
        >>> result = await clone_repository(
        ...     repository_url="https://github.com/microsoft/playwright",
        ...     destination_name="playwright-examples",
        ...     branch="main"
        ... )
        >>> print(f"Cloned to: {result['destination_path']}")
        "Cloned to: /workspace/projects/playwright-examples"
    """
    if ctx:
        await ctx.info(f"Cloning repository: {repository_url}")

    try:
        # Generate destination path if not provided
        if not destination_name:
            repo_name = repository_url.split("/")[-1].replace(".git", "")
            destination_name = f"cloned-{repo_name}"

        destination_path = get_workspace_manager().projects_path / destination_name

        # Clone the repository
        result = await git_authenticator.clone_repository(
            repository_url=repository_url,
            destination_path=str(destination_path),
            auth_type=auth_type,
            branch=branch,
        )

        if result.get("success") and ctx:
            await ctx.success(f"Repository cloned successfully to {destination_name}")
        elif ctx:
            await ctx.error(
                f"Failed to clone repository: {result.get('error', 'Unknown error')}"
            )

        return result

    except Exception as e:
        logger.error(f"Error cloning repository: {e!s}")
        if ctx:
            await ctx.error(f"Error cloning repository: {e!s}")
        return {"success": False, "repository_url": repository_url, "error": str(e)}


@workspace_mcp.tool()
async def get_repository_info(
    repository_url: str, auth_type: str = "auto", ctx: Context = None
) -> dict[str, Any]:
    """
    Fetch detailed information about a Git repository without cloning it.

    Uses Git provider APIs to gather repository metadata, statistics, and information
    useful for deciding whether to clone or integrate with a repository.

    Args:
        repository_url: Git repository URL to analyze (e.g., "https://github.com/owner/repo")
        auth_type: Authentication method - "auto" (detect available), "pat" (Personal Access Token), or "github_app" (GitHub App)
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if info retrieval succeeded
        - name: Repository name
        - full_name: Full repository name (owner/repo)
        - description: Repository description
        - language: Primary programming language
        - default_branch: Default branch name
        - private: Whether the repository is private
        - stars: Number of stars/stargazers
        - forks: Number of forks
        - last_updated: Last update timestamp
        - clone_url: HTTPS clone URL
        - ssh_url: SSH clone URL
        - topics: Repository topics/tags
        - license: License information
        - error: Error message if retrieval failed

    Use this to:
        - Preview repository information before cloning
        - Validate repository access with current credentials
        - Get metadata for project documentation
        - Check repository activity and popularity

    Example:
        >>> info = await get_repository_info("https://github.com/microsoft/playwright")
        >>> print(f"Language: {info['language']}, Stars: {info['stars']}")
        "Language: TypeScript, Stars: 50000"
    """
    if ctx:
        await ctx.info(f"Fetching repository information: {repository_url}")

    try:
        result = await git_authenticator.fetch_repository_info(
            repository_url=repository_url, auth_type=auth_type
        )

        if result.get("success") and ctx:
            await ctx.success(
                f"Repository information retrieved: {result.get('name', 'Unknown')}"
            )
        elif ctx:
            await ctx.error(
                f"Failed to get repository info: {result.get('error', 'Unknown error')}"
            )

        return result

    except Exception as e:
        logger.error(f"Error getting repository info: {e!s}")
        if ctx:
            await ctx.error(f"Error getting repository info: {e!s}")
        return {"success": False, "repository_url": repository_url, "error": str(e)}
