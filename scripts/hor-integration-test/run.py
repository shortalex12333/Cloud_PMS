#!/usr/bin/env python3
"""
HoR Integration Test Runner
============================
Tests all 9 MLC 2006 scenarios across 4 roles against the REAL API and REAL DB.

Usage:
  python3 run.py                          # API at localhost:8000
  HOR_TEST_API_BASE=https://... python3 run.py

Output: JSON report to stdout + hor_test_report.json (deleted with this folder when done).
"""
import sys
import os
import json
import time
from datetime import datetime, timezone

# Ensure local imports work regardless of cwd
sys.path.insert(0, os.path.dirname(__file__))

import auth
import teardown

SCENARIOS_RUN = []


def banner(msg: str):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


def section(msg: str):
    print(f"\n--- {msg} ---")


def run_scenario(fn, label: str, *args) -> dict:
    start = time.time()
    try:
        result = fn(*args)
    except Exception as e:
        result = {
            "pass": False,
            "checks": [{"name": "scenario executed without exception",
                        "pass": False, "error": str(e)}],
        }
    elapsed = round((time.time() - start) * 1000)
    result["duration_ms"] = elapsed

    status = "PASS" if result.get("pass") else "FAIL"
    skip   = result.get("skip_reason", "")
    label_out = f"[{status}] {label}"
    if skip:
        label_out += f" (partial: {skip})"
    print(f"  {label_out} — {elapsed}ms")

    for c in result.get("checks", []):
        icon = "✓" if c["pass"] else "✗"
        line = f"    {icon} {c['name']}"
        if not c["pass"]:
            line += f"\n        expected: {c.get('expected','')}"
            line += f"\n        actual:   {c.get('actual','')}"
            if c.get("error"):
                line += f"\n        error:    {c['error']}"
        print(line)

    return result


def main():
    banner("HoR MLC 2006 Integration Test Suite")
    print(f"API: {os.environ.get('HOR_TEST_API_BASE','http://localhost:8000')}")
    print(f"Run: {datetime.now(timezone.utc).isoformat()}")

    # ------------------------------------------------------------------
    # Auth — real JWTs
    # ------------------------------------------------------------------
    section("Authenticating test users")
    tokens = auth.get_all_tokens()

    missing_roles = [r for r, t in tokens.items() if t is None]
    if missing_roles:
        print(f"  WARNING: Missing tokens for: {missing_roles}")
        print("  Affected scenarios will be marked FAIL or SKIP.")

    # ------------------------------------------------------------------
    # Import scenarios
    # ------------------------------------------------------------------
    from scenarios import (
        s1_crew_submit,
        s2_hod_submit,
        s3_captain_submit,
        s4_hod_countersign,
        s5_captain_sign_all,
        s6_fleet_inspect,
        s7_violation_notification,
        s8_crew_undo,
        s9_correction_flow,
    )

    # ------------------------------------------------------------------
    # Run in dependency order — each result fed to dependents
    # ------------------------------------------------------------------
    section("Running scenarios")

    s1 = run_scenario(s1_crew_submit.run,    "S1 — Crew submits own time",              tokens)
    s2 = run_scenario(s2_hod_submit.run,     "S2 — HOD submits own time",               tokens)
    s3 = run_scenario(s3_captain_submit.run, "S3 — Captain submits own time",           tokens)

    # S7 depends on S1 (violation record)
    s7 = run_scenario(s7_violation_notification.run, "S7 — Violation → HOD notification", tokens, s1)

    # S9 depends on S1 (original record — must run BEFORE S8 which clears it)
    s9 = run_scenario(s9_correction_flow.run,"S9 — Correction flow (both preserved)",   tokens, s1)

    # S8 depends on S1 (record to undo) — runs AFTER S9 since S8 clears the record
    s8 = run_scenario(s8_crew_undo.run,      "S8 — Crew undo (original preserved)",     tokens, s1)

    # S4 depends on S1 (crew user ID for signoff)
    s4 = run_scenario(s4_hod_countersign.run,"S4 — HOD counter-signs crew (L2)",        tokens, s1)

    # S5 depends on S4 (signoff_id)
    if s4.get("pass") or s4.get("_signoff_id"):
        s5 = run_scenario(s5_captain_sign_all.run,"S5 — Captain signs all depts (L2)",  tokens, s4)
    else:
        s5 = {"id": "S5", "name": "Captain signs all depts", "pass": False,
              "skip_reason": "S4 failed — no signoff_id available",
              "checks": [{"name": "S4 prerequisite passed", "pass": False}],
              "duration_ms": 0}
        print("  [SKIP] S5 — Captain signs all depts (S4 failed)")

    # S6 depends on S5 (finalized sign chain)
    s6 = run_scenario(s6_fleet_inspect.run,  "S6 — Fleet manager inspects",            tokens)

    # S9 was already run above (before S8)

    all_results = [s1, s2, s3, s4, s5, s6, s7, s8, s9]

    # ------------------------------------------------------------------
    # Teardown — always runs
    # ------------------------------------------------------------------
    section("Teardown — deleting test data")
    teardown_result = teardown.run()

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    total   = len(all_results)
    passed  = sum(1 for r in all_results if r.get("pass"))
    failed  = total - passed
    all_checks = [c for r in all_results for c in r.get("checks", [])]
    total_checks  = len(all_checks)
    passed_checks = sum(1 for c in all_checks if c["pass"])

    report = {
        "run_at":       datetime.now(timezone.utc).isoformat(),
        "api_base":     os.environ.get("HOR_TEST_API_BASE", "http://localhost:8000"),
        "yacht_id":     "85fe1119-b04c-41ac-80f1-829d23322598",
        "scenarios": {
            "total":  total,
            "passed": passed,
            "failed": failed,
        },
        "checks": {
            "total":  total_checks,
            "passed": passed_checks,
            "failed": total_checks - passed_checks,
        },
        "results":   all_results,
        "teardown":  teardown_result,
    }

    banner(f"RESULT: {passed}/{total} scenarios passed · {passed_checks}/{total_checks} checks passed")

    if failed:
        print("\nFailed scenarios:")
        for r in all_results:
            if not r.get("pass"):
                print(f"  - {r.get('id')} {r.get('name')}")
                for c in r.get("checks", []):
                    if not c["pass"]:
                        print(f"      ✗ {c['name']}: {c.get('error','')}")

    # Write report file (lives in this disposable directory)
    report_path = os.path.join(os.path.dirname(__file__), "hor_test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport written to: {report_path}")
    print("When done: rm -rf scripts/hor-integration-test/")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
