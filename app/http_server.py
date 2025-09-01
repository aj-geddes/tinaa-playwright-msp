#!/usr/bin/env python3
"""
TINAA HTTP Server with WebSocket support for streaming and real-time interaction
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/http_server.log"),
    ],
)
logger = logging.getLogger("tinaa-http")

import os

# Import the MCP handler functions
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai_enhanced_handler import (
    generate_accessibility_insights,
    generate_exploratory_insights,
    generate_security_insights,
)
from app.mcp_handler import detect_form_fields as handle_detect_form_fields
from app.mcp_handler import fill_form_fields as handle_fill_form_fields
from app.mcp_handler import generate_test_report as handle_generate_test_report
from app.mcp_handler import (
    get_controller,
)
from app.mcp_handler import navigate_to_url as handle_navigate_to_url
from app.mcp_handler import run_accessibility_test as handle_run_accessibility_test
from app.mcp_handler import run_exploratory_test as handle_run_exploratory_test
from app.mcp_handler import run_responsive_test as handle_run_responsive_test
from app.mcp_handler import run_security_test as handle_run_security_test
from app.mcp_handler import take_element_screenshot as handle_take_element_screenshot
from app.mcp_handler import take_page_screenshot as handle_take_page_screenshot
from app.settings_api import setup_settings_api
from app.workspace_manager import WorkspaceManager

# FastAPI app
app = FastAPI(
    title="TINAA - Testing Intelligence Network Automation Assistant", version="2.0.0"
)

# Enable CORS for IDE integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.session_data: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.session_data[client_id] = {
            "created": datetime.now(),
            "playbook": [],
            "current_step": None,
            "progress": [],
        }
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.session_data[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_progress(self, client_id: str, progress_data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(
                {"type": "progress", "data": progress_data}
            )
            self.session_data[client_id]["progress"].append(progress_data)

    async def send_message(self, client_id: str, message: str, level: str = "info"):
        await self.send_progress(
            client_id,
            {
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def broadcast(self, message: dict):
        for client_id, websocket in self.active_connections.items():
            await websocket.send_json(message)


manager = ConnectionManager()

# Initialize workspace manager lazily
workspace_manager = None


def get_workspace_manager():
    """Get or create workspace manager instance"""
    global workspace_manager
    if workspace_manager is None:
        import tempfile

        default_workspace = os.path.join(tempfile.gettempdir(), "workspace")
        workspace_manager = WorkspaceManager(
            workspace_path=os.getenv("WORKSPACE_PATH", default_workspace)
        )
    return workspace_manager


# Request models
class TestRequest(BaseModel):
    action: str
    parameters: dict[str, Any]
    client_id: str | None = None


class PlaybookStep(BaseModel):
    id: str
    action: str
    parameters: dict[str, Any]
    description: str | None = None
    expected_outcome: str | None = None


class PlaybookRequest(BaseModel):
    name: str
    steps: list[PlaybookStep]
    client_id: str


# Workspace request models
class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    template: str = "basic-web-testing"
    repository_url: str | None = None


class UrlProjectRequest(BaseModel):
    url: str
    name: str | None = None


# Progress tracking decorator
def track_progress(action_name: str):
    def decorator(func):
        async def wrapper(request: TestRequest):
            client_id = request.client_id
            if client_id:
                await manager.send_message(
                    client_id, f"Starting {action_name}...", "info"
                )

            try:
                result = await func(request)
                if client_id:
                    await manager.send_message(
                        client_id, f"Completed {action_name}", "success"
                    )
                return result
            except Exception as e:
                if client_id:
                    await manager.send_message(
                        client_id, f"Error in {action_name}: {e!s}", "error"
                    )
                raise

        return wrapper

    return decorator


# API Endpoints
@app.get("/")
async def root():
    return {"message": "TINAA HTTP Server is running", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Workspace Management Endpoints


@app.post("/api/workspace/projects")
async def create_project(request: ProjectCreateRequest):
    """Create a new project in the workspace"""
    try:
        result = await get_workspace_manager().create_project(
            name=request.name,
            description=request.description,
            template=request.template,
            repository_url=request.repository_url,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Failed to create project: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/projects/from-url")
async def create_project_from_url(request: UrlProjectRequest):
    """Create a project by analyzing a URL"""
    try:
        result = await get_workspace_manager().create_project_from_url(
            url=request.url, name=request.name
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Failed to create project from URL: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/projects")
async def list_projects():
    """List all projects in the workspace"""
    try:
        projects = await get_workspace_manager().list_projects()
        return JSONResponse(content={"projects": projects})
    except Exception as e:
        logger.error(f"Failed to list projects: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/projects/{project_id}")
async def get_project(project_id: str):
    """Get project information by ID"""
    try:
        project = await get_workspace_manager().get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return JSONResponse(content=project)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workspace/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project from the workspace"""
    try:
        success = await get_workspace_manager().delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return JSONResponse(content={"success": True, "message": "Project deleted"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/status")
async def workspace_status():
    """Get workspace status and statistics"""
    try:
        projects = await get_workspace_manager().list_projects()

        # Calculate workspace statistics
        total_projects = len(projects)
        active_projects = len([p for p in projects if p.get("status") != "archived"])

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
        }

        return JSONResponse(content=workspace_info)
    except Exception as e:
        logger.error(f"Failed to get workspace status: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/connectivity")
@track_progress("Browser Connectivity Test")
async def test_connectivity(request: TestRequest):
    # Test browser connectivity by getting controller
    try:
        # get_controller returns a controller synchronously
        controller = await asyncio.to_thread(get_controller)
        if controller and hasattr(controller, "browser") and controller.browser:
            result = "Browser connectivity test successful. Playwright is ready."
        else:
            result = "Browser not initialized. Starting browser..."
            controller = await asyncio.to_thread(get_controller)
            result = "Browser started successfully."
    except Exception as e:
        result = f"Browser connectivity test failed: {e!s}"

    return JSONResponse(content={"success": True, "result": result})


@app.post("/navigate")
@track_progress("Navigation")
async def navigate(request: TestRequest):
    url = request.parameters.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    # Pass context parameter expected by MCP handlers
    result = await handle_navigate_to_url(url, ctx=None)
    return JSONResponse(content={"success": True, "result": result})


@app.post("/screenshot")
@track_progress("Screenshot Capture")
async def screenshot(request: TestRequest):
    screenshot_type = request.parameters.get("type", "page")

    if screenshot_type == "element":
        selector = request.parameters.get("selector")
        if not selector:
            raise HTTPException(
                status_code=400,
                detail="Selector parameter is required for element screenshots",
            )
        result = await handle_take_element_screenshot(selector, ctx=None)
    else:
        full_page = request.parameters.get("full_page", True)
        result = await handle_take_page_screenshot(full_page, ctx=None)

    return JSONResponse(content={"success": True, "result": result})


@app.post("/test/exploratory")
async def exploratory_test(request: TestRequest):
    client_id = request.client_id
    url = request.parameters.get(
        "url", "https://example.com"
    )  # Default URL if not provided
    focus_area = request.parameters.get("focus_area", "general")

    async def stream_test():
        if client_id:
            await manager.send_message(
                client_id, "Starting exploratory test...", "info"
            )
            await manager.send_progress(
                client_id, {"phase": "initialization", "progress": 0}
            )

        # Run the test with progress updates
        result = await handle_run_exploratory_test(url, focus_area, ctx=None)

        if client_id:
            await manager.send_progress(
                client_id, {"phase": "analyzing", "progress": 50}
            )
            await manager.send_message(client_id, "Generating AI insights...", "info")

        # Generate AI insights if the test was successful
        if result.get("success") and not result.get("error"):
            ai_insights = await generate_exploratory_insights(
                url=url,
                title=result.get("title", ""),
                screenshot_data=result.get("initial_screenshot"),
                focus_area=focus_area,
            )

            # Add AI insights to the result
            result["ai_insights"] = ai_insights

            if client_id:
                if ai_insights.get("insights"):
                    await manager.send_message(
                        client_id, "AI insights generated successfully", "success"
                    )
                else:
                    await manager.send_message(
                        client_id, "AI insights not available", "warning"
                    )

        if client_id:
            await manager.send_progress(
                client_id, {"phase": "complete", "progress": 100}
            )

        yield json.dumps({"success": True, "result": result}).encode()

    return StreamingResponse(stream_test(), media_type="application/json")


@app.post("/test/accessibility")
async def accessibility_test(request: TestRequest):
    client_id = request.client_id
    url = request.parameters.get("url", "")

    async def stream_test():
        if client_id:
            await manager.send_message(
                client_id, "Starting accessibility test...", "info"
            )

        result = await handle_run_accessibility_test(ctx=None)

        # Generate AI insights if the test was successful
        if result.get("success") and not result.get("error"):
            if client_id:
                await manager.send_message(
                    client_id, "Generating AI analysis...", "info"
                )

            ai_analysis = await generate_accessibility_insights(
                accessibility_results=result.get("results", {}),
                url=url or "current page",
            )

            # Add AI analysis to the result
            result["ai_analysis"] = ai_analysis

        if client_id:
            await manager.send_message(
                client_id, "Accessibility test completed", "success"
            )

        yield json.dumps({"success": True, "result": result}).encode()

    return StreamingResponse(stream_test(), media_type="application/json")


@app.post("/test/security")
async def security_test(request: TestRequest):
    client_id = request.client_id
    url = request.parameters.get("url", "")

    async def stream_test():
        if client_id:
            await manager.send_message(client_id, "Starting security test...", "info")

        result = await handle_run_security_test(ctx=None)

        # Generate AI insights if the test was successful
        if result.get("success") and not result.get("error"):
            if client_id:
                await manager.send_message(
                    client_id, "Generating AI security analysis...", "info"
                )

            ai_analysis = await generate_security_insights(
                security_observations=result.get("results", {}),
                url=url or "current page",
            )

            # Add AI analysis to the result
            result["ai_analysis"] = ai_analysis

        if client_id:
            await manager.send_message(client_id, "Security test completed", "success")

        yield json.dumps({"success": True, "result": result}).encode()

    return StreamingResponse(stream_test(), media_type="application/json")


@app.post("/playbook/execute")
async def execute_playbook(request: PlaybookRequest):
    client_id = request.client_id
    playbook_id = str(uuid.uuid4())

    if client_id in manager.session_data:
        manager.session_data[client_id]["current_playbook"] = {
            "id": playbook_id,
            "name": request.name,
            "steps": request.steps,
            "status": "running",
            "results": [],
        }

    async def stream_execution():
        results = []

        for i, step in enumerate(request.steps):
            if client_id:
                await manager.send_progress(
                    client_id,
                    {
                        "playbook_id": playbook_id,
                        "step": i + 1,
                        "total_steps": len(request.steps),
                        "action": step.action,
                        "status": "running",
                    },
                )

            try:
                # Execute the step based on action
                step_result = await execute_step(step)
                results.append(
                    {
                        "step_id": step.id,
                        "action": step.action,
                        "status": "success",
                        "result": step_result,
                    }
                )

                if client_id:
                    await manager.send_progress(
                        client_id,
                        {
                            "playbook_id": playbook_id,
                            "step": i + 1,
                            "status": "completed",
                            "result": step_result,
                        },
                    )

            except Exception as e:
                results.append(
                    {
                        "step_id": step.id,
                        "action": step.action,
                        "status": "error",
                        "error": str(e),
                    }
                )

                if client_id:
                    await manager.send_progress(
                        client_id,
                        {
                            "playbook_id": playbook_id,
                            "step": i + 1,
                            "status": "error",
                            "error": str(e),
                        },
                    )

        final_result = {
            "playbook_id": playbook_id,
            "name": request.name,
            "status": "completed",
            "results": results,
        }

        if client_id in manager.session_data:
            manager.session_data[client_id]["current_playbook"]["status"] = "completed"
            manager.session_data[client_id]["current_playbook"]["results"] = results

        yield json.dumps(final_result).encode()

    return StreamingResponse(stream_execution(), media_type="application/json")


async def execute_step(step: PlaybookStep) -> dict:
    """Execute a single playbook step"""
    action_map = {
        "navigate": lambda p: handle_navigate_to_url(p.get("url"), ctx=None),
        "screenshot": lambda p: handle_take_page_screenshot(
            p.get("full_page", True), ctx=None
        ),
        "fill_form": lambda p: handle_fill_form_fields(p.get("fields", {}), ctx=None),
        "test_exploratory": lambda p: handle_run_exploratory_test(
            p.get("url", "https://example.com"),
            p.get("focus_area", "general"),
            ctx=None,
        ),
        "test_accessibility": lambda p: handle_run_accessibility_test(ctx=None),
        "test_responsive": lambda p: handle_run_responsive_test(ctx=None),
        "test_security": lambda p: handle_run_security_test(ctx=None),
        "detect_forms": lambda p: handle_detect_form_fields(ctx=None),
        "generate_report": lambda p: handle_generate_test_report(ctx=None),
    }

    if step.action not in action_map:
        raise ValueError(f"Unknown action: {step.action}")

    return await action_map[step.action](step.parameters)


# WebSocket endpoint for real-time interaction
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_json()

            # Handle different message types
            if data["type"] == "ping":
                await websocket.send_json({"type": "pong"})

            elif data["type"] == "execute":
                # Execute a single action with real-time feedback
                request = TestRequest(
                    action=data["action"],
                    parameters=data.get("parameters", {}),
                    client_id=client_id,
                )

                # Route to appropriate handler
                if data["action"] == "navigate":
                    result = await navigate(request)
                elif data["action"] == "screenshot":
                    result = await screenshot(request)
                elif data["action"] == "test_exploratory":
                    result = await exploratory_test(request)
                elif data["action"] == "test_accessibility":
                    result = await accessibility_test(request)
                elif data["action"] == "test_security":
                    result = await security_test(request)
                # Add more action handlers as needed

                await websocket.send_json(
                    {"type": "result", "action": data["action"], "result": result}
                )

            elif data["type"] == "playbook_builder":
                # Handle playbook builder interactions
                await handle_playbook_builder(websocket, client_id, data)

    except WebSocketDisconnect:
        manager.disconnect(client_id)


async def handle_playbook_builder(websocket: WebSocket, client_id: str, data: dict):
    """Handle playbook builder interactions"""
    command = data.get("command")

    if command == "add_step":
        step = data.get("step")
        manager.session_data[client_id]["playbook"].append(step)
        await websocket.send_json(
            {
                "type": "playbook_updated",
                "playbook": manager.session_data[client_id]["playbook"],
            }
        )

    elif command == "remove_step":
        step_id = data.get("step_id")
        playbook = manager.session_data[client_id]["playbook"]
        manager.session_data[client_id]["playbook"] = [
            s for s in playbook if s.get("id") != step_id
        ]
        await websocket.send_json(
            {
                "type": "playbook_updated",
                "playbook": manager.session_data[client_id]["playbook"],
            }
        )

    elif command == "get_suggestions":
        # Provide intelligent suggestions based on current context
        suggestions = await get_playbook_suggestions(client_id)
        await websocket.send_json({"type": "suggestions", "suggestions": suggestions})


async def get_playbook_suggestions(client_id: str) -> list[dict]:
    """Provide intelligent suggestions for next playbook steps"""
    session = manager.session_data.get(client_id, {})
    playbook = session.get("playbook", [])

    suggestions = []

    if not playbook:
        # Initial suggestions
        suggestions = [
            {"action": "navigate", "description": "Navigate to a URL"},
            {"action": "test_connectivity", "description": "Test browser connectivity"},
        ]
    else:
        last_action = playbook[-1].get("action") if playbook else None

        if last_action == "navigate":
            suggestions = [
                {"action": "screenshot", "description": "Take a screenshot"},
                {"action": "detect_forms", "description": "Detect form fields"},
                {"action": "test_exploratory", "description": "Run exploratory test"},
            ]
        elif last_action == "detect_forms":
            suggestions = [
                {"action": "fill_form", "description": "Fill form fields"},
                {
                    "action": "test_accessibility",
                    "description": "Test form accessibility",
                },
            ]

    return suggestions


# Setup settings API routes
setup_settings_api(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
