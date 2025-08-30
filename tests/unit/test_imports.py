#!/usr/bin/env python3
"""
Simple import test to verify all modules can be imported
"""

def test_core_imports():
    """Test that core modules can be imported"""
    # Test main app import
    from app.main import mcp
    assert mcp is not None
    
def test_http_server_imports():
    """Test that HTTP server can be imported"""
    from app.http_server import app
    assert app is not None
    
def test_workspace_imports():
    """Test that workspace modules can be imported"""
    from app.workspace_manager import WorkspaceManager
    assert WorkspaceManager is not None
    
def test_ai_imports():
    """Test that AI modules can be imported"""
    from app.ai_integration import AIProvider
    assert AIProvider is not None
    
def test_settings_imports():
    """Test that settings API can be imported"""
    from app.settings_api import setup_settings_api
    assert setup_settings_api is not None