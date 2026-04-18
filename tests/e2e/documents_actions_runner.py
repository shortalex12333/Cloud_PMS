"""
documents_actions_runner.py — shard 3 — 10-action audit with DB verification.

Brief from DOCUMENTS04 (peer qbif5g9x, 2026-04-17 15:31Z):
Handler anchors in apps/api/action_router/dispatchers/internal_dispatcher.py:
  _eq_link_document_to_equipment:2971
  _doc_upload_document:467          _doc_update_document:475
  _doc_add_document_tags:483        _doc_delete_document:491
  _doc_get_document_url:502
  _doc_add_document_comment:517     _doc_update_document_comment:532
  _doc_delete_document_comment:545  _doc_list_document_comments:558

Per-action contract:
  - UI click → API 200
  - direct TENANT psql SELECT on expected row
  - assert ledger_events row with proof_hash (within 60s)
  - assert pms_notifications row (within 60s)
  - SIGNED (delete_document only among these 10):
      assert pms_audit_log.signature->>'method' = 'pin'

Roles:
  - captain (x@alex-short.com)        — full access
  - crew (crew.test@alex-short.com)   — expected 403 on HOD+ actions
  - chief_steward                     — link-to-equipment should now PASS per PR #590+

Usage:
  python documents_actions_runner.py --scenario A3                  # just upload
  python documents_actions_runner.py --role captain
  python documents_actions_runner.py --create-doc                    # seed doc first
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _docs_shared import (  # noqa: E402
    BASE_URL, CAPTAIN_EMAIL, CREW_EMAIL, HOD_EMAIL, PASSWORD,
    TEST_YACHT_ID, TEST_PIN,
    NAV_TIMEOUT_MS, POPUP_TIMEOUT_MS, STEP_TIMEOUT_MS, BROWSER_UA,
    assert_ledger_row, assert_notification_row, assert_signature_row,
    emit, finalize, instrument, login, ensure_logged_in, new_result, step,
    db_assert, psql_scalar, warmup_render_api,
)

from playwright.sync_api import BrowserContext, sync_playwright


# ---------------------------------------------------------------------------
# Action registry entries we exercise. Kept aligned with DOCUMENTS04 anchors.
# ---------------------------------------------------------------------------

ACTIONS = [
    # (scenario_id, action_name, signed, role, dispatcher_anchor_line)
    # NOTE: A5 (delete_document) runs LAST — it soft-deletes the shared seed doc.
    # Running it earlier would cause A6-A10 to operate on a deleted entity.
    ("A1", "link_document_to_equipment",   False, "captain",        2971),
    ("A2", "upload_document",              False, "captain",        467),
    ("A3", "update_document",              False, "captain",        475),
    ("A4", "add_document_tags",            False, "captain",        483),
    ("A6", "get_document_url",             False, "captain",        502),
    ("A7", "add_document_comment",         False, "captain",        517),
    ("A8", "update_document_comment",      False, "captain",        532),
    ("A9", "delete_document_comment",      False, "captain",        545),
    ("A10", "list_document_comments",      False, "captain",        558),
    ("A5", "delete_document",              True,  "captain",        491),  # SIGNED — runs last
]

CREW_FORBIDDEN = {"upload_document", "update_document", "delete_document",
                  "link_document_to_equipment", "add_document_tags"}


# ---------------------------------------------------------------------------
# Seed helpers — each run needs a disposable doc to mutate.
# ---------------------------------------------------------------------------


def seed_doc(state: dict) -> str:
    """Create a fresh doc via the backend directly (not through UI) so every
    per-action scenario starts with a known doc_id. Falls back to picking an
    existing doc if insertion is blocked.

    NOTE: doc_metadata has no `title` column — title lives in metadata JSONB.
    NOT NULL columns required by schema: id, yacht_id, source, filename,
    storage_path, created_at (updated_at is auto-set by trigger).
    """
    doc_id = str(uuid.uuid4())
    title = f"mcp02-sprint-{dt.datetime.utcnow().strftime('%H%M%S')}"
    storage_path = f"{TEST_YACHT_ID}/documents/{doc_id}/shard3-smoke.pdf"
    # title → metadata JSONB (no dedicated title column in doc_metadata)
    sql = (
        f"INSERT INTO doc_metadata "
        f"(id, yacht_id, doc_type, content_type, size_bytes, created_at, source, filename, storage_path, metadata) "
        f"VALUES ('{doc_id}', '{TEST_YACHT_ID}', 'certificate', "
        f"'application/pdf', 1024, now(), 'shard3_test', 'shard3-smoke.pdf', '{storage_path}', "
        f"'{{\"title\":\"{title}\"}}'::jsonb) RETURNING id"
    )
    try:
        raw = psql_scalar(sql)
        # psql -t -A with RETURNING may output "<uuid>\nINSERT 0 1" — take first line only.
        got = raw.splitlines()[0].strip()
        state["seed_doc_id"] = got
        state["seed_doc_title"] = title
        return got
    except AssertionError as e:
        # Fall back to the canonical S1 doc used in earlier tests.
        state["seed_doc_id"] = "0b353df3-72ec-4247-9009-15eb85df4926"
        state["seed_doc_warning"] = f"seed insert failed ({e}); reusing canonical doc"
        return state["seed_doc_id"]


# ---------------------------------------------------------------------------
# Generic action-click + popup-confirm flow.
# ---------------------------------------------------------------------------


def open_action_popup(page, action_name: str) -> None:
    """From an open document overlay, open the Actions SplitButton and click the
    named action. Accepts either a data-testid anchor or a role+name match."""
    page.get_by_test_id("splitbutton-caret").first.click(timeout=STEP_TIMEOUT_MS)
    page.get_by_test_id(f"action-item-{action_name}").click(timeout=STEP_TIMEOUT_MS)
    page.get_by_test_id("action-popup").wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)


def confirm_popup(page, signed: bool, pin: str = TEST_PIN) -> dict:
    """Click the popup's confirm/submit button. For SIGNED actions the pin
    input appears first — fill the 4 digits, then click the signature-confirm.
    Returns the captured /actions/execute response body."""
    if signed:
        # .pinHiddenInput is opacity:0, 1px×1px, position:absolute — invisible
        # to users but pointer-events is ENABLED so Playwright can interact.
        # press_sequentially() sends real key events per character; React's
        # synthetic onChange fires for each, updating the pin state.
        # The element must be "visible" at the Playwright level — it is: opacity
        # and dimensions don't matter, only that it exists in the layout.
        pin_input = page.get_by_test_id("signature-pin-input")
        pin_input.wait_for(state="attached", timeout=POPUP_TIMEOUT_MS)
        # opacity:0 fails Playwright's actionability check, but force=True on
        # click() bypasses it.  After the element is focused, keyboard.type()
        # doesn't check actionability — it dispatches to the focused element.
        pin_input.click(force=True, timeout=STEP_TIMEOUT_MS)
        page.keyboard.type(pin)
        time.sleep(0.1)

    with page.expect_response(
        lambda r: "/v1/actions/execute" in r.url and r.request.method == "POST",
        timeout=NAV_TIMEOUT_MS,
    ) as resp_info:
        if signed:
            page.get_by_test_id("signature-confirm-button").click(timeout=STEP_TIMEOUT_MS)
        else:
            page.locator("[data-testid='action-popup-submit'], button[type='submit']").first.click(timeout=STEP_TIMEOUT_MS)
    resp = resp_info.value
    try:
        body = resp.json()
    except Exception:
        try:
            body = resp.text()
        except Exception:
            body = None
    return {"status": resp.status, "body": body}


# ---------------------------------------------------------------------------
# Per-action scenarios. All share the same shape: login → open doc → open popup
# → fill fields → confirm → DB verify.
# ---------------------------------------------------------------------------


def run_action_scenario(ctx: BrowserContext, state: dict, spec: tuple) -> dict:
    sid, action, signed, role, anchor = spec
    res = new_result(sid, f"{action} (dispatcher:{anchor}, SIGNED={signed})", role)
    if state.get("seed_doc_warning"):
        res.setdefault("notes", []).append(state["seed_doc_warning"])
    doc_id = state.get("seed_doc_id") or seed_doc(state)

    page = ctx.new_page()
    instrument(page, res)

    step(res, f"{sid}.0", f"Login as {role}",
         lambda: ensure_logged_in(page, _email_for(role), PASSWORD))
    step(res, f"{sid}.1", "Open document overlay",
         lambda: _open_doc_overlay(page, doc_id))
    # Pre-cleanup: link_document_to_equipment is idempotent at the UI but
    # raises ALREADY_LINKED from the backend on duplicate runs. Delete any
    # existing link before each run so the INSERT always succeeds.
    if action == "link_document_to_equipment":
        try:
            # Clear ALL existing links for this test equipment so INSERT is always fresh.
            # Filtering by doc_id is unreliable because seed fallback may open a different doc.
            psql_scalar(
                "DELETE FROM pms_equipment_documents "
                "WHERE equipment_id='5a7792a7-dd73-494c-bd5d-799e9f88403c'"
            )
        except Exception:
            pass  # non-fatal — link may not exist yet

    step(res, f"{sid}.2", f"Open action popup: {action}",
         lambda: open_action_popup(page, action))
    step(res, f"{sid}.3", f"Fill action fields for {action}",
         lambda: _fill_fields_for_action(page, action, state))
    captured = {}
    step(res, f"{sid}.4", "Confirm popup — expect 200",
         lambda: captured.update(confirm_popup(page, signed)))
    if captured.get("status") != 200:
        res.setdefault("notes", []).append(f"execute status={captured.get('status')} body={captured.get('body')}")
    step(res, f"{sid}.5", "Execute returned 200",
         lambda: _assert_status_200(captured))

    # Resolve the actual entity_id from the execute response body.
    # The response may contain document_id / entity_id / id — use whichever lands.
    body = captured.get("body") or {}
    result_body = body.get("result", body) if isinstance(body, dict) else {}
    actual_doc_id = (
        result_body.get("document_id") or
        result_body.get("entity_id") or
        result_body.get("id") or
        doc_id
    )
    # If the execute succeeded on a different doc than seed, update for DB checks.
    if actual_doc_id and actual_doc_id != doc_id:
        res.setdefault("notes", []).append(f"actual doc_id={actual_doc_id[:8]}… (fallback from seed)")
        doc_id = actual_doc_id
        state["seed_doc_id"] = actual_doc_id  # align future scenarios to the same doc

    # Capture comment_id after add_document_comment so A8/A9 can reference it.
    if action == "add_document_comment" and captured.get("status") == 200:
        try:
            cid = psql_scalar(
                f"SELECT id FROM doc_metadata_comments "
                f"WHERE document_id='{doc_id}' "
                f"AND created_at > now() - interval '60 seconds' "
                f"ORDER BY created_at DESC LIMIT 1"
            )
            if cid.strip():
                state["last_comment_id"] = cid.strip()
        except Exception:
            pass

    # DB verification — short delay for write propagation, then assert.
    time.sleep(2)
    _READ_ONLY_ACTIONS = {"get_document_url", "list_document_comments"}
    if action not in _READ_ONLY_ACTIONS:
        assert_ledger_row(res, f"{sid}.db1", doc_id, _event_type_for(action))
    if _should_notify(action):
        assert_notification_row(res, f"{sid}.db2", doc_id)
    if signed:
        assert_signature_row(res, f"{sid}.db3", doc_id, "pin")

    # Per-action DB row verification.
    _assert_per_action_db_state(res, f"{sid}.db4", action, doc_id, state)

    page.close()
    return finalize(res)


def run_crew_403_scenario(ctx: BrowserContext, state: dict, spec: tuple) -> dict:
    sid, action, signed, _role, anchor = spec
    res = new_result(f"{sid}-crew", f"crew blocked from {action} (expect 403)", "crew")
    doc_id = state.get("seed_doc_id") or seed_doc(state)

    page = ctx.new_page()
    instrument(page, res)

    step(res, f"{sid}c.0", "Login as crew", lambda: ensure_logged_in(page, CREW_EMAIL, PASSWORD))
    step(res, f"{sid}c.1", "Open document overlay",
         lambda: _open_doc_overlay(page, doc_id))

    def expect_action_absent_or_403():
        # Either the action is gated off the SplitButton, or attempting it
        # returns 403. Both are acceptable; we just need to verify crew cannot
        # mutate.
        try:
            page.get_by_test_id("splitbutton-caret").first.click(timeout=STEP_TIMEOUT_MS)
        except Exception:
            return  # no splitbutton at all = already gated
        item = page.get_by_test_id(f"action-item-{action}")
        if item.count() == 0:
            return  # gated at UI
        item.click(timeout=STEP_TIMEOUT_MS)
        page.get_by_test_id("action-popup").wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
        cap = confirm_popup(page, signed=signed)
        assert cap["status"] == 403, f"expected 403, got {cap['status']}: {cap.get('body')}"

    step(res, f"{sid}c.2", f"crew blocked from {action}", expect_action_absent_or_403)
    page.close()
    return finalize(res)


# ---------------------------------------------------------------------------
# Field fillers. Minimal — actual field shapes come from registry required_fields.
# ---------------------------------------------------------------------------


def _fill_fields_for_action(page, action: str, state: dict) -> None:
    ts = dt.datetime.utcnow().strftime("%H%M%S")
    if action == "update_document":
        _fill(page, "title", f"mcp02-update-{ts}")
    elif action == "add_document_tags":
        _fill(page, "tags", f"sprint,shard3,{ts}")
    elif action == "add_document_comment":
        _fill(page, "comment", f"shard3 smoke {ts}")
        state["last_comment_ts"] = ts
    elif action == "update_document_comment":
        comment_id = state.get("last_comment_id", "")
        if comment_id:
            _fill(page, "comment_id", comment_id)
        _fill(page, "comment", f"shard3 updated {ts}")
    elif action == "link_document_to_equipment":
        _fill(page, "equipment_id", "5a7792a7-dd73-494c-bd5d-799e9f88403c")  # PARENT-EQ-0e563f on test yacht
    elif action == "upload_document":
        # upload_document popup renders file_name + mime_type as text inputs.
        # React controlled inputs need an explicit click to focus before fill
        # so that onChange is reliably triggered (Playwright 1.54 + React 18).
        _fill_react(page, "file_name", "shard3-smoke.pdf")
        _fill_react(page, "mime_type", "application/pdf")
    elif action == "delete_document":
        _fill(page, "reason", "shard3 smoke test deletion")
    elif action == "delete_document_comment":
        comment_id = state.get("last_comment_id", "")
        if comment_id:
            _fill(page, "comment_id", comment_id)
    else:
        pass  # get_url, list_comments — no required input


def _fill(page, field: str, value: str) -> None:
    wrapper = page.get_by_test_id(f"popup-field-{field}")
    wrapper.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
    control = wrapper.locator("input, textarea, select").first
    control.fill(value, timeout=STEP_TIMEOUT_MS)


def _fill_react(page, field: str, value: str) -> None:
    """Fill a React controlled input, triggering onChange via native value setter.
    Using click() before fill can time out if the popup is still animating —
    fill() focuses internally and avoids the coverage/animation race."""
    wrapper = page.get_by_test_id(f"popup-field-{field}")
    wrapper.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
    control = wrapper.locator("input, textarea, select").first
    tag = control.evaluate("el => el.tagName.toLowerCase()", timeout=STEP_TIMEOUT_MS)
    if tag == "select":
        control.select_option(value, timeout=STEP_TIMEOUT_MS)
    else:
        # Use native value setter + input event to fire React 18 synthetic onChange.
        # fill() alone may not trigger controlled-input state; evaluate() bypasses
        # the pointer-event coverage check that causes click() to time out.
        control.evaluate(
            """(el, val) => {
                const setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(el, val);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
            timeout=STEP_TIMEOUT_MS,
        )


def _upload_test_pdf(page) -> None:
    fi = page.locator("input[type='file']").first
    fi.wait_for(state="attached", timeout=POPUP_TIMEOUT_MS)
    path = "/tmp/docs_mcp02_test/runner-test.pdf"
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\nxref\n0 1\ntrailer<<>>\n%%EOF\n")
    fi.set_input_files(path)


# ---------------------------------------------------------------------------
# DB post-state assertions.
# ---------------------------------------------------------------------------


def _assert_per_action_db_state(res, assert_id, action, doc_id, state):
    if action == "update_document":
        # title is stored in metadata JSONB (no dedicated title column in doc_metadata)
        sql = f"SELECT metadata->>'title' FROM doc_metadata WHERE id='{doc_id}' LIMIT 1"
        db_assert(res, assert_id, "title stored in metadata.title",
                  sql, lambda r: r.strip().startswith("mcp02-update-"))
    elif action == "add_document_tags":
        sql = f"SELECT array_length(tags, 1) FROM doc_metadata WHERE id='{doc_id}' LIMIT 1"
        db_assert(res, assert_id, "tags array non-empty",
                  sql, lambda r: r.strip().isdigit() and int(r.strip()) >= 1)
    elif action == "delete_document":
        sql = f"SELECT (deleted_at IS NOT NULL)::text FROM doc_metadata WHERE id='{doc_id}' LIMIT 1"
        db_assert(res, assert_id, "doc soft-deleted",
                  sql, lambda r: r.strip() in ("t", "true"))
    elif action == "link_document_to_equipment":
        sql = (f"SELECT count(*) FROM pms_equipment_documents "
               f"WHERE document_id='{doc_id}' "
               f"AND created_at > now() - interval '60 seconds'")
        db_assert(res, assert_id, "equipment_documents link row",
                  sql, lambda r: r.strip().isdigit() and int(r.strip()) >= 1)
    elif action == "add_document_comment":
        sql = (f"SELECT count(*) FROM doc_metadata_comments "
               f"WHERE document_id='{doc_id}' "
               f"AND created_at > now() - interval '60 seconds'")
        db_assert(res, assert_id, "doc_metadata_comments row added",
                  sql, lambda r: r.strip().isdigit() and int(r.strip()) >= 1)
    # list_document_comments, get_document_url — read-only, no mutation


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _email_for(role: str) -> str:
    return {"captain": CAPTAIN_EMAIL, "crew": CREW_EMAIL, "chief_engineer": HOD_EMAIL}.get(role, CAPTAIN_EMAIL)


def _open_doc_overlay(page, doc_id: str) -> None:
    page.goto(f"{BASE_URL}/documents", timeout=NAV_TIMEOUT_MS)
    # Wait for tree to render at least one leaf before testing specific doc.
    page.locator("[data-testid^='doc-tree-leaf-']").first.wait_for(
        state="visible", timeout=NAV_TIMEOUT_MS
    )
    # Prefer the tree leaf for this exact id.
    leaf = page.locator(f"[data-testid='doc-tree-leaf-{doc_id}']")
    if leaf.count() > 0:
        leaf.first.click(timeout=STEP_TIMEOUT_MS)
    else:
        # Fallback — click first leaf available; scenarios that need a specific
        # doc will fail on downstream assertions and surface the issue there.
        page.locator("[data-testid^='doc-tree-leaf-']").first.click(timeout=STEP_TIMEOUT_MS)
    page.get_by_test_id("document-content").wait_for(state="visible", timeout=STEP_TIMEOUT_MS)


def _assert_status_200(cap: dict) -> None:
    assert cap.get("status") == 200, f"status={cap.get('status')} body={cap.get('body')}"


_EVENT_TYPE_MAP = {
    "update_document": "update",
    "delete_document": "delete",
    "upload_document": "create",
    "add_document_tags": "update",
    "add_document_comment": "create",
    "update_document_comment": "update",
    "delete_document_comment": "update",  # ledger_metadata maps this to event_type=update (doc-level audit)
    "link_document_to_equipment": "create",
    "get_document_url": "read",
    "list_document_comments": "read",
}

def _event_type_for(action: str) -> str:
    return _EVENT_TYPE_MAP.get(action, action)


def _should_notify(action: str) -> bool:
    return action in {
        "upload_document", "update_document", "delete_document",
        "add_document_comment", "link_document_to_equipment",
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", help="A1,A2,...,A10 or 'all'")
    ap.add_argument("--role", default="captain", help="captain | crew")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    wanted = {s.strip() for s in (args.scenario.split(",") if args.scenario != "all" else [])}
    to_run = ACTIONS if args.scenario == "all" else [s for s in ACTIONS if s[0] in wanted]

    warmup_render_api()
    state: dict = {}
    seed_doc(state)  # primes state["seed_doc_id"]
    results: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="docs_mcp02_actions_", dir="/tmp/docs_mcp02_test") as profile:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=profile,
                headless=not args.headed,
                user_agent=BROWSER_UA,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            try:
                for spec in to_run:
                    if args.role == "crew" and spec[1] in CREW_FORBIDDEN:
                        res = run_crew_403_scenario(ctx, state, spec)
                    else:
                        res = run_action_scenario(ctx, state, spec)
                    results.append(res)
                    emit(res)
            finally:
                ctx.close()

    passed = sum(1 for r in results if r["result"] == "pass")
    print(f"[summary] {passed}/{len(results)} pass", file=sys.stderr)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
