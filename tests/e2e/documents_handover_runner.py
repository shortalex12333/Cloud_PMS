"""
documents_handover_runner.py — shard 4 — Add-to-Handover prefill + submit.

Brief from DOCUMENTS04 (peer qbif5g9x, 2026-04-17 15:31Z):
Backend changes:
  apps/api/action_router/entity_prefill.py
    gets a (document, add_document_to_handover) map entry.
  apps/api/action_router/registry.py
    widens required_fields with section + summary (user-editable).
Frontend:
  apps/web/src/lib/microactions/handlers/handover.ts:348-374
    accepts entity_id, title, doc_type, source_doc_id, link.

Scenarios:
  H1 Login HOD, open doc overlay, Actions → Add to Handover
  H2 Popup opens with 5 fields: entity_id, title, doc_type, source_doc_id, link
     → assert 3 readonly (entity_id, source_doc_id, link) and 2 editable (section, summary)
  H3 User edits section + summary
  H4 Submit → /v1/actions/execute returns 200
  H5 DB verify: handover_items row with source_doc_id = seed_doc, section + summary set
  H6 Handover draft view shows the newly added item

Usage:
  python documents_handover_runner.py --scenario H2 --headed
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _docs_shared import (  # noqa: E402
    BASE_URL, HOD_EMAIL, PASSWORD,
    NAV_TIMEOUT_MS, POPUP_TIMEOUT_MS, STEP_TIMEOUT_MS, BROWSER_UA,
    db_assert, emit, finalize, instrument, login, ensure_logged_in, new_result, step,
    psql_scalar, warmup_render_api,
)

from playwright.sync_api import BrowserContext, sync_playwright


# Canonical seed — S1 doc that already exists in TENANT (verified 2026-04-17).
SEED_DOC_ID = "0b353df3-72ec-4247-9009-15eb85df4926"

# 5 prefill fields per handover.ts:348-374.
EXPECTED_PREFILL_FIELDS = ["entity_id", "title", "doc_type", "source_doc_id", "link"]
READONLY_FIELDS = {"entity_id", "source_doc_id", "link"}
EDITABLE_FIELDS = {"section", "summary"}


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def h1_open_popup(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("H1", "HOD opens Add-to-Handover popup on doc overlay", "chief_engineer")
    page = ctx.new_page()
    instrument(page, res)
    state["page"] = page
    state["run_ts"] = dt.datetime.utcnow().strftime("%H%M%S")

    step(res, "H1.0", "Login as HOD", lambda: ensure_logged_in(page, HOD_EMAIL, PASSWORD))
    step(res, "H1.1", "Navigate to /documents",
         lambda: page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS))
    step(res, "H1.2", "Open seed doc overlay",
         lambda: _open_seed_doc(page))
    step(res, "H1.3", "Click Actions caret",
         lambda: page.get_by_test_id("splitbutton-caret").first.click(timeout=STEP_TIMEOUT_MS))
    step(res, "H1.4", "Click 'Add to Handover' item",
         lambda: page.evaluate(
             "() => document.querySelector('[data-testid=\"action-item-add_document_to_handover\"]').click()"
         ))
    step(res, "H1.5", "Popup visible",
         lambda: page.get_by_test_id("action-popup").wait_for(state="visible", timeout=POPUP_TIMEOUT_MS))
    return finalize(res)


def h2_verify_prefill(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("H2", "5 fields prefilled, 2 editable", "chief_engineer")
    page = state.get("page")
    if not page:
        res["result"] = "skipped"
        res["steps"].append({"id": "H2.0", "desc": "prereq H1 missing", "pass": False, "error": "no page"})
        return finalize(res)

    # doc_type may be null on older docs — only assert non-empty for stable fields
    MUST_HAVE_VALUE_FIELDS = {"entity_id", "title", "source_doc_id"}

    def check_fields():
        for field in EXPECTED_PREFILL_FIELDS:
            wrapper = page.get_by_test_id(f"popup-field-{field}")
            assert wrapper.count() == 1, f"popup-field-{field} not present"
            if field in MUST_HAVE_VALUE_FIELDS:
                value = wrapper.locator("input, textarea").first.input_value()
                assert value, f"field {field} has empty prefill"
        for field in EDITABLE_FIELDS:
            wrapper = page.get_by_test_id(f"popup-field-{field}")
            assert wrapper.count() == 1, f"editable field {field} missing"
        # entity_id should be readonly / disabled
        for field in READONLY_FIELDS:
            wrapper = page.get_by_test_id(f"popup-field-{field}")
            control = wrapper.locator("input, textarea").first
            readonly = control.get_attribute("readonly")
            disabled = control.get_attribute("disabled")
            assert readonly is not None or disabled is not None, (
                f"field {field} should be readonly/disabled but isn't"
            )
    step(res, "H2.0", "All 5 prefill fields + section + summary present, readonly enforced", check_fields)
    return finalize(res)


def h3_edit_and_submit(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("H3", "Edit section+summary, submit → 200", "chief_engineer")
    page = state.get("page")
    if not page:
        res["result"] = "skipped"
        res["steps"].append({"id": "H3.0", "desc": "prereq missing", "pass": False, "error": "no page"})
        return finalize(res)

    ts = state["run_ts"]
    section_value = "Engineering"  # must match a valid select option
    summary_value = f"shard4 smoke summary {ts}"
    state["section_value"] = section_value
    state["summary_value"] = summary_value

    def fill_and_submit():
        # section renders as <select> — use select_option, not fill
        sec_select = page.get_by_test_id("popup-field-section").locator("select").first
        sec_select.select_option(section_value, timeout=STEP_TIMEOUT_MS)
        summ = page.get_by_test_id("popup-field-summary").locator("input, textarea").first
        summ.fill(summary_value, timeout=STEP_TIMEOUT_MS)
        with page.expect_response(
            lambda r: "/v1/actions/execute" in r.url and r.request.method == "POST",
            timeout=NAV_TIMEOUT_MS,
        ) as ri:
            page.locator("[data-testid='action-popup-submit'], button[type='submit']").first.click(timeout=STEP_TIMEOUT_MS)
        resp = ri.value
        assert resp.status == 200, f"execute {resp.status}: {resp.text()[:200]}"
        state["execute_body"] = resp.json()
    step(res, "H3.0", "Fill section + summary, submit, expect 200", fill_and_submit)
    return finalize(res)


def h4_db_handover_row(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("H4", "handover_items row present with source_doc_id + section + summary", "static")
    if "section_value" not in state:
        res["result"] = "skipped"
        res["steps"].append({"id": "H4.0", "desc": "prereq H3 missing", "pass": False, "error": "no submit"})
        return finalize(res)

    section_value = state["section_value"]
    # Use the actual entity_id from the H3 execute response — avoids hardcoded SEED_DOC_ID
    # mismatch when the fallback doc is opened instead of the seed.
    execute_body = state.get("execute_body", {})
    actual_entity_id = execute_body.get("entity_id") or SEED_DOC_ID
    time.sleep(2)  # write propagation

    # 1. row exists
    sql_count = (
        f"SELECT count(*) FROM handover_items "
        f"WHERE entity_id='{actual_entity_id}' "
        f"AND section=$${section_value}$$ "
        f"AND created_at > now() - interval '300 seconds'"
    )
    db_assert(res, "H4.1", "handover_items row with entity_id + section",
              sql_count, lambda r: r.strip().isdigit() and int(r.strip()) >= 1)

    # 2. summary set
    summary_value = state["summary_value"]
    sql_summary = (
        f"SELECT summary FROM handover_items "
        f"WHERE entity_id='{actual_entity_id}' "
        f"AND section=$${section_value}$$ "
        f"ORDER BY created_at DESC LIMIT 1"
    )
    db_assert(res, "H4.2", "handover_items.summary matches submission",
              sql_summary, lambda r: summary_value in r)

    return finalize(res)


def h5_draft_visible(ctx: BrowserContext, state: dict) -> dict:
    res = new_result("H5", "Handover draft UI shows new item", "chief_engineer")
    page = state.get("page") or ctx.new_page()
    instrument(page, res)

    summary_value = state.get("summary_value")
    if not summary_value:
        res["result"] = "skipped"
        res["steps"].append({"id": "H5.0", "desc": "prereq missing", "pass": False, "error": "no summary"})
        return finalize(res)

    step(res, "H5.0", "Navigate to /handover-export",
         lambda: page.goto(f"{BASE_URL}/handover-export", timeout=NAV_TIMEOUT_MS))
    step(res, "H5.1", "Click Draft Items tab",
         lambda: page.get_by_test_id("handover-tab-draft").click(timeout=STEP_TIMEOUT_MS))
    step(res, "H5.2", f"Draft panel contains summary '{summary_value[:20]}...'",
         lambda: page.get_by_text(summary_value, exact=False).first.wait_for(state="visible", timeout=NAV_TIMEOUT_MS))
    return finalize(res)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_seed_doc(page) -> None:
    leaf = page.locator(f"[data-testid='doc-tree-leaf-{SEED_DOC_ID}']")
    if leaf.count() > 0:
        leaf.first.click(timeout=STEP_TIMEOUT_MS)
    else:
        page.locator("[data-testid^='doc-tree-leaf-']").first.click(timeout=STEP_TIMEOUT_MS)
    page.get_by_test_id("document-content").wait_for(state="visible", timeout=STEP_TIMEOUT_MS)


SCENARIOS = [
    ("H1", h1_open_popup),
    ("H2", h2_verify_prefill),
    ("H3", h3_edit_and_submit),
    ("H4", h4_db_handover_row),
    ("H5", h5_draft_visible),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    wanted = {s.strip() for s in (args.scenario.split(",") if args.scenario != "all" else [])}
    to_run = SCENARIOS if args.scenario == "all" else [s for s in SCENARIOS if s[0] in wanted]

    warmup_render_api()
    results: list[dict] = []
    state: dict = {}
    with tempfile.TemporaryDirectory(prefix="docs_mcp02_handover_", dir="/tmp/docs_mcp02_test") as profile:
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

    passed = sum(1 for r in results if r["result"] == "pass")
    print(f"[summary] {passed}/{len(results)} pass", file=sys.stderr)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
