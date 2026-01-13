#!/usr/bin/env python3
"""
G0 Compliance Checker
=====================

Automated check for mandatory security guards in mutation handlers.

This script validates that all *_mutation_handlers.py files implement
the required G0 (mandatory blocker) guard rails.

Usage:
    python scripts/check_g0_compliance.py

Exit codes:
    0 - All checks passed
    1 - G0 violations found (fails CI)
    2 - Script error

G0 GUARDS CHECKED:
- G0.1: Yacht isolation (A2)
- G0.2: Authentication gate (A1)
- G0.3: Role-based access (A3)
- G0.6: Audit trail (S3)

Note: This is a BASIC check using regex patterns. It does not guarantee
correctness, only presence. Code review is still required.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json


# G0 guard patterns to detect in code
G0_PATTERNS = {
    "yacht_isolation": {
        "description": "G0.1: Yacht Isolation - Validates user's yacht_id matches request",
        "patterns": [
            r'user\["yacht_id"\]\s*!=\s*yacht_id',  # Inequality check
            r'yacht_id.*!=.*user\.data\["yacht_id"\]',
            r'if\s+user\.data\["yacht_id"\]\s*!=\s*yacht_id',
            r'yacht isolation breach',  # Log message
        ],
        "severity": "CRITICAL",
        "required_for": ["MUTATE_LOW", "MUTATE_MEDIUM", "MUTATE_HIGH"]
    },

    "authentication": {
        "description": "G0.2: Authentication Gate - Validates user_id exists",
        "patterns": [
            r'if\s+not\s+user_id',
            r'user_id\s+==\s+"undefined"',
            r'UNAUTHORIZED.*not\s+authenticated',
        ],
        "severity": "CRITICAL",
        "required_for": ["MUTATE_LOW", "MUTATE_MEDIUM", "MUTATE_HIGH"]
    },

    "role_check": {
        "description": "G0.3: Role-Based Access Control - Checks allowed roles",
        "patterns": [
            r'allowed_roles\s*=\s*\[',
            r'user\["role"\]\s+not\s+in\s+allowed_roles',
            r'FORBIDDEN.*cannot\s+perform',
        ],
        "severity": "CRITICAL",
        "required_for": ["MUTATE_LOW", "MUTATE_MEDIUM", "MUTATE_HIGH"]
    },

    "audit_log": {
        "description": "G0.6: Audit Trail - Creates pms_audit_log entry",
        "patterns": [
            r'pms_audit_log.*\.insert\(',
            r'table\("pms_audit_log"\)',
            r'INSERT\s+INTO\s+pms_audit_log',
        ],
        "severity": "CRITICAL",
        "required_for": ["MUTATE_LOW", "MUTATE_MEDIUM", "MUTATE_HIGH"]
    },

    "transaction_safety": {
        "description": "G0.4: Atomic Transactions - Multi-table operations in transaction",
        "patterns": [
            r'async\s+with.*\.transaction\(\)',
            r'BEGIN\s+TRANSACTION',
            r'# BEGIN transaction',
        ],
        "severity": "HIGH",
        "required_for": ["MUTATE_MEDIUM", "MUTATE_HIGH"],
        "conditional": "Only if multi-table mutation"
    },

    "signature_check": {
        "description": "G0.8: Signature Validation - Checks signature when required",
        "patterns": [
            r'signature_data\s*=\s*params\.get\("signature_data"\)',
            r'SIGNATURE_REQUIRED',
            r'if\s+.*signature_required',
        ],
        "severity": "HIGH",
        "required_for": ["MUTATE_HIGH"],
        "conditional": "Only if signature_required in action catalog"
    }
}


class G0Checker:
    """Checks handler files for G0 compliance"""

    def __init__(self, handlers_dir: Path):
        self.handlers_dir = handlers_dir
        self.violations = []
        self.warnings = []
        self.files_checked = 0

    def check_handler_file(self, filepath: Path) -> Tuple[bool, List[Dict]]:
        """
        Check a single handler file for G0 compliance

        Returns:
            (passed, issues) - passed=True if all G0 checks pass
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        issues = []

        # Detect handler classification from file content
        classification = self._detect_classification(content)

        # Check each G0 pattern
        for guard_id, guard_config in G0_PATTERNS.items():
            # Skip if not required for this classification
            if classification not in guard_config["required_for"]:
                continue

            # Check if any pattern matches
            found = False
            for pattern in guard_config["patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    found = True
                    break

            if not found:
                issues.append({
                    "guard": guard_id,
                    "description": guard_config["description"],
                    "severity": guard_config["severity"],
                    "conditional": guard_config.get("conditional"),
                    "file": str(filepath),
                    "classification": classification
                })

        return len(issues) == 0, issues

    def _detect_classification(self, content: str) -> str:
        """Detect handler classification from file content"""

        # Look for classification markers in docstrings or comments
        if re.search(r'MUTATE_HIGH', content):
            return "MUTATE_HIGH"
        elif re.search(r'MUTATE_MEDIUM', content):
            return "MUTATE_MEDIUM"
        elif re.search(r'MUTATE_LOW', content):
            return "MUTATE_LOW"
        else:
            # Default to MUTATE_MEDIUM (strictest non-signature check)
            return "MUTATE_MEDIUM"

    def check_all_handlers(self) -> bool:
        """
        Check all *_mutation_handlers.py files

        Returns:
            True if all files pass, False if violations found
        """
        # Find all mutation handler files
        handler_files = list(self.handlers_dir.glob("*_mutation_handlers.py"))

        if not handler_files:
            print(f"⚠️  WARNING: No mutation handler files found in {self.handlers_dir}")
            return True

        print(f"🔍 Checking {len(handler_files)} mutation handler files...\n")

        all_passed = True

        for handler_file in handler_files:
            self.files_checked += 1
            passed, issues = self.check_handler_file(handler_file)

            if not passed:
                all_passed = False
                print(f"❌ FAILED: {handler_file.name}")

                for issue in issues:
                    severity_icon = "🔴" if issue["severity"] == "CRITICAL" else "🟠"
                    print(f"   {severity_icon} {issue['description']}")
                    if issue.get("conditional"):
                        print(f"      Note: {issue['conditional']}")

                    self.violations.append(issue)

                print()
            else:
                print(f"✅ PASSED: {handler_file.name}")

        return all_passed

    def print_summary(self):
        """Print check summary"""
        print("\n" + "="*70)
        print("G0 COMPLIANCE CHECK SUMMARY")
        print("="*70)

        print(f"\nFiles checked: {self.files_checked}")

        if not self.violations:
            print("✅ ALL CHECKS PASSED")
            print("\nAll mutation handlers implement required G0 guard rails.")
            return

        print(f"❌ VIOLATIONS FOUND: {len(self.violations)}")

        # Group violations by guard
        violations_by_guard = {}
        for violation in self.violations:
            guard = violation["guard"]
            if guard not in violations_by_guard:
                violations_by_guard[guard] = []
            violations_by_guard[guard].append(violation)

        print("\nViolations by guard:")
        for guard, issues in violations_by_guard.items():
            severity = issues[0]["severity"]
            description = issues[0]["description"]
            print(f"\n  {guard.upper()} ({severity}): {description}")
            print(f"  Missing in {len(issues)} file(s):")
            for issue in issues:
                print(f"    - {Path(issue['file']).name} ({issue['classification']})")

        print("\n" + "="*70)
        print("REQUIRED ACTIONS:")
        print("="*70)
        print("\n1. Add missing G0 guards to the files listed above")
        print("2. Follow the pattern from commit_receiving_session handler")
        print("3. Do NOT skip G0 guards for 'speed' or 'simplicity'")
        print("4. Re-run this check after fixes")
        print("\nG0 guards are NON-NEGOTIABLE for security and accountability.")


def main():
    """Main entry point"""

    # Find handlers directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    handlers_dir = project_root / "apps" / "api" / "handlers"

    if not handlers_dir.exists():
        print(f"❌ ERROR: Handlers directory not found: {handlers_dir}")
        print("\nExpected structure: {project_root}/apps/api/handlers/")
        sys.exit(2)

    # Run checks
    checker = G0Checker(handlers_dir)
    passed = checker.check_all_handlers()
    checker.print_summary()

    # Exit with appropriate code
    if passed:
        print("\n✅ CI CHECK PASSED - All G0 guards present")
        sys.exit(0)
    else:
        print("\n❌ CI CHECK FAILED - G0 violations must be fixed")
        sys.exit(1)


if __name__ == "__main__":
    main()
