"""
Base class for Celeste lens health monitors.

Provides:
  - JWT minting (same pattern as Playwright global-setup.ts)
  - Authenticated HTTP GET against API_BASE_URL
  - Supabase query to discover a live test entity ID
  - Retry-with-backoff + configurable interval loop
  - Structured JSON log output for log aggregators

Environment (all monitors share these):
    API_BASE_URL              Base URL of the API (e.g. http://api:8000 in Docker,
                              https://celeste-pipeline-v1.onrender.com in prod)
    TENANT_SUPABASE_URL       Supabase project URL for the tenant DB
    SUPABASE_SERVICE_KEY      Service-role key for Supabase (direct DB queries)
    TENANT_SUPABASE_JWT_SECRET  JWT secret — used to mint test tokens
    TEST_YACHT_ID             UUID of the test yacht
    TEST_HOD_USER_ID          UUID of the HoD test user (sub claim)
    HEALTH_CHECK_INTERVAL_MINUTES  How often to run (default: 15)
    LOG_LEVEL                 Logging level (default: INFO)
    MAX_RETRIES               API call retries per cycle (default: 3)
    RETRY_BACKOFF_SEC         Initial backoff seconds on failure (default: 5)
"""

from __future__ import annotations

import os
import sys
import time
import json
import logging
import signal
from datetime import datetime, timezone
from typing import Optional

import jwt        # PyJWT
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000").rstrip("/")
SUPABASE_URL = os.environ.get("TENANT_SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
JWT_SECRET   = os.environ.get("TENANT_SUPABASE_JWT_SECRET", "")
YACHT_ID     = os.environ.get("TEST_YACHT_ID", "")
USER_ID      = os.environ.get("TEST_HOD_USER_ID", "")
USER_EMAIL   = os.environ.get("TEST_HOD_EMAIL", "")
INTERVAL_MIN = int(os.environ.get("HEALTH_CHECK_INTERVAL_MINUTES", "15"))
LOG_LEVEL    = os.environ.get("LOG_LEVEL", "INFO").upper()
MAX_RETRIES  = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF_SEC", "5"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("HealthMonitor")

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info(f"Received signal {signum} — shutting down after current cycle")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ---------------------------------------------------------------------------
# JWT Minting
# ---------------------------------------------------------------------------

def mint_jwt(ttl_seconds: int = 3600) -> str:
    """
    Mint a Supabase-compatible JWT for the test HoD user.

    Matches the self-minting pattern in Playwright global-setup.ts:
      sub  = real user UUID (TEST_HOD_USER_ID)
      aud  = 'authenticated'
      role = 'authenticated'
      email included for Supabase RLS context
    """
    if not JWT_SECRET:
        raise RuntimeError("TENANT_SUPABASE_JWT_SECRET is not set")
    if not USER_ID:
        raise RuntimeError("TEST_HOD_USER_ID is not set")

    now = int(time.time())
    payload = {
        "sub":   USER_ID,
        "aud":   "authenticated",
        "role":  "authenticated",
        "email": USER_EMAIL,
        "iat":   now,
        "exp":   now + ttl_seconds,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# ---------------------------------------------------------------------------
# Supabase REST helper (raw REST, no supabase-py dependency)
# ---------------------------------------------------------------------------

def supabase_select(table: str, params: dict, limit: int = 1) -> list:
    """
    Direct Supabase REST query using the service key.

    Returns list of rows (may be empty).
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("TENANT_SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }

    # Build query string
    qs = {f"{k}": f"eq.{v}" for k, v in params.items()}
    qs["limit"] = str(limit)
    qs["select"] = "id"   # we only need the ID

    resp = requests.get(url, headers=headers, params=qs, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# API call helper
# ---------------------------------------------------------------------------

def api_get(path: str, token: str, timeout: int = 15) -> requests.Response:
    """
    Authenticated GET against API_BASE_URL.
    """
    url = f"{API_BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
    }
    return requests.get(url, headers=headers, timeout=timeout)


# ---------------------------------------------------------------------------
# Result logging
# ---------------------------------------------------------------------------

def log_result(
    monitor_name: str,
    entity_id: Optional[str],
    ok: bool,
    status_code: Optional[int],
    latency_ms: float,
    detail: str = "",
) -> None:
    record = {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "monitor":      monitor_name,
        "entity_id":    entity_id,
        "ok":           ok,
        "status_code":  status_code,
        "latency_ms":   round(latency_ms, 1),
        "detail":       detail,
    }
    level = logging.INFO if ok else logging.ERROR
    logger.log(level, json.dumps(record))


# ---------------------------------------------------------------------------
# Base Monitor class
# ---------------------------------------------------------------------------

class BaseHealthMonitor:
    """
    Subclass this and implement:
      - name: str                           — display name for logs
      - find_test_entity_id() -> str | None — Supabase query for a live entity
      - check_entity(entity_id, token)      — API call + assertion, returns (ok, status, detail)
    """

    name: str = "BaseHealthMonitor"

    def find_test_entity_id(self) -> Optional[str]:
        raise NotImplementedError

    def check_entity(self, entity_id: str, token: str) -> tuple[bool, Optional[int], str]:
        """
        Returns (success: bool, http_status: int | None, detail: str).
        """
        raise NotImplementedError

    # ------------------------------------------------------------------

    def run_once(self) -> bool:
        """
        Execute one health-check cycle. Returns True if healthy.
        """
        logger.info(f"[{self.name}] Starting health check cycle")

        # 1. Find a live entity to test
        try:
            entity_id = self.find_test_entity_id()
        except Exception as e:
            log_result(self.name, None, False, None, 0, f"entity_lookup_failed: {e}")
            return False

        if not entity_id:
            log_result(self.name, None, False, None, 0, "no_test_entity_found")
            logger.warning(
                f"[{self.name}] No entity found for yacht {YACHT_ID} — "
                "DB may be empty or YACHT_ID is wrong"
            )
            return False

        # 2. Mint JWT
        try:
            token = mint_jwt()
        except Exception as e:
            log_result(self.name, entity_id, False, None, 0, f"jwt_mint_failed: {e}")
            return False

        # 3. Call API with retry
        for attempt in range(1, MAX_RETRIES + 1):
            t0 = time.perf_counter()
            try:
                ok, status, detail = self.check_entity(entity_id, token)
                latency = (time.perf_counter() - t0) * 1000
                log_result(self.name, entity_id, ok, status, latency, detail)
                if ok:
                    return True
            except Exception as e:
                latency = (time.perf_counter() - t0) * 1000
                log_result(self.name, entity_id, False, None, latency, f"exception: {e}")

            if attempt < MAX_RETRIES:
                backoff = RETRY_BACKOFF * attempt
                logger.warning(f"[{self.name}] Attempt {attempt} failed — retrying in {backoff}s")
                time.sleep(backoff)

        return False

    def run_loop(self) -> None:
        """
        Run continuously at HEALTH_CHECK_INTERVAL_MINUTES intervals.
        """
        logger.info(
            f"[{self.name}] Starting — "
            f"API={API_BASE_URL}, yacht={YACHT_ID}, interval={INTERVAL_MIN}m"
        )

        cycle = 0
        while not _shutdown:
            cycle += 1
            healthy = self.run_once()
            status = "PASS" if healthy else "FAIL"
            logger.info(f"[{self.name}] Cycle {cycle}: {status}")

            if _shutdown:
                break

            sleep_sec = INTERVAL_MIN * 60
            logger.info(f"[{self.name}] Sleeping {sleep_sec}s until next check")
            # Sleep in 1s chunks so SIGTERM is handled promptly
            for _ in range(sleep_sec):
                if _shutdown:
                    break
                time.sleep(1)

        logger.info(f"[{self.name}] Stopped cleanly")
