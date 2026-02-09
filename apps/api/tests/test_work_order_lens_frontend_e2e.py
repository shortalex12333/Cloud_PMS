#!/usr/bin/env python3
"""
Work Order Lens - Frontend E2E Test Suite
==========================================

Tests the FULL backend → frontend flow:
1. Entity Extraction → Transformation → SQL → Rendering
2. Action Registry → Microactions → RBAC → Signature Flow
3. Frontend Payload Structure → Display Logic

This tests the ACTUAL code, not HTTP APIs, for maximum thoroughness.

Run: PYTHONPATH=/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api python3 test_work_order_lens_frontend_e2e.py
"""
import sys
import os
from pathlib import Path

# Add API directory to Python path
sys.path.insert(0, "/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api")

import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime

# Import backend modules
from pipeline_v1 import Pipeline
from actions.action_registry import get_registry, ActionVariant
from supabase import create_client

# Configuration
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

os.environ["SUPABASE_URL"] = SUPABASE_URL
os.environ["SUPABASE_SERVICE_KEY"] = SUPABASE_KEY

# Test output
ISSUES = []


def log_issue(category: str, severity: str, description: str, details: Dict = None):
    """Log an issue found during testing"""
    issue = {
        "category": category,
        "severity": severity,
        "description": description,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    ISSUES.append(issue)

    # Color code by severity
    colors = {
        "CRITICAL": "\033[91m",  # Red
        "HIGH": "\033[93m",       # Yellow
        "MEDIUM": "\033[94m",     # Blue
        "LOW": "\033[92m"         # Green
    }
    color = colors.get(severity, "\033[97m")
    reset = "\033[0m"

    print(f"{color}[{severity}] {category}: {description}{reset}")
    if details:
        print(f"  Details: {json.dumps(details, indent=2)}")


def print_section(title: str):
    """Print test section header"""
    print(f"\n{'=' * 100}")
    print(f"{title.center(100)}")
    print(f"{'=' * 100}\n")


async def test_1_entity_extraction():
    """Test 1: Entity Extraction for Work Order Lens"""
    print_section("TEST 1: ENTITY EXTRACTION")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(yacht_id=YACHT_ID, supabase_client=supabase)

    test_queries = [
        {
            "query": "main engine starboard oil change",
            "expected": {
                "equipment": ["main engine", "engine", "starboard engine"],
                "action": ["oil change", "change"]
            }
        },
        {
            "query": "watermaker 1 membrane replacement in progress",
            "expected": {
                "equipment": ["watermaker", "watermaker 1"],
                "action": ["replacement"],
                "status": ["in progress", "in_progress"]
            }
        },
        {
            "query": "WO-12345 update status",
            "expected": {
                "work_order_id": ["WO-12345", "12345"]
            }
        }
    ]

    for test_case in test_queries:
        query = test_case["query"]
        expected = test_case["expected"]

        print(f"\nQuery: \"{query}\"")

        try:
            result = await pipeline.search(query)

            if not result.success:
                log_issue(
                    "Entity Extraction",
                    "CRITICAL",
                    f"Pipeline failed for query: {query}",
                    {"error": result.error}
                )
                continue

            # Check entities extracted
            entities = result.extraction.get("entities", [])
            if not entities:
                log_issue(
                    "Entity Extraction",
                    "HIGH",
                    f"Zero entities extracted for: {query}",
                    {"query": query}
                )
                continue

            print(f"  Extracted {len(entities)} entities:")
            for entity in entities:
                print(f"    - {entity.get('type')}: \"{entity.get('value')}\" (conf: {entity.get('confidence', 0):.2f})")

            # Validate expected entities
            for entity_type, expected_values in expected.items():
                extracted = [e for e in entities if e.get("type") == entity_type]

                if not extracted:
                    log_issue(
                        "Entity Extraction",
                        "HIGH",
                        f"Missing expected entity type: {entity_type}",
                        {"query": query, "expected_values": expected_values}
                    )
                else:
                    print(f"  ✅ Found entity type: {entity_type}")

        except Exception as e:
            log_issue(
                "Entity Extraction",
                "CRITICAL",
                f"Exception during extraction: {str(e)}",
                {"query": query, "exception": str(e)}
            )


async def test_2_work_order_transformation():
    """Test 2: Work Order Lens Transformation Logic"""
    print_section("TEST 2: WORK ORDER TRANSFORMATION")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(yacht_id=YACHT_ID, supabase_client=supabase)

    test_queries = [
        "main engine maintenance",
        "generator overhaul",
        "troubleshoot port pump",
        "calibrate hvac chiller"
    ]

    for query in test_queries:
        print(f"\nQuery: \"{query}\"")

        try:
            result = await pipeline.search(query)

            if not result.success:
                log_issue(
                    "Transformation",
                    "HIGH",
                    f"Pipeline failed for: {query}",
                    {"error": result.error}
                )
                continue

            entities = result.extraction.get("entities", [])

            # Check for Work Order specific entity types
            wo_equipment = [e for e in entities if e.get("type") == "WORK_ORDER_EQUIPMENT"]
            wo_title = [e for e in entities if e.get("type") == "WORK_ORDER_TITLE"]

            if not wo_equipment:
                log_issue(
                    "Transformation",
                    "MEDIUM",
                    f"No WORK_ORDER_EQUIPMENT entity created for: {query}",
                    {"entities": [e.get("type") for e in entities]}
                )
            else:
                print(f"  ✅ WORK_ORDER_EQUIPMENT: {wo_equipment[0].get('value')}")

            if not wo_title:
                log_issue(
                    "Transformation",
                    "MEDIUM",
                    f"No WORK_ORDER_TITLE entity created for: {query}",
                    {"entities": [e.get("type") for e in entities]}
                )
            else:
                print(f"  ✅ WORK_ORDER_TITLE: {wo_title[0].get('value')}")

        except Exception as e:
            log_issue(
                "Transformation",
                "CRITICAL",
                f"Exception during transformation: {str(e)}",
                {"query": query}
            )


async def test_3_microactions_structure():
    """Test 3: Microactions Structure and Completeness"""
    print_section("TEST 3: MICROACTIONS STRUCTURE")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(yacht_id=YACHT_ID, supabase_client=supabase)
    query = "main engine port 500-hour service"

    print(f"Query: \"{query}\"")

    try:
        result = await pipeline.search(query)

        if not result.success or not result.results:
            log_issue(
                "Microactions",
                "HIGH",
                "No results returned for microactions test",
                {"query": query}
            )
            return

        work_order = result.results[0]

        # Check microactions field exists
        if "microactions" not in work_order:
            log_issue(
                "Microactions",
                "CRITICAL",
                "No 'microactions' field in result",
                {"work_order_id": work_order.get("id")}
            )
            return

        microactions = work_order["microactions"]

        # Check primary action
        if "primary" not in microactions:
            log_issue(
                "Microactions",
                "CRITICAL",
                "No 'primary' action in microactions",
                {"work_order_id": work_order.get("id")}
            )
        else:
            primary = microactions["primary"]
            print(f"\n  PRIMARY ACTION:")
            print(f"    action_id: {primary.get('action_id')}")
            print(f"    label: {primary.get('label')}")
            print(f"    variant: {primary.get('variant')}")

            # Validate primary is READ
            if primary.get("variant") != "READ":
                log_issue(
                    "Microactions",
                    "HIGH",
                    "Primary action is not READ variant",
                    {"primary": primary}
                )
            else:
                print(f"    ✅ Correct: PRIMARY is READ")

        # Check dropdown actions
        if "dropdown" not in microactions:
            log_issue(
                "Microactions",
                "CRITICAL",
                "No 'dropdown' actions in microactions",
                {"work_order_id": work_order.get("id")}
            )
        else:
            dropdown = microactions["dropdown"]
            print(f"\n  DROPDOWN ACTIONS ({len(dropdown)} total):")

            # Categorize by variant
            read_actions = [a for a in dropdown if a.get("variant") == "READ"]
            mutate_actions = [a for a in dropdown if a.get("variant") == "MUTATE"]
            signed_actions = [a for a in dropdown if a.get("variant") == "SIGNED"]

            print(f"    READ: {len(read_actions)}")
            print(f"    MUTATE: {len(mutate_actions)}")
            print(f"    SIGNED: {len(signed_actions)}")

            # Check MUTATE actions have signature requirements
            for action in mutate_actions:
                if "requires_signature" not in action:
                    log_issue(
                        "Microactions",
                        "HIGH",
                        f"MUTATE action missing 'requires_signature' field",
                        {"action_id": action.get("action_id")}
                    )

            # Check SIGNED actions have role restrictions
            for action in signed_actions:
                if "allowed_roles" not in action:
                    log_issue(
                        "Microactions",
                        "HIGH",
                        f"SIGNED action missing 'allowed_roles' field",
                        {"action_id": action.get("action_id")}
                    )
                else:
                    print(f"      {action.get('action_id')}: roles={action.get('allowed_roles')}")

    except Exception as e:
        log_issue(
            "Microactions",
            "CRITICAL",
            f"Exception during microactions test: {str(e)}",
            {"query": query}
        )


def test_4_action_registry():
    """Test 4: Action Registry Completeness"""
    print_section("TEST 4: ACTION REGISTRY")

    registry = get_registry()

    # Get all Work Order domain actions
    wo_actions = registry.get_actions_for_domain("work_orders")

    print(f"Work Order Domain: {len(wo_actions)} actions registered")

    # Expected Work Order actions (from action_registry.py)
    expected_actions = [
        "view_work_order",
        "create_work_order",
        "update_work_order_status",
        "mark_work_order_complete",
        "add_work_order_note",
        "add_work_order_photo",
        "add_parts_to_work_order",
        "view_work_order_history",
        "view_work_order_checklist",
        "assign_work_order",
        "edit_work_order_details",
        "reassign_work_order",
        "archive_work_order"
    ]

    registered_ids = [a.action_id for a in wo_actions]

    # Check for missing actions
    missing = set(expected_actions) - set(registered_ids)
    if missing:
        log_issue(
            "Action Registry",
            "HIGH",
            f"Missing expected Work Order actions",
            {"missing_actions": list(missing)}
        )
    else:
        print(f"  ✅ All {len(expected_actions)} expected actions present")

    # Validate each action
    print(f"\n  Validating action structures:")
    for action in wo_actions:
        # Check required fields
        if not action.action_id:
            log_issue(
                "Action Registry",
                "CRITICAL",
                "Action missing action_id",
                {"action": str(action)}
            )

        if not action.label:
            log_issue(
                "Action Registry",
                "HIGH",
                f"Action {action.action_id} missing label"
            )

        if not action.variant:
            log_issue(
                "Action Registry",
                "CRITICAL",
                f"Action {action.action_id} missing variant"
            )

        # Check variant-specific requirements
        if action.variant == ActionVariant.MUTATE:
            if not action.mutation:
                log_issue(
                    "Action Registry",
                    "HIGH",
                    f"MUTATE action {action.action_id} missing mutation config"
                )

        if action.ui.primary and action.variant != ActionVariant.READ:
            log_issue(
                "Action Registry",
                "CRITICAL",
                f"Primary action {action.action_id} is not READ variant",
                {"variant": action.variant}
            )

    print(f"  Validated {len(wo_actions)} actions")


async def test_5_frontend_payload_structure():
    """Test 5: Frontend Rendering Payload"""
    print_section("TEST 5: FRONTEND PAYLOAD STRUCTURE")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    pipeline = Pipeline(yacht_id=YACHT_ID, supabase_client=supabase)
    query = "all in progress work orders"

    print(f"Query: \"{query}\"")

    try:
        result = await pipeline.search(query)

        if not result.success:
            log_issue(
                "Frontend Payload",
                "HIGH",
                "Pipeline failed",
                {"error": result.error}
            )
            return

        if not result.results:
            log_issue(
                "Frontend Payload",
                "MEDIUM",
                "No results returned (may be expected)",
                {"query": query}
            )
            return

        print(f"\n  Testing payload for {len(result.results)} results:")

        for i, work_order in enumerate(result.results[:3], 1):  # Test first 3
            print(f"\n  Result #{i}:")

            # Check required display fields
            display_fields = ["id", "title", "status"]
            for field in display_fields:
                if field not in work_order:
                    log_issue(
                        "Frontend Payload",
                        "HIGH",
                        f"Missing required display field: {field}",
                        {"work_order_id": work_order.get("id")}
                    )
                else:
                    print(f"    ✅ {field}: {work_order[field]}")

            # Check microactions for rendering
            if "microactions" not in work_order:
                log_issue(
                    "Frontend Payload",
                    "CRITICAL",
                    "Missing microactions - frontend cannot render buttons",
                    {"work_order_id": work_order.get("id")}
                )
            else:
                ma = work_order["microactions"]
                if "primary" not in ma:
                    log_issue(
                        "Frontend Payload",
                        "HIGH",
                        "Missing primary action - no primary button",
                        {"work_order_id": work_order.get("id")}
                    )

                if "dropdown" not in ma:
                    log_issue(
                        "Frontend Payload",
                        "HIGH",
                        "Missing dropdown actions - no action menu",
                        {"work_order_id": work_order.get("id")}
                    )

        # Check response metadata
        print(f"\n  Response Metadata:")
        if not hasattr(result, "total_count"):
            log_issue(
                "Frontend Payload",
                "MEDIUM",
                "Missing total_count - pagination won't work"
            )
        else:
            print(f"    ✅ total_count: {result.total_count}")

        if not hasattr(result, "extraction"):
            log_issue(
                "Frontend Payload",
                "MEDIUM",
                "Missing extraction metadata - no debug info"
            )
        else:
            print(f"    ✅ extraction: {len(result.extraction.get('entities', []))} entities")

    except Exception as e:
        log_issue(
            "Frontend Payload",
            "CRITICAL",
            f"Exception during payload test: {str(e)}",
            {"query": query}
        )


def test_6_rbac_logic():
    """Test 6: RBAC Logic (Role-Based Access Control)"""
    print_section("TEST 6: RBAC LOGIC")

    registry = get_registry()

    # Test SIGNED actions have role restrictions
    wo_actions = registry.get_actions_for_domain("work_orders")
    signed_actions = [a for a in wo_actions if a.variant == ActionVariant.SIGNED]

    print(f"  Testing {len(signed_actions)} SIGNED actions:")

    for action in signed_actions:
        print(f"\n  Action: {action.action_id}")

        if not hasattr(action, "allowed_roles") or not action.allowed_roles:
            log_issue(
                "RBAC",
                "CRITICAL",
                f"SIGNED action {action.action_id} has no role restrictions",
                {"action_id": action.action_id}
            )
        else:
            print(f"    Allowed roles: {action.allowed_roles}")

            # Check for valid roles
            valid_roles = ["captain", "chief_engineer", "chief_officer", "purser", "manager"]
            invalid = set(action.allowed_roles) - set(valid_roles)
            if invalid:
                log_issue(
                    "RBAC",
                    "HIGH",
                    f"Action {action.action_id} has invalid roles",
                    {"invalid_roles": list(invalid)}
                )

    # Test that crew role is properly restricted
    print(f"\n  Testing crew role restrictions:")
    crew_denied_actions = ["reassign_work_order", "archive_work_order"]

    for action_id in crew_denied_actions:
        action = registry.get_action(action_id)
        if action and hasattr(action, "allowed_roles"):
            if "crew" in action.allowed_roles:
                log_issue(
                    "RBAC",
                    "CRITICAL",
                    f"Action {action_id} incorrectly allows 'crew' role",
                    {"allowed_roles": action.allowed_roles}
                )
            else:
                print(f"    ✅ {action_id}: crew correctly denied")


def generate_issues_report():
    """Generate comprehensive issues report"""
    print_section("ISSUES REPORT")

    if not ISSUES:
        print("  🎉 NO ISSUES FOUND! All tests passed.")
        return

    # Group by severity
    by_severity = {}
    for issue in ISSUES:
        severity = issue["severity"]
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)

    # Print summary
    print(f"Total Issues: {len(ISSUES)}\n")
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if severity in by_severity:
            print(f"  {severity}: {len(by_severity[severity])}")

    # Print details
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if severity not in by_severity:
            continue

        print(f"\n{severity} Issues ({len(by_severity[severity])}):")
        print("=" * 100)

        for issue in by_severity[severity]:
            print(f"\n  Category: {issue['category']}")
            print(f"  Description: {issue['description']}")
            if issue["details"]:
                print(f"  Details: {json.dumps(issue['details'], indent=4)}")

    # Save to file
    report_file = Path(__file__).parent / "test_results" / f"work_order_lens_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w") as f:
        json.dump({
            "test_run": datetime.now().isoformat(),
            "total_issues": len(ISSUES),
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "issues": ISSUES
        }, f, indent=2)

    print(f"\n\n  📄 Full report saved: {report_file}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 100)
    print("WORK ORDER LENS - FRONTEND END-TO-END TEST SUITE")
    print("=" * 100)

    # Run tests
    await test_1_entity_extraction()
    await test_2_work_order_transformation()
    await test_3_microactions_structure()
    test_4_action_registry()
    await test_5_frontend_payload_structure()
    test_6_rbac_logic()

    # Generate report
    generate_issues_report()


if __name__ == "__main__":
    asyncio.run(main())
