"""
Flora OS — Standalone Scheduler Worker
Run this independently of Streamlit so morning brief emails are
delivered reliably even when no browser is open.

Usage:
    python scheduler_worker.py

Keep this running in the background (Windows Task Scheduler handles auto-start).
"""

import sys
import os
import time
import logging
from datetime import datetime, timezone

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create logs directory before logger initialises
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)

_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "scheduler.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("flora.scheduler_worker")


def main():
    logger.info("Flora OS Scheduler Worker starting...")

    # Bootstrap DB
    from app.database import init_db
    init_db()
    logger.info("Database initialised.")

    # Start scheduler
    from app.scheduler.morning_brief import start_scheduler
    start_scheduler()
    logger.info("Scheduler started. Waiting for jobs…")
    logger.info("Morning briefs will be sent at each user's configured time.")

    # Keep process alive — scheduler runs in background threads
    try:
        while True:
            now = datetime.now(timezone.utc)
            logger.debug("Heartbeat %s", now.strftime("%Y-%m-%d %H:%M:%S UTC"))
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler worker stopped by user.")
        from app.scheduler.morning_brief import stop_scheduler
        stop_scheduler()


if __name__ == "__main__":
    main()
