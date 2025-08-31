#!/usr/bin/env python3
"""
Minimalist MCP server runner script with proper signal handling
"""
import logging
import os
import signal
import sys
import threading
import time
import traceback

# Configure logging to use a file instead of stderr/stdout to avoid breaking MCP
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/mcp_server.log"),
    ],
)
logger = logging.getLogger("tinaa-playwright-msp")

# Log Python environment information
logger.info(f"Python version: {sys.version}")
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current directory: {os.getcwd()}")

# Global flag to track running state
running = True


# Set up signal handling to exit gracefully
def signal_handler(sig, frame):
    global running
    logger.info(f"Received signal {sig}, shutting down...")
    running = False


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger.info("Starting MCP server...")

try:
    # Log FastMCP version info
    try:
        import fastmcp

        logger.info(f"FastMCP version: {fastmcp.__version__}")
    except Exception as e:
        logger.error(f"Error importing FastMCP: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Import and run the MCP server
    try:
        from app.main import mcp

        logger.info("Successfully imported MCP server from app.main")
    except Exception as e:
        logger.error(f"Error importing MCP server from app.main: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Create an event to signal when MCP is running
    mcp_running = threading.Event()

    def run_mcp():
        logger.info("Starting MCP server in thread...")
        try:
            # Redirect all stdout/stderr to avoid interfering with MCP protocol
            stdout_log = open("logs/stdout.log", "w")
            stderr_log = open("logs/stderr.log", "w")
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_log
            sys.stderr = stderr_log

            # Run MCP server - this will block until shutdown
            logger.info("Running MCP server...")
            mcp.run()

            logger.info("MCP server thread exited")
        except Exception as e:
            logger.error(f"Error in MCP server thread: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            stdout_log.close()
            stderr_log.close()
            global running
            running = False

    # Start MCP in a separate thread
    mcp_thread = threading.Thread(target=run_mcp)
    mcp_thread.daemon = True
    mcp_thread.start()

    logger.info("MCP server started in background thread")

    # Keep the main thread alive
    while running and mcp_thread.is_alive():
        time.sleep(1)

    logger.info("MCP server shutting down...")

except Exception as e:
    logger.error(f"Error starting MCP server: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)
