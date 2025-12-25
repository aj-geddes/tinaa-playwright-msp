#!/usr/bin/env python3
"""
Workspace Manager for TINAA - Manages test projects and workspaces
"""
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger("tinaa-workspace")


class WorkspaceManager:
    """
    Manages test projects and workspace organization.

    Provides functionality to create, list, retrieve, and delete test projects
    within a workspace directory structure.
    """

    def __init__(self, workspace_path: str):
        """
        Initialize workspace manager.

        Args:
            workspace_path: Path to the workspace root directory
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)

        # Create workspace structure
        (self.workspace_path / "projects").mkdir(exist_ok=True)
        (self.workspace_path / "templates").mkdir(exist_ok=True)
        (self.workspace_path / "reports").mkdir(exist_ok=True)

        logger.info(f"Workspace initialized at: {self.workspace_path}")

    def _get_projects_dir(self) -> Path:
        """Get the projects directory path."""
        return self.workspace_path / "projects"

    def _get_project_path(self, project_id: str) -> Path:
        """Get the path for a specific project."""
        return self._get_projects_dir() / project_id

    def _get_project_metadata_path(self, project_id: str) -> Path:
        """Get the path to a project's metadata file."""
        return self._get_project_path(project_id) / "project.json"

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        project_type: str = "playwright",
    ) -> dict[str, Any]:
        """
        Create a new test project.

        Args:
            name: Project name
            description: Optional project description
            project_type: Type of project (default: "playwright")

        Returns:
            Dictionary with project information including id and path
        """
        try:
            project_id = str(uuid4())
            project_path = self._get_project_path(project_id)
            project_path.mkdir(parents=True, exist_ok=True)

            # Create project structure
            (project_path / "tests").mkdir(exist_ok=True)
            (project_path / "fixtures").mkdir(exist_ok=True)
            (project_path / "reports").mkdir(exist_ok=True)

            # Create project metadata
            metadata = {
                "id": project_id,
                "name": name,
                "description": description or "",
                "type": project_type,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "status": "active",
            }

            # Save metadata
            with open(self._get_project_metadata_path(project_id), "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Created project: {name} ({project_id})")

            return {
                "success": True,
                "project_id": project_id,
                "name": name,
                "path": str(project_path),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Failed to create project: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def create_project_from_url(
        self, url: str, name: str | None = None
    ) -> dict[str, Any]:
        """
        Create a project based on a target URL.

        Args:
            url: Target URL to test
            name: Optional project name (defaults to domain from URL)

        Returns:
            Dictionary with project information
        """
        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            project_name = name or f"Test {parsed_url.netloc}"

            # Create project
            result = await self.create_project(
                name=project_name, description=f"Testing project for {url}"
            )

            if result["success"]:
                # Add URL to metadata
                project_id = result["project_id"]
                metadata_path = self._get_project_metadata_path(project_id)

                with open(metadata_path) as f:
                    metadata = json.load(f)

                metadata["target_url"] = url
                metadata["updated_at"] = datetime.now().isoformat()

                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                result["metadata"]["target_url"] = url

            return result

        except Exception as e:
            logger.error(f"Failed to create project from URL: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def list_projects(self) -> list[dict[str, Any]]:
        """
        List all projects in the workspace.

        Returns:
            List of project metadata dictionaries
        """
        try:
            projects = []
            projects_dir = self._get_projects_dir()

            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    metadata_path = project_dir / "project.json"
                    if metadata_path.exists():
                        with open(metadata_path) as f:
                            metadata = json.load(f)
                            metadata["path"] = str(project_dir)
                            projects.append(metadata)

            # Sort by creation date (newest first)
            projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return projects

        except Exception as e:
            logger.error(f"Failed to list projects: {e}", exc_info=True)
            return []

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        """
        Get a specific project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project metadata dictionary or None if not found
        """
        try:
            metadata_path = self._get_project_metadata_path(project_id)

            if not metadata_path.exists():
                return None

            with open(metadata_path) as f:
                metadata = json.load(f)
                metadata["path"] = str(self._get_project_path(project_id))
                return metadata

        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
            return None

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project and all its contents.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            project_path = self._get_project_path(project_id)

            if not project_path.exists():
                logger.warning(f"Project {project_id} not found")
                return False

            # Remove project directory and contents
            shutil.rmtree(project_path)

            logger.info(f"Deleted project: {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
            return False

    async def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """
        Update project metadata.

        Args:
            project_id: Project identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            metadata_path = self._get_project_metadata_path(project_id)

            if not metadata_path.exists():
                return False

            with open(metadata_path) as f:
                metadata = json.load(f)

            # Update fields
            for key, value in updates.items():
                if key != "id":  # Don't allow changing the ID
                    metadata[key] = value

            metadata["updated_at"] = datetime.now().isoformat()

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Updated project: {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}", exc_info=True)
            return False
