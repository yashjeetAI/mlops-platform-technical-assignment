"""Worker process: claim → execute deployments, woken by LISTEN/NOTIFY.

Push-based via Postgres LISTEN/NOTIFY (no Redis/broker), with a periodic poll as the
safety net and a reaper for crash recovery. Runs as its own container.
"""
import os
import socket
import time

from sqlalchemy import inspect

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal, engine
from app.worker import queue
from app.worker.executor import process_deployment

logger = get_logger("worker")

WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"
POLL_TIMEOUT_SECONDS = 5.0   # safety-net poll when no NOTIFY arrives
REAP_EVERY_SECONDS = 30.0


def _wait_for_schema(retries: int = 60) -> None:
    """Block until the backend has run migrations and the table exists."""
    for _ in range(retries):
        try:
            if inspect(engine).has_table("deployments"):
                return
        except Exception:  # noqa: BLE001 - DB may not be up yet
            pass
        time.sleep(1)
    raise RuntimeError("deployments table not available after waiting")


def _drain_all() -> int:
    """Claim and process jobs until the queue is empty. Returns count processed."""
    processed = 0
    while True:
        with SessionLocal() as db:
            deployment = queue.claim_one(db, WORKER_ID)
            if deployment is None:
                return processed
            process_deployment(db, deployment)
            processed += 1


def _open_listener():
    """Open a raw psycopg connection LISTENing on the notify channel, or None."""
    dsn = get_settings().database_url.replace("+psycopg", "")
    if not dsn.startswith("postgresql"):
        return None
    try:
        import psycopg

        conn = psycopg.connect(dsn, autocommit=True)
        conn.execute(f"LISTEN {queue.NOTIFY_CHANNEL}")
        logger.info("listening", channel=queue.NOTIFY_CHANNEL)
        return conn
    except Exception as exc:  # noqa: BLE001
        logger.warning("listen_unavailable", error=str(exc))
        return None


def _wait_for_notify(listener, timeout: float) -> None:
    """Block until a NOTIFY arrives or `timeout` elapses (push, with poll fallback)."""
    if listener is None:
        time.sleep(timeout)
        return
    try:
        for _ in listener.notifies(timeout=timeout, stop_after=1):
            break
    except Exception as exc:  # noqa: BLE001
        logger.warning("notify_wait_failed", error=str(exc))
        time.sleep(timeout)


def run() -> None:
    configure_logging()
    _wait_for_schema()
    logger.info("worker_started", worker_id=WORKER_ID)
    listener = _open_listener()
    last_reap = 0.0
    while True:
        _drain_all()

        now = time.monotonic()
        if now - last_reap > REAP_EVERY_SECONDS:
            with SessionLocal() as db:
                reaped = queue.reap_stuck(db)
            if reaped:
                logger.info("reaped_stuck", count=reaped)
            last_reap = now

        _wait_for_notify(listener, POLL_TIMEOUT_SECONDS)
