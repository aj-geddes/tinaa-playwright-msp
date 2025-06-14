#!/usr/bin/env python3
"""
TINAA HTTP Server with WebSocket support for streaming and real-time interaction
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/http_server.log"),
    ]
)
logger = logging.getLogger("tinaa-http")

# Import the MCP handler functions
from mcp_handler import (
    navigate_to_url as handle_navigate_to_url,
    take_page_screenshot as handle_take_page_screenshot,
    take_element_screenshot as handle_take_element_screenshot,
    fill_login_form as handle_fill_login_form,
    detect_form_fields as handle_detect_form_fields,
    fill_form_fields as handle_fill_form_fields,
    run_exploratory_test as handle_run_exploratory_test,
    run_accessibility_test as handle_run_accessibility_test,
    run_responsive_test as handle_run_responsive_test,
    run_security_test as handle_run_security_test,
    generate_test_report as handle_generate_test_report,
    prompt_for_credentials as handle_prompt_for_credentials,
    get_controller
)

# FastAPI app
app = FastAPI(title="TINAA - Test Intelligence and Automation Advanced", version="2.0.0")

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
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.session_data[client_id] = {
            "created": datetime.now(),
            "playbook": [],
            "current_step": None,
            "progress": []
        }
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.session_data[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_progress(self, client_id: str, progress_data: Dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "type": "progress",
                "data": progress_data
            })
            self.session_data[client_id]["progress"].append(progress_data)

    async def send_message(self, client_id: str, message: str, level: str = "info"):
        await self.send_progress(client_id, {
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast(self, message: Dict):
        for client_id, websocket in self.active_connections.items():
            await websocket.send_json(message)

manager = ConnectionManager()

# Request models
class TestRequest(BaseModel):
    action: str
    parameters: Dict[str, Any]
    client_id: Optional[str] = None

class PlaybookStep(BaseModel):
    id: str
    action: str
    parameters: Dict[str, Any]
    description: Optional[str] = None
    expected_outcome: Optional[str] = None

class PlaybookRequest(BaseModel):
    name: str
    steps: List[PlaybookStep]
    client_id: str

# Progress tracking decorator
def track_progress(action_name: str):
    def decorator(func):
        async def wrapper(request: TestRequest):
            client_id = request.client_id
            if client_id:
                await manager.send_message(client_id, f"Starting {action_name}...", "info")
            
            try:
                result = await func(request)
                if client_id:
                    await manager.send_message(client_id, f"Completed {action_name}", "success")
                return result
            except Exception as e:
                if client_id:
                    await manager.send_message(client_id, f"Error in {action_name}: {str(e)}", "error")
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

@app.post("/test/connectivity")
@track_progress("Browser Connectivity Test")
async def test_connectivity(request: TestRequest):
    # Test browser connectivity by getting controller
    try:
        # get_controller returns a controller synchronously
        controller = await asyncio.to_thread(get_controller)
        if controller and hasattr(controller, 'browser') and controller.browser:
            result = "Browser connectivity test successful. Playwright is ready."
        else:
            result = "Browser not initialized. Starting browser..."
            controller = await asyncio.to_thread(get_controller)
            result = "Browser started successfully."
    except Exception as e:
        result = f"Browser connectivity test failed: {str(e)}"
    
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
            raise HTTPException(status_code=400, detail="Selector parameter is required for element screenshots")
        result = await handle_take_element_screenshot(selector, ctx=None)
    else:
        full_page = request.parameters.get("full_page", True)
        result = await handle_take_page_screenshot(full_page, ctx=None)
    
    return JSONResponse(content={"success": True, "result": result})

@app.post("/test/exploratory")
async def exploratory_test(request: TestRequest):
    client_id = request.client_id
    
    async def stream_test():
        if client_id:
            await manager.send_message(client_id, "Starting exploratory test...", "info")
            await manager.send_progress(client_id, {"phase": "initialization", "progress": 0})
        
        # Run the test with progress updates
        result = await handle_run_exploratory_test(ctx=None)
        
        if client_id:
            await manager.send_progress(client_id, {"phase": "complete", "progress": 100})
        
        yield json.dumps({"success": True, "result": result}).encode()
    
    return StreamingResponse(stream_test(), media_type="application/json")

@app.post("/test/accessibility")
async def accessibility_test(request: TestRequest):
    client_id = request.client_id
    
    async def stream_test():
        if client_id:
            await manager.send_message(client_id, "Starting accessibility test...", "info")
        
        result = await handle_run_accessibility_test(ctx=None)
        
        if client_id:
            await manager.send_message(client_id, "Accessibility test completed", "success")
        
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
            "results": []
        }
    
    async def stream_execution():
        results = []
        
        for i, step in enumerate(request.steps):
            if client_id:
                await manager.send_progress(client_id, {
                    "playbook_id": playbook_id,
                    "step": i + 1,
                    "total_steps": len(request.steps),
                    "action": step.action,
                    "status": "running"
                })
            
            try:
                # Execute the step based on action
                step_result = await execute_step(step)
                results.append({
                    "step_id": step.id,
                    "action": step.action,
                    "status": "success",
                    "result": step_result
                })
                
                if client_id:
                    await manager.send_progress(client_id, {
                        "playbook_id": playbook_id,
                        "step": i + 1,
                        "status": "completed",
                        "result": step_result
                    })
                
            except Exception as e:
                results.append({
                    "step_id": step.id,
                    "action": step.action,
                    "status": "error",
                    "error": str(e)
                })
                
                if client_id:
                    await manager.send_progress(client_id, {
                        "playbook_id": playbook_id,
                        "step": i + 1,
                        "status": "error",
                        "error": str(e)
                    })
        
        final_result = {
            "playbook_id": playbook_id,
            "name": request.name,
            "status": "completed",
            "results": results
        }
        
        if client_id in manager.session_data:
            manager.session_data[client_id]["current_playbook"]["status"] = "completed"
            manager.session_data[client_id]["current_playbook"]["results"] = results
        
        yield json.dumps(final_result).encode()
    
    return StreamingResponse(stream_execution(), media_type="application/json")

async def execute_step(step: PlaybookStep) -> Dict:
    """Execute a single playbook step"""
    action_map = {
        "navigate": lambda p: handle_navigate_to_url(p.get("url"), ctx=None),
        "screenshot": lambda p: handle_take_page_screenshot(p.get("full_page", True), ctx=None),
        "fill_form": lambda p: handle_fill_form_fields(p.get("fields", {}), ctx=None),
        "test_exploratory": lambda p: handle_run_exploratory_test(ctx=None),
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
                    client_id=client_id
                )
                
                # Route to appropriate handler
                if data["action"] == "navigate":
                    result = await navigate(request)
                elif data["action"] == "screenshot":
                    result = await screenshot(request)
                # Add more action handlers as needed
                
                await websocket.send_json({
                    "type": "result",
                    "action": data["action"],
                    "result": result
                })
            
            elif data["type"] == "playbook_builder":
                # Handle playbook builder interactions
                await handle_playbook_builder(websocket, client_id, data)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)

async def handle_playbook_builder(websocket: WebSocket, client_id: str, data: Dict):
    """Handle playbook builder interactions"""
    command = data.get("command")
    
    if command == "add_step":
        step = data.get("step")
        manager.session_data[client_id]["playbook"].append(step)
        await websocket.send_json({
            "type": "playbook_updated",
            "playbook": manager.session_data[client_id]["playbook"]
        })
    
    elif command == "remove_step":
        step_id = data.get("step_id")
        playbook = manager.session_data[client_id]["playbook"]
        manager.session_data[client_id]["playbook"] = [
            s for s in playbook if s.get("id") != step_id
        ]
        await websocket.send_json({
            "type": "playbook_updated",
            "playbook": manager.session_data[client_id]["playbook"]
        })
    
    elif command == "get_suggestions":
        # Provide intelligent suggestions based on current context
        suggestions = await get_playbook_suggestions(client_id)
        await websocket.send_json({
            "type": "suggestions",
            "suggestions": suggestions
        })

async def get_playbook_suggestions(client_id: str) -> List[Dict]:
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
                {"action": "test_accessibility", "description": "Test form accessibility"},
            ]
    
    return suggestions

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)