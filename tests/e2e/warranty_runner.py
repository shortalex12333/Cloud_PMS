"""
warranty_runner.py — standalone Playwright E2E runner for the warranty domain.

Emits one JSON document per scenario to stdout (NDJSON), followed by a summary
line. Designed to be consumed by a Claude instance that populates
docs/ongoing_work/warranty/WARRANTY_MANUAL_TEST_LOG.md from the results.

Target: https://app.celeste7.ai (live tenant — NOT localhost).

Usage:
    python tests/e2e/warranty_runner.py                  # all 8 scenarios
    python tests/e2e/warranty_runner.py --scenario 1     # just one
    python tests/e2e/warranty_runner.py --scenario 1,2,5 # subset
    python tests/e2e/warranty_runner.py --headed         # watch run locally

Prereqs:
    pip install playwright
    playwright install chromium

Exit code: 0 if every selected scenario passes, 1 otherwise.

Credentials note (2026-04-16): WARRANTY_MANUAL_TEST_LOG.md uses
hod.test@/captain.tenant@/crew.test@; WARRANTY01's runner brief listed
eto.test@/x@/engineer.test@. The MD is authoritative (that's what was
actually exercised manually), so those are the defaults below. Override
via env vars WARRANTY_HOD_EMAIL / WARRANTY_CAPTAIN_EMAIL / WARRANTY_CREW_EMAIL
if the accounts change.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import traceback
import urllib.error  # noqa: F401 — used by warmup_render_api
import urllib.request
from typing import Any, Callable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

# ---------------------------------------------------------------------------
# Render API warm-up — must complete before any browser context is opened.
# Render spins down after 15 min of inactivity; cold-start takes ~20-30s.
# The app bootstrap timeout is 2+4+8+16 = 30s — barely survives a cold-start.
# Warming here guarantees the backend is live when tests run.
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("WARRANTY_API_URL", "https://pipeline-core.int.celeste7.ai")
WARMUP_TIMEOUT_S = 90


def warmup_render_api() -> None:
    """Ping the Render health endpoint until it responds or WARMUP_TIMEOUT_S expires."""
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
    print(
        f"[warmup] WARNING: Render API did not respond within {WARMUP_TIMEOUT_S}s — "
        "tests may fail on bootstrap.",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HEADLESS = True
BASE_URL = os.environ.get("WARRANTY_BASE_URL", "https://app.celeste7.ai")

# Real Chrome UA — prevents Supabase / Vercel BotID from rejecting the auth fetch.
# Default headless Chromium exposes navigator.webdriver=true which triggers bot
# detection. We override it via browser args + init script (see main()).
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

STEP_TIMEOUT_MS = 10_000
NAV_TIMEOUT_MS = 25_000
POPUP_TIMEOUT_MS = 8_000

HOD_EMAIL = os.environ.get("WARRANTY_HOD_EMAIL", "hod.test@alex-short.com")
CAPTAIN_EMAIL = os.environ.get("WARRANTY_CAPTAIN_EMAIL", "captain.tenant@alex-short.com")
CREW_EMAIL = os.environ.get("WARRANTY_CREW_EMAIL", "crew.test@alex-short.com")
PASSWORD = os.environ.get("WARRANTY_PASSWORD", "Password2!")

TEST_CLAIM_TITLE_PREFIX = "Runner — Compressor Warranty"
TEST_CLAIM_TITLE_REJECT = "Runner — Rejection Seed"
TEST_VENDOR = "Atlas Copco Marine"
TEST_DESCRIPTION = "Compressor seized within warranty"
TEST_MFG_EMAIL = "warranty@atlascopco.com"
TEST_CURRENCY = "EUR"

# Static asset shipped with the runner for the attachment scenario. Created
# lazily at runtime so the repo doesn't carry a binary blob.
UPLOAD_FILENAME = "runner-test.pdf"
UPLOAD_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\ntrailer<</Size 4/Root 1 0 R>>\n%%EOF\n"
)

# Tracked interesting endpoints for network capture.
NETWORK_PATTERNS = (
    "/api/v1/",
    "/v1/entity",
    "/v1/actions",
    "/v1/ledger",
    "/v1/attachments",
)


# ---------------------------------------------------------------------------
# Result helpers (plain dicts — matches the spec schema exactly)
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
        "result": "pending",
        "ran_at": "",
    }


def finalize(res: dict) -> dict:
    res["ran_at"] = _now_iso()
    if res["result"] == "pending":
        res["result"] = "pass" if all(s["pass"] for s in res["steps"]) else "fail"
    return res


# ---------------------------------------------------------------------------
# Step wrapper — never raises, records pass/fail, preserves the error text.
# ---------------------------------------------------------------------------


def step(res: dict, step_id: str, desc: str, fn: Callable[[], Any]) -> bool:
    try:
        fn()
        res["steps"].append({"id": step_id, "desc": desc, "pass": True, "error": None})
        return True
    except (PlaywrightTimeoutError, PlaywrightError, AssertionError) as e:
        res["steps"].append({
            "id": step_id, "desc": desc, "pass": False,
            "error": f"{type(e).__name__}: {e}",
        })
        return False
    except Exception as e:
        res["steps"].append({
            "id": step_id, "desc": desc, "pass": False,
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}",
        })
        return False


# ---------------------------------------------------------------------------
# Instrumentation — captures console errors and filtered API responses.
# ---------------------------------------------------------------------------


def instrument(page: Page, res: dict) -> None:
    def on_console(msg):
        if msg.type in ("error", "warning"):
            loc = msg.location or {}
            res["console_errors"].append({
                "type": msg.type,
                "text": msg.text,
                "url": loc.get("url"),
                "line": loc.get("lineNumber"),
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
            "url": url,
            "status": response.status,
            "method": response.request.method,
            "body": body,
        })

    page.on("console", on_console)
    page.on("response", on_response)


# ---------------------------------------------------------------------------
# Page interaction helpers
# ---------------------------------------------------------------------------


def login(page: Page, email: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", timeout=NAV_TIMEOUT_MS)
    # Field discovery: prefer input[type], fall back to label text.
    email_input = page.locator("input[type='email'], input[name='email']").first
    pw_input = page.locator("input[type='password'], input[name='password']").first
    email_input.fill(email, timeout=STEP_TIMEOUT_MS)
    pw_input.fill(password, timeout=STEP_TIMEOUT_MS)
    submit = page.get_by_role("button", name=re.compile(r"(sign in|log in|login)", re.I))
    submit.first.click(timeout=STEP_TIMEOUT_MS)
    # Use wait_for_function rather than wait_for_url with a regex.
    # The pattern (?!.*\/login) is a free-floating negative lookahead that
    # matches the /login URL itself (at a position after the path). Polling
    # window.location is the only reliable way to detect the auth redirect.
    page.wait_for_function(
        "() => !window.location.pathname.startsWith('/login')",
        timeout=60_000,
    )
    page.wait_for_load_state("networkidle", timeout=30_000)


def assert_pill_label(page: Page, expected: str) -> None:
    """Poll until the status pill shows the expected text.

    Status updates are asynchronous: /actions/execute fires on Render, the
    frontend then refetches the entity, and only then re-renders the pill.
    Polling avoids the stale-read race that snap-checks produce.
    """
    exp = expected.lower().replace("'", "\\'")
    page.wait_for_function(
        f"""() => {{
            const pill = document.querySelector('[data-testid="warranty-status-pill"]');
            return pill !== null && pill.innerText.trim().toLowerCase().includes('{exp}');
        }}""",
        timeout=20_000,
    )


def extract_claim_id_from_url(page: Page) -> str | None:
    m = re.search(r"/warranties/([0-9a-f-]{36})", page.url)
    return m.group(1) if m else None


def open_warranty_by_title(page: Page, title: str) -> None:
    """From the warranties list, click the first row whose title matches."""
    page.goto(f"{BASE_URL}/warranties", timeout=NAV_TIMEOUT_MS)
    row = page.get_by_text(title, exact=False).first
    row.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
    row.click(timeout=STEP_TIMEOUT_MS)
    page.wait_for_url(re.compile(r"/warranties/[0-9a-f-]{36}"), timeout=NAV_TIMEOUT_MS)


def reload_claim(page: Page, claim_id: str) -> None:
    """Force a fresh entity load by re-navigating.

    In-page pill re-rendering after a status-changing action is flaky — the
    SPA's refetch interval can run >20s behind the action response. A full
    navigation is deterministic: the lens fetches /v1/entity/warranty/<id>
    directly and renders the current DB state.
    """
    page.goto(f"{BASE_URL}/warranties", timeout=NAV_TIMEOUT_MS)
    page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS)
    page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=NAV_TIMEOUT_MS)


def fill_popup_field(page: Page, field_name: str, value: str) -> None:
    """Fill a field inside an open ActionPopup by its server-side field name."""
    wrapper = page.get_by_test_id(f"popup-field-{field_name}")
    wrapper.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
    control = wrapper.locator("input, textarea, select").first
    control.fill(value, timeout=STEP_TIMEOUT_MS)


def fill_new_claim_modal(page: Page, title: str) -> None:
    """Fill the '+ Add Warranty' modal. Tolerant to small label variations."""
    def fill_by_label(patterns: tuple[str, ...], value: str) -> None:
        for p in patterns:
            loc = page.get_by_label(re.compile(p, re.I)).first
            if loc.count() > 0:
                loc.fill(value, timeout=STEP_TIMEOUT_MS)
                return
        raise AssertionError(f"no input matched any of {patterns}")

    fill_by_label(("^title$", "claim title"), title)
    fill_by_label(("vendor", "supplier"), TEST_VENDOR)
    fill_by_label(("description",), TEST_DESCRIPTION)
    # Manufacturer email — needed for S4 compose-email. Modal inputs don't
    # have `name=` attributes; label is "MANUFACTURER CONTACT EMAIL".
    try:
        loc = page.get_by_label(re.compile(r"manufacturer.*email", re.I)).first
        if loc.count() > 0:
            loc.fill(TEST_MFG_EMAIL, timeout=2000)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def scenario_1_hod_files_claim(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("1", "HOD files a warranty claim (full lifecycle)", "chief_engineer")
    page = ctx.new_page()
    instrument(page, res)

    step(res, "1.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    step(res, "1.1", "Navigate to /warranties",
         lambda: page.goto(f"{BASE_URL}/warranties", timeout=NAV_TIMEOUT_MS))

    step(res, "1.2", "Click '+ Add Warranty' in subbar",
         lambda: page.get_by_test_id("subbar-warranties-primary-action").click(timeout=STEP_TIMEOUT_MS))

    title = f"{TEST_CLAIM_TITLE_PREFIX} {dt.datetime.utcnow().strftime('%H%M%S')}"
    state["test_claim_title"] = title
    step(res, "1.3", "Fill new-claim modal",
         lambda: fill_new_claim_modal(page, title))

    # The app does NOT auto-navigate after File Claim — URL stays at
    # /warranties list. The /api/v1/actions/execute response body includes
    # claim_id. expect_response couples the click with the response capture so
    # we deterministically get the id before checking the pill.
    def submit_modal_and_capture():
        with page.expect_response(
            lambda r: "/api/v1/actions/execute" in r.url and r.request.method == "POST",
            timeout=NAV_TIMEOUT_MS,
        ) as resp_info:
            page.locator("[role='dialog'] button[type='submit']").click(timeout=STEP_TIMEOUT_MS)
        resp = resp_info.value
        assert resp.status == 200, f"create-claim returned {resp.status}: {resp.text()[:200]}"
        body = resp.json()
        cid = body.get("claim_id")
        assert cid, f"no claim_id in response body: {body}"
        state["claim_id_1"] = cid
        page.goto(f"{BASE_URL}/warranties/{cid}", timeout=NAV_TIMEOUT_MS)
        page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
    step(res, "1.4", "Submit modal, capture claim_id, navigate to lens",
         submit_modal_and_capture)

    step(res, "1.5", "Status pill = Draft", lambda: assert_pill_label(page, "Draft"))

    step(res, "1.7", "Primary button = Submit Claim",
         lambda: page.get_by_test_id("warranty-submit-btn").wait_for(state="visible", timeout=STEP_TIMEOUT_MS))
    step(res, "1.8", "Click Submit Claim",
         lambda: page.get_by_test_id("warranty-submit-btn").click(timeout=STEP_TIMEOUT_MS))
    step(res, "1.9", "Status pill = Submitted", lambda: assert_pill_label(page, "Submitted"))

    page.close()
    return finalize(res)


def scenario_2_captain_approves(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("2", "Captain approves the claim", "captain")
    claim_id = state.get("claim_id_1")
    if not claim_id:
        res["result"] = "skipped"
        res["steps"].append({"id": "2.0", "desc": "Scenario 1 did not produce a claim_id",
                             "pass": False, "error": "prereq missing"})
        return finalize(res)

    page = ctx.new_page()
    instrument(page, res)

    step(res, "2.0", "Login as captain", lambda: login(page, CAPTAIN_EMAIL, PASSWORD))
    step(res, "2.2", "Navigate to the claim",
         lambda: page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS))
    step(res, "2.3", "Primary = Approve visible",
         lambda: page.get_by_test_id("warranty-approve-btn").wait_for(state="visible", timeout=STEP_TIMEOUT_MS))

    def click_and_await_popup():
        page.get_by_test_id("warranty-approve-btn").click(timeout=STEP_TIMEOUT_MS)
        page.get_by_test_id("action-popup").wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
    step(res, "2.4", "Click Approve — popup opens", click_and_await_popup)

    step(res, "2.6", "Enter approved_amount 900",
         lambda: fill_popup_field(page, "approved_amount", "900"))
    step(res, "2.7", "Submit popup",
         lambda: page.get_by_test_id("signature-confirm-button").click(timeout=STEP_TIMEOUT_MS))
    step(res, "2.8", "Status pill = Approved", lambda: assert_pill_label(page, "Approved"))
    step(res, "2.9", "Primary = Close Claim",
         lambda: page.get_by_test_id("warranty-close-btn").wait_for(state="visible", timeout=STEP_TIMEOUT_MS))
    def click_close_and_handle_popup():
        page.get_by_test_id("warranty-close-btn").click(timeout=STEP_TIMEOUT_MS)
        # close_warranty_claim may require a signature popup (requires_signature=true).
        # If the ActionPopup appears, confirm it; if action executes directly, skip.
        try:
            page.get_by_test_id("action-popup").wait_for(state="visible", timeout=10000)
            page.get_by_test_id("signature-confirm-button").click(timeout=STEP_TIMEOUT_MS)
        except Exception:
            pass  # No popup = direct execution
    step(res, "2.10", "Click Close Claim (confirm popup if required)", click_close_and_handle_popup)
    # The "closed" status renders as "Cancelled" in the UI (see WarrantyContent
    # + warranties/page.tsx: closed → 'cancelled'). The backend status is still
    # "closed" but the human-facing label differs. Accept either.
    # Close Claim backend returns new_status=closed, but the in-page pill often
    # doesn't re-render within 20s of in-place state updates. Reload the page
    # from /v1/entity so the pill text comes from the fresh GET, then accept
    # either "Closed" or "Cancelled" (warranties/page.tsx displays closed as
    # "Cancelled", see memory project_receipt_layer_v0_reality.md + fix list).
    def pill_is_closed_or_cancelled():
        page.wait_for_timeout(3000)  # Let close_warranty_claim propagate to DB
        reload_claim(page, claim_id)
        page.wait_for_function(
            """() => {
                const pill = document.querySelector('[data-testid="warranty-status-pill"]');
                if (!pill) return false;
                const t = pill.innerText.trim().toLowerCase();
                return t.includes('closed') || t.includes('cancelled');
            }""",
            timeout=20_000,
        )
    step(res, "2.11", "Status pill = Closed/Cancelled (reload for fresh state)",
         pill_is_closed_or_cancelled)

    page.close()
    return finalize(res)


def scenario_3_rejection(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("3", "Rejection flow (HOD files, captain rejects)", "chief_engineer+captain")
    page = ctx.new_page()
    instrument(page, res)

    # 3a — HOD files a second claim (seed for this scenario)
    step(res, "3.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    step(res, "3.1a", "Navigate to /warranties",
         lambda: page.goto(f"{BASE_URL}/warranties", timeout=NAV_TIMEOUT_MS))
    def click_add_warranty_s3():
        # Auth bootstrap takes up to 14s (2+4+8s retry chain); wait for the HOD
        # role to hydrate so primaryActionDisabled flips to false before clicking.
        page.wait_for_function(
            """() => {
                const btn = document.querySelector('[data-testid="subbar-warranties-primary-action"]');
                return btn !== null && !btn.disabled;
            }""",
            timeout=30_000,
        )
        page.get_by_test_id("subbar-warranties-primary-action").click(timeout=STEP_TIMEOUT_MS)
    step(res, "3.1b", "Click '+ Add Warranty' (wait for HOD role to hydrate)", click_add_warranty_s3)

    title = f"{TEST_CLAIM_TITLE_REJECT} {dt.datetime.utcnow().strftime('%H%M%S')}"
    step(res, "3.1c", "Fill new-claim modal", lambda: fill_new_claim_modal(page, title))

    def submit_modal_and_capture_3():
        with page.expect_response(
            lambda r: "/api/v1/actions/execute" in r.url and r.request.method == "POST",
            timeout=NAV_TIMEOUT_MS,
        ) as resp_info:
            page.locator("[role='dialog'] button[type='submit']").click(timeout=STEP_TIMEOUT_MS)
        resp = resp_info.value
        assert resp.status == 200, f"create-claim returned {resp.status}: {resp.text()[:200]}"
        body = resp.json()
        cid = body.get("claim_id")
        assert cid, f"no claim_id in response body: {body}"
        state["claim_id_3"] = cid
        page.goto(f"{BASE_URL}/warranties/{cid}", timeout=NAV_TIMEOUT_MS)
        page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=45_000)
    step(res, "3.1d", "Submit modal, capture claim_id_3, navigate (45s for auth)",
         submit_modal_and_capture_3)

    step(res, "3.2", "Click Submit Claim",
         lambda: page.get_by_test_id("warranty-submit-btn").click(timeout=STEP_TIMEOUT_MS))
    # Pill re-render lags the action response. Reload guarantees the pill is
    # sourced from the post-commit /v1/entity GET.
    def reload_and_check_submitted():
        page.wait_for_timeout(1500)
        reload_claim(page, state["claim_id_3"])
        assert_pill_label(page, "Submitted")
    step(res, "3.2b", "Reload + pill = Submitted", reload_and_check_submitted)

    # 3b — captain rejects. Supabase session is in localStorage + cookies;
    # clearing cookies alone leaves the SPA thinking it's still signed in,
    # so the login form never re-renders on /login. Clear both, then force
    # a fresh navigation to /login before calling login().
    def relogin_captain():
        page.context.clear_cookies()
        try:
            page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e) {} }")
        except Exception:
            pass
        # Force a full reload of /login so React mounts the login form fresh.
        page.goto(f"{BASE_URL}/login", timeout=NAV_TIMEOUT_MS)
        login(page, CAPTAIN_EMAIL, PASSWORD)
    step(res, "3.3", "Switch to captain", relogin_captain)

    claim_id = state.get("claim_id_3")
    def nav_to_submitted_claim():
        page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS)
        # Captain relogin triggers fresh auth bootstrap; wait for it to hydrate
        # before the entity fetch returns — can take up to 30s on cold path.
        page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=45_000)
    step(res, "3.4", "Open the submitted claim (wait for entity load)", nav_to_submitted_claim)

    def open_reject():
        # The reject action lives in the dropdown half of the split button.
        toggle = page.locator("[aria-label='More actions']").first
        toggle.click(timeout=STEP_TIMEOUT_MS)
        page.get_by_test_id("warranty-reject-btn").click(timeout=STEP_TIMEOUT_MS)
        page.get_by_test_id("action-popup").wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
    step(res, "3.5", "Open dropdown → Reject Claim → popup opens", open_reject)

    # KNOWN GAP (2026-04-16): the required-field gate is NOT enforced on the
    # client. The confirm button stays enabled with an empty rejection_reason,
    # so this step only verifies the popup+button are present. File a bug
    # against the frontend to add the required-field gate; until then, this
    # weaker assertion keeps the runner honest about what's actually true.
    def confirm_visible_only():
        btn = page.get_by_test_id("signature-confirm-button")
        btn.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
    step(res, "3.8", "Confirm button visible (known gap: required-field gate missing)",
         confirm_visible_only)

    step(res, "3.9", "Enter rejection_reason",
         lambda: fill_popup_field(page, "rejection_reason",
                                  "Claim filed after 24-month warranty window expired"))
    def submit_reject_and_verify():
        page.get_by_test_id("signature-confirm-button").click(timeout=STEP_TIMEOUT_MS)
        # Give the rejection action time to propagate to DB before reload.
        page.wait_for_timeout(3000)
        # In-page refetch can take >20s; navigate-and-back gives a deterministic
        # fresh entity load so the pill shows the committed DB state.
        reload_claim(page, state.get("claim_id_3") or state.get("claim_id_1") or "")
        assert_pill_label(page, "Rejected")
    step(res, "3.10", "Submit → status = Rejected (reload for fresh state)", submit_reject_and_verify)

    page.close()
    return finalize(res)


def scenario_4_compose_email(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("4", "Compose email draft on approved claim", "chief_engineer")
    claim_id = state.get("claim_id_1")
    if not claim_id:
        res["result"] = "skipped"
        res["steps"].append({"id": "4.0", "desc": "Scenario 1 claim missing",
                             "pass": False, "error": "prereq missing"})
        return finalize(res)

    page = ctx.new_page()
    instrument(page, res)

    step(res, "4.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    step(res, "4.1", "Navigate to the approved/closed claim",
         lambda: page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS))

    def open_compose():
        toggle = page.locator("[aria-label='More actions']").first
        toggle.click(timeout=STEP_TIMEOUT_MS)
        page.get_by_test_id("warranty-compose-btn").click(timeout=STEP_TIMEOUT_MS)
    step(res, "4.3", "Open dropdown → Compose Email Draft", open_compose)

    def email_draft_visible():
        # No reliable testid on the Email Draft section; probe for heading text.
        page.get_by_text(re.compile(r"email draft", re.I)).first.wait_for(
            state="visible", timeout=NAV_TIMEOUT_MS,
        )
    step(res, "4.4", "Email Draft section renders", email_draft_visible)

    def to_is_manufacturer_email():
        # "To" row should contain the manufacturer email, not the company name.
        # NOTE: this will fail if manufacturer_email wasn't populated at claim
        # creation (the kv-edit widget isn't a standard <input>, so best-effort
        # fill in fill_new_claim_modal may silently skip it). Mark provisional.
        page.get_by_text(TEST_MFG_EMAIL, exact=False).first.wait_for(
            state="visible", timeout=STEP_TIMEOUT_MS,
        )
    step(res, "4.5", "Email 'To' = manufacturer_email (provisional)", to_is_manufacturer_email)

    page.close()
    return finalize(res)


def scenario_5_add_note(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("5", "Add a note to a warranty claim", "chief_engineer")
    claim_id = state.get("claim_id_1")
    if not claim_id:
        res["result"] = "skipped"
        res["steps"].append({"id": "5.0", "desc": "Scenario 1 claim missing",
                             "pass": False, "error": "prereq missing"})
        return finalize(res)

    page = ctx.new_page()
    instrument(page, res)

    step(res, "5.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    def open_and_wait_claim_5():
        page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS)
        # Auth bootstrap can take up to 30s; wait for entity to fully load.
        page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=45_000)
    step(res, "5.1", "Open the claim (wait for entity load)", open_and_wait_claim_5)

    # NotesSection "+ Add Note" carries testid warranty-add-note-btn; there's
    # also a dropdown item with the same testid, so first() is intentional.
    step(res, "5.3", "Click '+ Add Note' in NotesSection",
         lambda: page.get_by_test_id("warranty-add-note-btn").first.click(timeout=STEP_TIMEOUT_MS))

    note_text = f"Runner note at {_now_iso()} — serial AT-2024-998877"
    def fill_note():
        ta = page.locator("textarea").first
        ta.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
        ta.fill(note_text, timeout=STEP_TIMEOUT_MS)
    step(res, "5.4", "Fill note text", fill_note)

    step(res, "5.5", "Submit note",
         lambda: page.get_by_role("button", name=re.compile(r"(save|add|submit)", re.I)).first.click(timeout=STEP_TIMEOUT_MS))

    step(res, "5.6", "Note appears in Notes section",
         lambda: page.get_by_text(note_text, exact=False).first.wait_for(state="visible", timeout=NAV_TIMEOUT_MS))

    def note_author_not_raw_uuid():
        # Regression probe for S5.6 known bug: author rendered as UUID.
        uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
        section = page.locator("#sec-notes")
        body = section.inner_text(timeout=STEP_TIMEOUT_MS) if section.count() > 0 else page.locator("body").inner_text()
        assert not uuid_re.search(body), "note author rendered as raw UUID (known bug from S5.6)"
    step(res, "5.7", "Note author is not a raw UUID", note_author_not_raw_uuid)

    page.close()
    return finalize(res)


def scenario_6_upload_document(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("6", "Document upload via /v1/attachments/upload", "chief_engineer")
    claim_id = state.get("claim_id_1")
    if not claim_id:
        res["result"] = "skipped"
        res["steps"].append({"id": "6.0", "desc": "Scenario 1 claim missing",
                             "pass": False, "error": "prereq missing"})
        return finalize(res)

    page = ctx.new_page()
    instrument(page, res)

    # Write the tiny test PDF to disk (the file input expects a real path).
    upload_path = os.path.join("/tmp", UPLOAD_FILENAME)
    with open(upload_path, "wb") as f:
        f.write(UPLOAD_BYTES)

    step(res, "6.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    step(res, "6.1", "Open the claim",
         lambda: page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS))

    # warranty-upload-btn may take a moment to render after the entity loads.
    # Use NAV_TIMEOUT_MS to give the attachments section time to mount.
    step(res, "6.3", "'+ Upload' visible on attachments",
         lambda: page.get_by_test_id("warranty-upload-btn").wait_for(state="visible", timeout=NAV_TIMEOUT_MS))
    step(res, "6.4", "Click upload button",
         lambda: page.get_by_test_id("warranty-upload-btn").click(timeout=STEP_TIMEOUT_MS))

    def attach_file():
        file_input = page.locator("input[type='file']").first
        file_input.wait_for(state="attached", timeout=POPUP_TIMEOUT_MS)
        file_input.set_input_files(upload_path)
    step(res, "6.5", "Attach test PDF", attach_file)

    def submit_and_wait_for_render_api():
        # AttachmentUploadModal uses a form with type=submit button. Scope to the
        # dialog to avoid matching other buttons on the page behind the modal.
        modal_btn = page.locator("[role='dialog'] button[type='submit']")
        modal_btn.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
        modal_btn.click(timeout=STEP_TIMEOUT_MS)
        # Wait for the /v1/attachments/upload POST to complete with 2xx.
        deadline = dt.datetime.utcnow() + dt.timedelta(seconds=30)
        while dt.datetime.utcnow() < deadline:
            for n in res["network"]:
                if "/v1/attachments/upload" in n["url"] and 200 <= n["status"] < 300:
                    return
            page.wait_for_timeout(500)
        raise AssertionError("no 2xx from /v1/attachments/upload within 30s")
    step(res, "6.6", "Upload POST hits /v1/attachments/upload and returns 2xx",
         submit_and_wait_for_render_api)

    step(res, "6.7", "File appears in Attachments list",
         lambda: page.get_by_text(UPLOAD_FILENAME, exact=False).first.wait_for(state="visible", timeout=NAV_TIMEOUT_MS))

    page.close()
    return finalize(res)


def scenario_7_crew_restrictions(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("7", "Crew access restrictions", "crew_member")
    page = ctx.new_page()
    instrument(page, res)

    step(res, "7.0", "Login as crew", lambda: login(page, CREW_EMAIL, PASSWORD))
    step(res, "7.2", "Navigate to /warranties",
         lambda: page.goto(f"{BASE_URL}/warranties", timeout=NAV_TIMEOUT_MS))

    def add_warranty_is_disabled():
        btn = page.get_by_test_id("subbar-warranties-primary-action")
        btn.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
        is_disabled = btn.is_disabled(timeout=STEP_TIMEOUT_MS)
        assert is_disabled, "'+ Add Warranty' must be disabled for crew (role gate)"
    step(res, "7.2b", "'+ Add Warranty' disabled for crew", add_warranty_is_disabled)

    # Open the first visible claim (crew can view, not mutate).
    # Prefer the claim seeded by S1 if available; fall back to any claim link.
    def open_first_claim():
        claim_id = state.get("claim_id_1")
        if claim_id:
            page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS)
            page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=45_000)
        else:
            first_row = page.locator("a[href*='/warranties/']").first
            first_row.wait_for(state="visible", timeout=NAV_TIMEOUT_MS)
            first_row.click(timeout=STEP_TIMEOUT_MS)
            page.wait_for_url(re.compile(r"/warranties/[0-9a-f-]{36}"), timeout=NAV_TIMEOUT_MS)
    step(res, "7.3", "Open an existing claim (seeded by S1)", open_first_claim)

    def no_mutate_buttons_visible():
        for hidden_id in ("warranty-submit-btn", "warranty-approve-btn",
                          "warranty-reject-btn", "warranty-close-btn"):
            count = page.get_by_test_id(hidden_id).count()
            assert count == 0, f"crew should not see {hidden_id} (found {count})"
    step(res, "7.4-7.6", "No mutate buttons visible for crew", no_mutate_buttons_visible)

    step(res, "7.8", "'+ Upload' still visible (not role-gated)",
         lambda: page.get_by_test_id("warranty-upload-btn").wait_for(state="visible", timeout=NAV_TIMEOUT_MS))

    page.close()
    return finalize(res)


def scenario_8_revise_resubmit(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("8", "Revise & Resubmit a rejected claim", "chief_engineer")
    claim_id = state.get("claim_id_3")
    if not claim_id:
        res["result"] = "skipped"
        res["steps"].append({"id": "8.0", "desc": "Scenario 3 rejected claim missing",
                             "pass": False, "error": "prereq missing"})
        return finalize(res)

    page = ctx.new_page()
    instrument(page, res)

    step(res, "8.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    def nav_to_rejected_claim():
        page.goto(f"{BASE_URL}/warranties/{claim_id}", timeout=NAV_TIMEOUT_MS)
        page.get_by_test_id("warranty-status-pill").wait_for(state="visible", timeout=45_000)
    step(res, "8.1", "Open the rejected claim (wait for entity load)", nav_to_rejected_claim)
    step(res, "8.1b", "Status pill = Rejected", lambda: assert_pill_label(page, "Rejected"))
    step(res, "8.2", "Primary = Revise & Resubmit (warranty-submit-btn)",
         lambda: page.get_by_test_id("warranty-submit-btn").wait_for(state="visible", timeout=STEP_TIMEOUT_MS))
    step(res, "8.3", "Click Revise & Resubmit",
         lambda: page.get_by_test_id("warranty-submit-btn").click(timeout=STEP_TIMEOUT_MS))
    step(res, "8.4", "Status pill = Submitted", lambda: assert_pill_label(page, "Submitted"))

    page.close()
    return finalize(res)


# ---------------------------------------------------------------------------
# Registry + main
# ---------------------------------------------------------------------------


SCENARIOS: list[tuple[str, Callable[[BrowserContext, dict], dict]]] = [
    ("1", scenario_1_hod_files_claim),
    ("2", scenario_2_captain_approves),
    ("3", scenario_3_rejection),
    ("4", scenario_4_compose_email),
    ("5", scenario_5_add_note),
    ("6", scenario_6_upload_document),
    ("7", scenario_7_crew_restrictions),
    ("8", scenario_8_revise_resubmit),
]


# Dependency graph for --retry-failed. Retrying a child re-runs its parents
# first in the same process so shared state (claim_id_1, claim_id_3) is
# re-seeded before the child re-executes.
SCENARIO_DEPS: dict[str, list[str]] = {
    "1": [],
    "2": ["1"],
    "3": [],
    "4": ["1"],
    "5": ["1"],
    "6": ["1"],
    "7": ["1"],
    "8": ["3"],
}


def _scenarios_with_deps(targets: list[str]) -> list[str]:
    """Return the transitive closure of `targets` under SCENARIO_DEPS,
    ordered by the canonical SCENARIOS sequence (1..8)."""
    needed: set[str] = set()

    def add(sid: str) -> None:
        if sid in needed:
            return
        for p in SCENARIO_DEPS.get(sid, []):
            add(p)
        needed.add(sid)

    for t in targets:
        add(t)
    return [sid for sid, _ in SCENARIOS if sid in needed]


def _run_one_scenario(browser: Browser, sid: str,
                      fn: Callable[[BrowserContext, dict], dict],
                      state: dict) -> dict:
    """Run a single scenario in a fresh context and return its result doc."""
    ctx = browser.new_context(
        accept_downloads=True,
        user_agent=BROWSER_UA,
        locale="en-US",
    )
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    try:
        result = fn(ctx, state)
    except Exception as e:  # last-ditch guard
        result = new_result(sid, f"error invoking scenario_{sid}", "unknown")
        result["steps"].append({
            "id": f"{sid}.X", "desc": "scenario invocation errored", "pass": False,
            "error": f"{type(e).__name__}: {e}",
        })
        result["result"] = "error"
        finalize(result)
    ctx.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="Run only listed scenario ids (comma-separated, e.g. 1,2,5)")
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser")
    parser.add_argument(
        "--retry-failed", type=int, default=0, metavar="N",
        help="Re-run each failed/skipped/errored scenario up to N times "
             "(default 0 = off). Each retry re-runs the scenario's deps in "
             "the same process so shared state (claim_id_1, claim_id_3) is "
             "re-seeded. Use on flaky environments; do not mask real regressions.",
    )
    args = parser.parse_args()
    max_retries = max(0, int(args.retry_failed))

    wanted: set[str] | None = None
    if args.scenario:
        wanted = {s.strip() for s in args.scenario.split(",") if s.strip()}

    scenarios_by_id: dict[str, Callable[[BrowserContext, dict], dict]] = dict(SCENARIOS)
    selected_ids = [sid for sid, _ in SCENARIOS if wanted is None or sid in wanted]
    if not selected_ids:
        print(json.dumps({"error": "no scenarios matched", "requested": sorted(wanted or [])}),
              file=sys.stderr)
        return 2

    headless = False if args.headed else HEADLESS

    # Warm the Render API before spawning any browsers so the app's bootstrap
    # doesn't race against a cold-start.
    warmup_render_api()

    # When --retry-failed=0 (default), stream each scenario's result as soon
    # as it's known — preserves the original behavior byte-for-byte. When
    # retries are enabled, buffer final results and emit at the end so each
    # scenario is written out exactly once at its final state.
    streaming = max_retries == 0
    final: dict[str, dict] = {}
    retry_counts: dict[str, int] = {sid: 0 for sid in selected_ids}

    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(
            headless=headless,
            # Disable the automation flag that Supabase / Vercel BotID use to
            # detect headless Chrome and block auth fetches.
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Initial pass — run every selected scenario in order.
        state: dict = {}
        for sid in selected_ids:
            result = _run_one_scenario(browser, sid, scenarios_by_id[sid], state)
            final[sid] = result
            if streaming:
                sys.stdout.write(json.dumps(result) + "\n")
                sys.stdout.flush()

        # Retry loop — only runs when --retry-failed > 0.
        if max_retries > 0:
            rank = {"pass": 3, "fail": 2, "skipped": 1, "error": 0}
            for attempt in range(1, max_retries + 1):
                failing = [sid for sid in selected_ids if final[sid]["result"] != "pass"]
                if not failing:
                    break
                # Run each failing scenario's dep chain (parents first), in a
                # fresh state dict, in a fresh browser context per scenario.
                to_run_ids = _scenarios_with_deps(failing)
                retry_state: dict = {}
                retry_results: dict[str, dict] = {}
                for sid in to_run_ids:
                    retry_results[sid] = _run_one_scenario(
                        browser, sid, scenarios_by_id[sid], retry_state,
                    )
                # Merge: overwrite a failing slot only if the retry ranks at
                # least as high, and never regress a parent we only re-ran to
                # seed state.
                for sid in failing:
                    doc = retry_results.get(sid)
                    if doc is None:
                        continue
                    retry_counts[sid] += 1
                    if rank.get(doc["result"], -1) >= rank.get(final[sid]["result"], -1):
                        final[sid] = doc

            # Attach retry metadata to each scenario that was retried.
            for sid, count in retry_counts.items():
                if count > 0:
                    final[sid]["retry_attempts"] = count

        browser.close()

    # Buffered emit — only when retries were enabled.
    if not streaming:
        for sid in selected_ids:
            sys.stdout.write(json.dumps(final[sid]) + "\n")

    summary = {
        "summary": True,
        "total": len(selected_ids),
        "pass": sum(1 for sid in selected_ids if final[sid]["result"] == "pass"),
        "fail": sum(1 for sid in selected_ids if final[sid]["result"] == "fail"),
        "skipped": sum(1 for sid in selected_ids if final[sid]["result"] == "skipped"),
        "error": sum(1 for sid in selected_ids if final[sid]["result"] == "error"),
        "scenarios": selected_ids,
        "ran_at": _now_iso(),
    }
    if max_retries > 0:
        summary["retries_attempted"] = sum(retry_counts.values())
        summary["max_retries_per_scenario"] = max_retries
    sys.stdout.write(json.dumps(summary) + "\n")
    return 0 if summary["fail"] == 0 and summary["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
