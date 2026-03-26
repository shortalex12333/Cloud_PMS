"""
Combined Service — Subprocess Supervisor for Render Free Tier
=============================================================

Runs the FastAPI API + all 5 background workers + nightly feedback loop
as a single Render web service. Workers are spawned as subprocesses for
isolation (each has its own signal handlers, logging, and sys.exit scope).

Usage:
    uvicorn combined_service:app --host 0.0.0.0 --port $PORT

This file does NOT modify any original code. It imports pipeline_service.app
and adds a supervisor layer on top.
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Logging (combined service only — workers have their own)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [combined] %(levelname)s %(message)s",
)
logger = logging.getLogger("combined_service")

# ---------------------------------------------------------------------------
# Resolve working directory (apps/api)
# ---------------------------------------------------------------------------
API_DIR = Path(__file__).parent.resolve()

# ---------------------------------------------------------------------------
# Worker Definitions
# ---------------------------------------------------------------------------
WORKER_CONFIGS = {
    "projection": {
        "cmd": [sys.executable, "workers/projection_worker.py"],
        "env_gate": {"F1_PROJECTION_WORKER_ENABLED": "true"},
        "env_required": ["DATABASE_URL"],
    },
    "embedding": {
        "cmd": [sys.executable, "workers/embedding_worker_1536.py"],
        "env_gate": {},
        "env_required": ["DATABASE_URL", "OPENAI_API_KEY"],
    },
    "extraction": {
        "cmd": [sys.executable, "workers/extraction_worker.py"],
        "env_gate": {},
        "env_required": ["DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"],
    },
    "email_watcher": {
        "cmd": [sys.executable, "workers/email_watcher_worker.py"],
        "env_gate": {"EMAIL_WATCHER_ENABLED": "true"},
        "env_required": ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"],
    },
    "cache_listener": {
        "cmd": [sys.executable, "cache/invalidation_listener.py"],
        "env_gate": {},
        "env_required": ["REDIS_URL"],
    },
}

MAX_RESTARTS = 10
BACKOFF_BASE = 5      # seconds
BACKOFF_CAP = 120     # seconds
POLL_INTERVAL = 10    # seconds


# ---------------------------------------------------------------------------
# Worker State
# ---------------------------------------------------------------------------
class WorkerState:
    __slots__ = ("name", "proc", "restarts", "last_start", "last_exit_code",
                 "status", "backoff")

    def __init__(self, name: str):
        self.name = name
        self.proc: Optional[subprocess.Popen] = None
        self.restarts = 0
        self.last_start: Optional[float] = None
        self.last_exit_code: Optional[int] = None
        self.status = "pending"   # pending | running | stopped | failed
        self.backoff = BACKOFF_BASE


workers: Dict[str, WorkerState] = {}


# ---------------------------------------------------------------------------
# Subprocess Management
# ---------------------------------------------------------------------------
def _build_env() -> dict:
    """Build environment for child processes — inherit everything."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _can_start(config: dict) -> bool:
    """Check env gates and required vars."""
    for key, expected in config["env_gate"].items():
        if os.environ.get(key, "").lower() != expected.lower():
            logger.warning("Worker skipped — %s != %s", key, expected)
            return False
    for key in config["env_required"]:
        if not os.environ.get(key):
            logger.warning("Worker skipped — missing env var %s", key)
            return False
    return True


def spawn_worker(name: str) -> Optional[subprocess.Popen]:
    """Launch a worker subprocess."""
    config = WORKER_CONFIGS[name]
    logger.info("Spawning worker: %s  cmd=%s", name, " ".join(config["cmd"]))
    try:
        proc = subprocess.Popen(
            config["cmd"],
            cwd=str(API_DIR),
            env=_build_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return proc
    except Exception as e:
        logger.error("Failed to spawn %s: %s", name, e)
        return None


# ---------------------------------------------------------------------------
# Log Relay — tails subprocess stdout and logs it
# ---------------------------------------------------------------------------
async def relay_logs(name: str, proc: subprocess.Popen):
    """Read subprocess stdout line-by-line and relay to combined logger."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                logger.info("[%s] %s", name, text)
        except Exception:
            break


# ---------------------------------------------------------------------------
# Supervisor Loop
# ---------------------------------------------------------------------------
async def supervisor_loop():
    """Poll worker processes, restart crashed ones with backoff."""
    while True:
        try:
            for name, state in workers.items():
                if state.status in ("failed", "pending"):
                    continue

                if state.proc is None:
                    continue

                ret = state.proc.poll()
                if ret is not None:
                    # Process exited
                    state.last_exit_code = ret
                    logger.warning(
                        "Worker %s exited with code %d (restarts=%d)",
                        name, ret, state.restarts,
                    )

                    if state.restarts >= MAX_RESTARTS:
                        state.status = "failed"
                        logger.error(
                            "Worker %s exceeded max restarts (%d) — marking failed",
                            name, MAX_RESTARTS,
                        )
                        continue

                    # Exponential backoff
                    wait = min(state.backoff, BACKOFF_CAP)
                    logger.info("Restarting %s in %ds...", name, wait)
                    await asyncio.sleep(wait)
                    state.backoff = min(state.backoff * 2, BACKOFF_CAP)
                    state.restarts += 1

                    proc = spawn_worker(name)
                    if proc:
                        state.proc = proc
                        state.last_start = time.time()
                        state.status = "running"
                        # Relay logs for new process
                        asyncio.create_task(relay_logs(name, proc))
                    else:
                        state.status = "failed"
                else:
                    # Process still alive — reset backoff after 5 min of stability
                    if (state.last_start and
                            time.time() - state.last_start > 300):
                        state.backoff = BACKOFF_BASE

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Supervisor error: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Nightly Feedback Scheduler
# ---------------------------------------------------------------------------
class NightlyScheduler:
    def __init__(self):
        self.last_run_date: Optional[str] = None  # "YYYY-MM-DD"
        self.last_run_time: Optional[str] = None   # ISO timestamp

    async def run(self):
        """Check every 60s, run feedback loop at 3 AM UTC once per day."""
        while True:
            try:
                now = datetime.now(timezone.utc)
                today = now.strftime("%Y-%m-%d")

                if (now.hour == 3 and
                        now.minute < 2 and
                        self.last_run_date != today):

                    if not os.environ.get("DATABASE_URL"):
                        logger.warning("Nightly feedback skipped — no DATABASE_URL")
                    else:
                        logger.info("Launching nightly feedback loop...")
                        self.last_run_date = today
                        self.last_run_time = now.isoformat()

                        try:
                            proc = subprocess.Popen(
                                [sys.executable, "workers/nightly_feedback_loop.py"],
                                cwd=str(API_DIR),
                                env=_build_env(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                            )
                            # Wait for completion in background thread
                            loop = asyncio.get_event_loop()
                            ret = await loop.run_in_executor(None, proc.wait)
                            logger.info(
                                "Nightly feedback loop finished (exit=%d)", ret
                            )
                        except Exception as e:
                            logger.error("Nightly feedback error: %s", e)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Nightly scheduler error: %s", e)

            await asyncio.sleep(60)


nightly = NightlyScheduler()


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
_background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Combined Service Starting ===")

    # Spawn workers
    for name, config in WORKER_CONFIGS.items():
        state = WorkerState(name)
        workers[name] = state

        if not _can_start(config):
            state.status = "pending"
            logger.info("Worker %s: skipped (env check failed)", name)
            continue

        proc = spawn_worker(name)
        if proc:
            state.proc = proc
            state.last_start = time.time()
            state.status = "running"
            # Start log relay
            task = asyncio.create_task(relay_logs(name, proc))
            _background_tasks.append(task)
        else:
            state.status = "failed"

    # Start supervisor
    sup_task = asyncio.create_task(supervisor_loop())
    _background_tasks.append(sup_task)

    # Start nightly scheduler
    nightly_task = asyncio.create_task(nightly.run())
    _background_tasks.append(nightly_task)

    logger.info("=== All workers launched, supervisor active ===")

    yield

    # Shutdown — terminate all workers
    logger.info("=== Combined Service Shutting Down ===")

    for name, state in workers.items():
        if state.proc and state.proc.poll() is None:
            logger.info("Sending SIGTERM to %s (pid=%d)", name, state.proc.pid)
            try:
                state.proc.terminate()
            except OSError:
                pass

    # Give workers 5s to exit gracefully
    deadline = time.time() + 5
    for name, state in workers.items():
        if state.proc and state.proc.poll() is None:
            remaining = max(0, deadline - time.time())
            try:
                state.proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                logger.warning("Force-killing %s", name)
                state.proc.kill()

    # Cancel background tasks
    for task in _background_tasks:
        task.cancel()

    logger.info("=== Shutdown complete ===")


# ---------------------------------------------------------------------------
# App — mounts the original pipeline_service on top
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CelesteOS Combined Service",
    description="API + Workers unified for Render free tier",
    lifespan=lifespan,
)


# Workers health endpoint (on the outer app, before mount)
@app.get("/workers/health")
async def workers_health():
    result = {}
    for name, state in workers.items():
        uptime = None
        if state.status == "running" and state.last_start:
            uptime = round(time.time() - state.last_start)

        pid = None
        if state.proc and state.proc.poll() is None:
            pid = state.proc.pid

        result[name] = {
            "status": state.status,
            "pid": pid,
            "restarts": state.restarts,
            "uptime_s": uptime,
            "last_exit_code": state.last_exit_code,
        }

    return JSONResponse({
        "workers": result,
        "nightly_feedback": {
            "last_run": nightly.last_run_time,
            "last_run_date": nightly.last_run_date,
        },
    })


# Mount the original pipeline service — this gives us all existing routes
# at their original paths (/, /health, /healthz, /v1/bootstrap, etc.)
from pipeline_service import app as pipeline_app  # noqa: E402

app.mount("/", pipeline_app)
