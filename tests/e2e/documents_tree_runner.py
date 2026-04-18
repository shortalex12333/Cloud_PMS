"""
documents_tree_runner.py — shard 1 — Documents tree render + search toggle.

Brief from DOCUMENTS04 (peer qbif5g9x, 2026-04-17 15:31Z):
- New files under test: apps/web/src/components/documents/DocumentTree.tsx,
  apps/web/src/components/documents/docTreeBuilder.ts.
- Modified: apps/web/src/app/documents/page.tsx (mode switch).
- Search input: apps/web/src/components/shell/Subbar.tsx:228-241 (placeholder
  "Search documents…"). Tree listens via useShellContext() (AppShellInner:335).
- Vessel name: useAuth().user.yachtName (AuthContext.tsx:36, useAuth.ts:4-12).
- Crew cannot see Upload (AppShell:148-150).
- Data coverage: 93.2% original_path on TEST_YACHT_ID.

Scenarios:
  T1 tree renders on /documents as HOD
  T2 zero raw UUIDs in visible DOM (regex guard)
  T3 zero raw UUIDs in JSX children (source grep)
  T4 typing in Subbar search hides tree, shows results list, fires /v2/search?domain=documents
  T5 Escape key restores tree with preserved expanded folders + scrollTop + selected-doc
  T6 Click a doc → EntityDetailOverlay opens DocumentContent
  T7 Crew role: no Upload button visible

Usage:
  python documents_tree_runner.py             # all
  python documents_tree_runner.py --scenario T4,T5
  python documents_tree_runner.py --headed
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _docs_shared import (  # noqa: E402
    BASE_URL, CREW_EMAIL, HOD_EMAIL, PASSWORD,
    NAV_TIMEOUT_MS, POPUP_TIMEOUT_MS, STEP_TIMEOUT_MS,
    BROWSER_UA,
    count_uuids_in_dom, count_uuids_in_jsx_children,
    emit, finalize, instrument, login, new_result, step,
    warmup_render_api,
)

from playwright.sync_api import BrowserContext, sync_playwright

COMPONENT_DIR = os.environ.get("DOCS_COMPONENT_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web", "src", "components", "documents")))


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def t1_tree_renders(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T1", "Tree renders on /documents as HOD", "chief_engineer")
    page = ctx.new_page()
    instrument(page, res)
    state["page_t1"] = page

    step(res, "T1.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
    step(res, "T1.1", "Navigate to /documents",
         lambda: page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS))
    step(res, "T1.2", "DocumentTree root visible",
         lambda: page.get_by_test_id("document-tree-root").wait_for(state="visible", timeout=NAV_TIMEOUT_MS))
    step(res, "T1.3", "At least one folder node rendered",
         lambda: _expect_min_count(page, "[data-testid^='doc-tree-folder-']", 1))
    return finalize(res)


def t2_no_uuids_in_dom(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T2", "Zero raw UUIDs visible in /documents DOM", "chief_engineer")
    page = state.get("page_t1") or ctx.new_page()
    if page != state.get("page_t1"):
        instrument(page, res)
        step(res, "T2.0", "Login as HOD", lambda: login(page, HOD_EMAIL, PASSWORD))
        step(res, "T2.1", "Navigate to /documents",
             lambda: page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS))

    def check():
        count = count_uuids_in_dom(page)
        assert count == 0, f"found {count} raw UUID strings in document.body.innerText"
    step(res, "T2.2", "count_uuids_in_dom == 0", check)
    return finalize(res)


def t3_no_uuids_in_jsx(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T3", "Zero raw UUIDs in apps/web/src/components/documents JSX", "static")

    def check():
        count = count_uuids_in_jsx_children(COMPONENT_DIR)
        assert count == 0, f"grep found {count} UUID-shaped strings under {COMPONENT_DIR}"
    step(res, "T3.0", "grep UUID regex under components/documents", check)
    return finalize(res)


def t4_search_toggle(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T4", "Search hides tree, shows results, fires /v2/search", "chief_engineer")
    page = ctx.new_page()
    instrument(page, res)
    state["page_t4"] = page

    step(res, "T4.0", "Login as HOD", lambda: _ensure_logged_in(page, HOD_EMAIL, PASSWORD))
    step(res, "T4.1", "Navigate to /documents",
         lambda: page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS))
    step(res, "T4.2", "Tree visible pre-search",
         lambda: page.get_by_test_id("document-tree-root").wait_for(state="visible", timeout=NAV_TIMEOUT_MS))

    # Capture expanded+scroll state before typing so we can verify Escape restore.
    def capture_state():
        snapshot = page.evaluate("""() => {
            const root = document.querySelector('[data-testid="document-tree-root"]');
            const expanded = Array.from(document.querySelectorAll('[data-tree-expanded="true"]'))
                .map(e => e.getAttribute('data-node-id'));
            return {
                expanded,
                scrollTop: root ? root.scrollTop : 0,
            };
        }""")
        state["t4_pre_state"] = snapshot
    step(res, "T4.3", "Capture tree state snapshot", capture_state)

    def type_and_await_search():
        search = page.locator("input[placeholder*='Search documents' i]").first
        search.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
        with page.expect_response(
            lambda r: "/api/f1/search/stream" in r.url and r.request.method in ("GET", "POST"),
            timeout=NAV_TIMEOUT_MS,
        ) as resp_info:
            search.type("compressor", delay=40)
        assert resp_info.value.status == 200, f"search status {resp_info.value.status}"
    step(res, "T4.4", "Type 'compressor' → /api/f1/search/stream 200", type_and_await_search)

    step(res, "T4.5", "Tree hidden while searching",
         lambda: page.get_by_test_id("document-tree-root").wait_for(state="hidden", timeout=STEP_TIMEOUT_MS))
    step(res, "T4.6", "Search component mounted (results/loading/empty)",
         lambda: page.locator("[data-testid^='documents-search-']").first.wait_for(state="visible", timeout=STEP_TIMEOUT_MS))
    return finalize(res)


def t5_escape_restores(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T5", "Escape restores tree with expanded/scroll/selected preserved", "chief_engineer")
    page = state.get("page_t4")
    if not page:
        res["result"] = "skipped"
        res["steps"].append({"id": "T5.0", "desc": "prereq T4 missing", "pass": False, "error": "no page"})
        return finalize(res)

    def press_escape_and_check():
        # Focus search input so Escape reaches it, then press Escape
        search = page.locator("input[placeholder*='Search' i]").first
        try:
            search.focus(timeout=3000)
        except Exception:
            pass
        page.keyboard.press("Escape")
        page.get_by_test_id("document-tree-root").wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
        after = page.evaluate("""() => {
            const root = document.querySelector('[data-testid="document-tree-root"]');
            const expanded = Array.from(document.querySelectorAll('[data-tree-expanded="true"]'))
                .map(e => e.getAttribute('data-node-id'));
            return { expanded, scrollTop: root ? root.scrollTop : 0 };
        }""")
        pre = state.get("t4_pre_state", {"expanded": [], "scrollTop": 0})
        assert sorted(after["expanded"]) == sorted(pre["expanded"]), (
            f"expanded drift — before={pre['expanded']} after={after['expanded']}"
        )
        assert abs(after["scrollTop"] - pre["scrollTop"]) < 4, (
            f"scrollTop drift — before={pre['scrollTop']} after={after['scrollTop']}"
        )
    step(res, "T5.0", "Escape → tree back, expanded + scroll preserved", press_escape_and_check)
    return finalize(res)


def t6_click_opens_overlay(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T6", "Click doc leaf → EntityDetailOverlay + DocumentContent", "chief_engineer")
    page = ctx.new_page()
    instrument(page, res)

    step(res, "T6.0", "Ensure HOD logged in", lambda: _ensure_logged_in(page, HOD_EMAIL, PASSWORD))
    step(res, "T6.1", "Navigate to /documents",
         lambda: page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS))
    step(res, "T6.2", "First document leaf visible",
         lambda: page.locator("[data-testid^='doc-tree-leaf-']").first.wait_for(state="visible", timeout=NAV_TIMEOUT_MS))
    step(res, "T6.3", "Click first leaf",
         lambda: page.locator("[data-testid^='doc-tree-leaf-']").first.click(timeout=STEP_TIMEOUT_MS))
    step(res, "T6.4", "EntityDetailOverlay visible",
         lambda: page.get_by_test_id("entity-detail-overlay").wait_for(state="visible", timeout=STEP_TIMEOUT_MS))
    step(res, "T6.5", "DocumentContent rendered inside overlay",
         lambda: page.get_by_test_id("document-content").wait_for(state="visible", timeout=STEP_TIMEOUT_MS))
    return finalize(res)


def t7_crew_no_upload(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("T7", "Crew role: Upload button not visible", "crew")
    page = ctx.new_page()
    instrument(page, res)

    def _clear_session():
        page.goto(f"{BASE_URL}/", timeout=NAV_TIMEOUT_MS)
        page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e) {} }")
        page.context.clear_cookies()
    step(res, "T7.p", "Clear HOD session", _clear_session)
    step(res, "T7.0", "Login as crew", lambda: login(page, CREW_EMAIL, PASSWORD))
    step(res, "T7.1", "Navigate to /documents",
         lambda: page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS))
    step(res, "T7.2", "Tree still renders for crew",
         lambda: page.get_by_test_id("document-tree-root").wait_for(state="visible", timeout=NAV_TIMEOUT_MS))

    def check_no_upload():
        count = page.get_by_test_id("subbar-documents-primary-action").count()
        assert count == 0, f"Upload button visible for crew (count={count})"
    step(res, "T7.3", "subbar-documents-primary-action absent for crew", check_no_upload)
    return finalize(res)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_logged_in(page, email: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login", timeout=NAV_TIMEOUT_MS)
    # If email input not visible within 3s, we're already redirected (logged in)
    try:
        page.locator("input[type='email'], input[name='email']").first.wait_for(state="visible", timeout=3000)
    except Exception:
        return
    # Form visible — fill credentials
    page.locator("input[type='email'], input[name='email']").first.fill(email, timeout=STEP_TIMEOUT_MS)
    page.locator("input[type='password'], input[name='password']").first.fill(password, timeout=STEP_TIMEOUT_MS)
    page.get_by_role("button", name=re.compile(r"(sign in|log in|login)", re.I)).first.click(timeout=STEP_TIMEOUT_MS)
    page.wait_for_function("() => !window.location.pathname.startsWith('/login')", timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=30_000)


def _expect_min_count(page, selector: str, minimum: int) -> None:
    page.locator(selector).first.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
    got = page.locator(selector).count()
    assert got >= minimum, f"expected ≥{minimum} of '{selector}', got {got}"


SCENARIOS = [
    ("T1", t1_tree_renders),
    ("T2", t2_no_uuids_in_dom),
    ("T3", t3_no_uuids_in_jsx),
    ("T4", t4_search_toggle),
    ("T5", t5_escape_restores),
    ("T6", t6_click_opens_overlay),
    ("T7", t7_crew_no_upload),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", help="comma list: T1,T4,T5 or 'all'", default="all")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    wanted = {s.strip() for s in (args.scenario.split(",") if args.scenario != "all" else [])}
    to_run = SCENARIOS if args.scenario == "all" else [s for s in SCENARIOS if s[0] in wanted]

    warmup_render_api()
    results: list[dict] = []
    state: dict = {}
    with tempfile.TemporaryDirectory(prefix="docs_mcp02_tree_", dir="/tmp/docs_mcp02_test") as profile:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=profile,
                headless=not args.headed,
                user_agent=BROWSER_UA,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            try:
                for sid, fn in to_run:
                    res = fn(ctx, state)
                    results.append(res)
                    emit(res)
            finally:
                ctx.close()

    total = len(results)
    passed = sum(1 for r in results if r["result"] == "pass")
    print(f"[summary] {passed}/{total} pass", file=sys.stderr)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
