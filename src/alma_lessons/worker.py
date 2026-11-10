"""
ALMA Academy — Background Worker Service
========================================
Runs asynchronous generation and regeneration tasks.
Supports both 'inprocess' (FastAPI BackgroundTasks / Threading)
and 'rq' (Redis Queue) backends.

Run with:
    python -m alma_lessons.worker
"""

import sys
import os
import time
import logging
from typing import Optional, Dict, Any

from .config import config
from .generation.tasks import (
    run_generation_task,
    run_regeneration_task,
    cleanup_stale_jobs_on_startup,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("alma.worker")


def enqueue_generation_job(job_id: str, request_data: Dict[str, Any], background_tasks=None):
    """Enqueue a lesson generation job depending on configured JOB_BACKEND."""
    if config.job_backend == "rq":
        try:
            from redis import Redis
            from rq import Queue
            redis_conn = Redis.from_url(config.redis_url)
            q = Queue("alma_generation", connection=redis_conn)
            q.enqueue(run_generation_task, job_id, request_data, job_timeout="10m")
            logger.info(f"Enqueued job {job_id} to RQ (Redis: {config.redis_url})")
            return
        except Exception as e:
            logger.warning(f"Failed to enqueue to RQ ({e}). Falling back to inprocess execution.")

    # Fallback or default inprocess execution
    if background_tasks is not None:
        background_tasks.add_task(run_generation_task, job_id, request_data)
    else:
        import threading
        t = threading.Thread(target=run_generation_task, args=(job_id, request_data), daemon=True)
        t.start()


def enqueue_regeneration_job(job_id: str, lesson_id: str, request_data: Dict[str, Any], background_tasks=None):
    """Enqueue a lesson regeneration job depending on configured JOB_BACKEND."""
    if config.job_backend == "rq":
        try:
            from redis import Redis
            from rq import Queue
            redis_conn = Redis.from_url(config.redis_url)
            q = Queue("alma_generation", connection=redis_conn)
            q.enqueue(run_regeneration_task, job_id, lesson_id, request_data, job_timeout="10m")
            logger.info(f"Enqueued regeneration job {job_id} to RQ (Redis: {config.redis_url})")
            return
        except Exception as e:
            logger.warning(f"Failed to enqueue to RQ ({e}). Falling back to inprocess execution.")

    # Fallback or default inprocess execution
    if background_tasks is not None:
        background_tasks.add_task(run_regeneration_task, job_id, lesson_id, request_data)
    else:
        import threading
        t = threading.Thread(target=run_regeneration_task, args=(job_id, lesson_id, request_data), daemon=True)
        t.start()


def main():
    logger.info(f"Starting ALMA Worker Service (JOB_BACKEND={config.job_backend})...")
    cleanup_stale_jobs_on_startup()

    if config.job_backend == "rq":
        try:
            from redis import Redis
            from rq import Worker, Queue, Connection
            redis_conn = Redis.from_url(config.redis_url)
            with Connection(redis_conn):
                worker = Worker(["alma_generation"])
                logger.info("RQ Worker listening on 'alma_generation' queue...")
                worker.work()
        except ImportError:
            logger.error("RQ or Redis package not installed. Install with `pip install rq redis` to run RQ workers.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to connect to Redis at {config.redis_url}: {e}")
            sys.exit(1)
    else:
        logger.info("ALMA Worker running in standby mode for inprocess / polling jobs. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
