import logging
import time
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Load env variables first
load_dotenv()

# Initialize memory early
from memory import get_memory_instance
memory = get_memory_instance()

from scheduler import start_scheduler, stop_scheduler
from telegram_bot import run_bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing Tom Agent...")
    
    # 0. Start Dummy Web Server for Render Port Binding
    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Tom is ALIVE!")
            
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info(f"Binded health check server to port {port}")

    # 1. Start Background Scheduler
    start_scheduler()
    
    try:
        # 2. Start Telegram Bot (blocks until stopped)
        logger.info("Tom is coming online...")
        run_bot()
    except KeyboardInterrupt:
        logger.info("Tom shut down locally.")
    except Exception as e:
        logger.error(f"Tom failed with error: {e}")
    finally:
        logger.info("Stopping scheduler...")
        stop_scheduler()

if __name__ == '__main__':
    # Ensure playwright is installed at least structurally on Render/VPS
    import subprocess
    try:
        import playwright
        # Check if browser needs to be installed, useful on VPS
        # Note: on Render usually need to run `playwright install chromium` in build script
    except ImportError:
        logger.warning("Playwright not found, proceeding with caution.")
    
    main()
