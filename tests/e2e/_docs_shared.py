"""
_docs_shared.py — shared primitives for the Documents-domain Playwright runners.

Consumed by:
    documents_tree_runner.py       (shard 1)
    documents_splitbutton_runner.py (shard 2)
    documents_actions_runner.py    (shard 3)
    documents_handover_runner.py   (shard 4)

Pattern source: Cloud_PMS/tests/e2e/warranty_runner.py (canonical per
reference_domain_e2e_runner_pattern.md).

Auth model: MASTER JWT injection via localStorage pre-bootstrap
(reference_shard54_master_auth_pattern.md) — bypasses the Supabase UI login
entirely so we can run headless without hitting the slow bootstrap retry chain.
Fallback path: standard email/password login against /login.

Every public helper here MUST be side-effect-free against prod data other
than the explicit test yacht (85fe1119-b04c-41ac-80f1-829d23322598) and the
three test users (hod.test@/x@/crew.test@alex-short.com).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import traceback
import urllib.request
from typing import Any, Callable

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Sprint runner: set DOCS_BASE_URL=http://localhost:3015 (sprint Next.js dev server)
# Production smoke: DOCS_BASE_URL=https://app.celeste7.ai (after PR merge + deploy)
BASE_URL = os.environ.get("DOCS_BASE_URL", "http://localhost:3015")
API_BASE_URL = os.environ.get("DOCS_API_URL", "https://backend.celeste7.ai")

# Test yacht + users — see documents_mcp02_identity.md and
# reference_cloud_pms_db.md.
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
HOD_EMAIL = os.environ.get("DOCS_HOD_EMAIL", "hod.test@alex-short.com")
CAPTAIN_EMAIL = os.environ.get("DOCS_CAPTAIN_EMAIL", "x@alex-short.com")
CREW_EMAIL = os.environ.get("DOCS_CREW_EMAIL", "crew.test@alex-short.com")
PASSWORD = os.environ.get("DOCS_PASSWORD", "Password2!")

# TENANT DB — creds in reference_cloud_pms_db.md.
TENANT_DB_HOST = "db.vzsohavtuotocgrfkfyd.supabase.co"
TENANT_DB_PASSWORD = "@-Ei-9Pa.uENn6g"
PSQL_STATEMENT_TIMEOUT = "15s"

# SIGNED-action PIN — frontend-only gate, any 4 digits accepted.
TEST_PIN = "1234"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

STEP_TIMEOUT_MS = 10_000
NAV_TIMEOUT_MS = 25_000
POPUP_TIMEOUT_MS = 8_000
WARMUP_TIMEOUT_S = 90

NETWORK_PATTERNS = (
    "/api/v1/",
    "/v1/entity",
    "/v1/actions",
    "/v1/ledger",
    "/v1/attachments",
    "/v2/search",
)


# ---------------------------------------------------------------------------
# Render warm-up — same pattern as warranty_runner:64-83.
# ---------------------------------------------------------------------------


def warmup_render_api() -> None:
    if os.environ.get("DOCS_SKIP_WARMUP") == "1":
        print("[warmup] skipped via DOCS_SKIP_WARMUP=1", file=sys.stderr)
        return
    health_url = f"{API_BASE_URL}/health"
    deadline = time.monotonic() + WARMUP_TIMEOUT_S
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            with urllib.request.urlopen(health_url, timeout=10) as resp:
                if resp.status == 200:
                    print(f"[warmup] Render API warm after {attempt} attempt(s)", file=sys.stderr)
                    return
        except Exception as exc:
            print(f"[warmup] attempt {attempt}: {exc}", file=sys.stderr)
        time.sleep(2)
    print(f"[warmup] WARN: Render API silent after {WARMUP_TIMEOUT_S}s — tests may fail on bootstrap.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Result schema — mirror of warranty_runner.py:147-164.
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def new_result(scenario_id: str, name: str, role: str) -> dict:
    return {
        "scenario_id": scenario_id,
        "scenario_name": name,
        "role": role,
        "steps": [],
        "console_errors": [],
        "network": [],
        "db_asserts": [],
        "result": "pending",
        "ran_at": "",
    }


def finalize(res: dict) -> dict:
    res["ran_at"] = _now_iso()
    if res["result"] == "pending":
        steps_ok = all(s["pass"] for s in res["steps"])
        db_ok = all(a["pass"] for a in res["db_asserts"])
        res["result"] = "pass" if (steps_ok and db_ok) else "fail"
    return res


def step(res: dict, step_id: str, desc: str, fn: Callable[[], Any]) -> bool:
    try:
        fn()
        res["steps"].append({"id": step_id, "desc": desc, "pass": True, "error": None})
        return True
    except (PlaywrightTimeoutError, PlaywrightError, AssertionError) as e:
        res["steps"].append({"id": step_id, "desc": desc, "pass": False, "error": f"{type(e).__name__}: {e}"})
        return False
    except Exception as e:
        res["steps"].append({
            "id": step_id, "desc": desc, "pass": False,
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}",
        })
        return False


# ---------------------------------------------------------------------------
# Instrumentation — warranty_runner.py:196-226.
# ---------------------------------------------------------------------------


def instrument(page: Page, res: dict) -> None:
    def on_console(msg):
        if msg.type in ("error", "warning"):
            loc = msg.location or {}
            res["console_errors"].append({
                "type": msg.type, "text": msg.text,
                "url": loc.get("url"), "line": loc.get("lineNumber"),
            })

    def on_response(response):
        url = response.url
        if not any(pat in url for pat in NETWORK_PATTERNS):
            return
        body: Any = None
        try:
            ct = (response.headers.get("content-type") or "").lower()
            if "json" in ct:
                body = response.json()
        except Exception:
            body = None
        res["network"].append({
            "url": url, "status": response.status,
            "method": response.request.method, "body": body,
        })

    page.on("console", on_console)
    page.on("response", on_response)


# ---------------------------------------------------------------------------
# Auth — email/password login, same shape as warranty_runner.py:234-251.
# ---------------------------------------------------------------------------


def login(page: Page, email: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", timeout=NAV_TIMEOUT_MS)
    page.locator("input[type='email'], input[name='email']").first.fill(email, timeout=STEP_TIMEOUT_MS)
    page.locator("input[type='password'], input[name='password']").first.fill(password, timeout=STEP_TIMEOUT_MS)
    page.get_by_role("button", name=re.compile(r"(sign in|log in|login)", re.I)).first.click(timeout=STEP_TIMEOUT_MS)
    page.wait_for_function(
        "() => !window.location.pathname.startsWith('/login')",
        timeout=60_000,
    )
    page.wait_for_load_state("networkidle", timeout=30_000)


def ensure_logged_in(page: Page, email: str, password: str) -> None:
    """Login only if the page isn't already authenticated.
    Navigates to /login; if the email input doesn't appear within 3s
    (because auth already redirected us away), return immediately."""
    page.goto(f"{BASE_URL}/login", timeout=NAV_TIMEOUT_MS)
    try:
        page.locator("input[type='email'], input[name='email']").first.wait_for(
            state="visible", timeout=3000
        )
    except Exception:
        return  # already logged in
    page.locator("input[type='email'], input[name='email']").first.fill(email, timeout=STEP_TIMEOUT_MS)
    page.locator("input[type='password'], input[name='password']").first.fill(password, timeout=STEP_TIMEOUT_MS)
    page.get_by_role("button", name=re.compile(r"(sign in|log in|login)", re.I)).first.click(timeout=STEP_TIMEOUT_MS)
    page.wait_for_function(
        "() => !window.location.pathname.startsWith('/login')",
        timeout=60_000,
    )
    page.wait_for_load_state("networkidle", timeout=30_000)


# ---------------------------------------------------------------------------
# TENANT psql — direct DB cross-exam with 15s statement timeout.
# ---------------------------------------------------------------------------


def psql_scalar(sql: str) -> str:
    """Run a single SELECT against TENANT and return trimmed stdout.

    Uses env PGPASSWORD to avoid colon-in-password URL-encoding hell with the
    Supabase pooler format ("@-Ei-9Pa.uENn6g"). Conn string is keyword form
    (host=..., user=postgres) which the 15:01 drift probe proved works.
    """
    env = os.environ.copy()
    env["PGPASSWORD"] = TENANT_DB_PASSWORD
    conn = (
        f"host={TENANT_DB_HOST} port=5432 dbname=postgres "
        f"user=postgres sslmode=require"
    )
    wrapped = f"SET statement_timeout='{PSQL_STATEMENT_TIMEOUT}'; {sql}"
    cp = subprocess.run(
        ["psql", conn, "-t", "-A", "-c", wrapped],
        env=env, capture_output=True, text=True, timeout=30,
    )
    if cp.returncode != 0:
        raise AssertionError(f"psql failed: {cp.stderr.strip()}")
    return cp.stdout.strip()


def db_assert(res: dict, assert_id: str, desc: str, sql: str, expect: Callable[[str], bool]) -> bool:
    """Run a SELECT and record pass/fail based on the predicate."""
    try:
        got = psql_scalar(sql)
        ok = expect(got)
        res["db_asserts"].append({
            "id": assert_id, "desc": desc, "sql": sql,
            "result": got, "pass": bool(ok), "error": None,
        })
        return bool(ok)
    except Exception as e:
        res["db_asserts"].append({
            "id": assert_id, "desc": desc, "sql": sql,
            "result": None, "pass": False, "error": f"{type(e).__name__}: {e}",
        })
        return False


# ---------------------------------------------------------------------------
# Ledger + notification assertions — cross-cutting for shards 3 and 4.
# ---------------------------------------------------------------------------


def assert_ledger_row(res: dict, assert_id: str, entity_id: str, event_type: str, max_age_sec: int = 60) -> bool:
    """Expect a ledger_events row for this entity, action, within max_age_sec."""
    sql = (
        f"SELECT count(*) FROM ledger_events "
        f"WHERE entity_id='{entity_id}' "
        f"AND event_type='{event_type}' "
        f"AND created_at > now() - interval '{max_age_sec} seconds' "
        f"AND proof_hash IS NOT NULL"
    )
    return db_assert(
        res, assert_id,
        f"ledger_events row: {event_type} for {entity_id[:8]}... with proof_hash",
        sql,
        lambda r: r.strip().isdigit() and int(r.strip()) >= 1,
    )


def assert_notification_row(res: dict, assert_id: str, entity_id: str, max_age_sec: int = 60) -> bool:
    sql = (
        f"SELECT count(*) FROM pms_notifications "
        f"WHERE entity_id='{entity_id}' "
        f"AND created_at > now() - interval '{max_age_sec} seconds'"
    )
    return db_assert(
        res, assert_id,
        f"pms_notifications row for {entity_id[:8]}...",
        sql,
        lambda r: r.strip().isdigit() and int(r.strip()) >= 1,
    )


def assert_signature_row(res: dict, assert_id: str, entity_id: str, expected_method: str = "pin") -> bool:
    """SIGNED actions must produce a pms_audit_log row with signature.method set."""
    sql = (
        f"SELECT signature->>'method' FROM pms_audit_log "
        f"WHERE entity_id='{entity_id}' "
        f"AND created_at > now() - interval '120 seconds' "
        f"ORDER BY created_at DESC LIMIT 1"
    )
    return db_assert(
        res, assert_id,
        f"pms_audit_log.signature.method = '{expected_method}' for {entity_id[:8]}...",
        sql,
        lambda r: r.strip() == expected_method,
    )


# ---------------------------------------------------------------------------
# UUID guard — shard 1 requires 0 raw UUIDs visible in document.body.innerText.
# ---------------------------------------------------------------------------


UUID_RE_JS = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def count_uuids_in_dom(page: Page) -> int:
    """Count UUID-shaped strings in document.body.innerText (visible text only)."""
    js = (
        "() => {"
        " const re = /" + UUID_RE_JS + "/gi;"
        " const m = document.body.innerText.match(re);"
        " return m ? m.length : 0;"
        "}"
    )
    return int(page.evaluate(js))


def count_uuids_in_jsx_children(component_dir: str) -> int:
    """grep -roE UUID regex in JSX children under component_dir — should be 0."""
    cp = subprocess.run(
        ["grep", "-roE", UUID_RE_JS, component_dir],
        capture_output=True, text=True,
    )
    if cp.returncode not in (0, 1):
        raise AssertionError(f"grep failed: {cp.stderr}")
    return len([ln for ln in cp.stdout.splitlines() if ln.strip()])


# ---------------------------------------------------------------------------
# NDJSON emit — stdout, same as warranty_runner.
# ---------------------------------------------------------------------------


def emit(res: dict) -> None:
    print(json.dumps(res, default=str), flush=True)
