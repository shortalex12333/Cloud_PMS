#!/usr/bin/env python3
"""
G0 Compliance Checker V2
========================

Behavioral enforcement of security guards using guards.yml

This script enforces guard rails through:
1. GUARDS dict declaration in handlers
2. Behavioral checks (required function calls)
3. Waiver validation (expiry, required fields)
4. Approval gate enforcement

Usage:
    python scripts/check_g0_compliance_v2.py
    python scripts/check_g0_compliance_v2.py --verbose
    python scripts/check_g0_compliance_v2.py --file handlers/fault_mutation_handlers.py

Exit codes:
    0 - All checks passed
    1 - G0 violations (BLOCKS)
    2 - G1 violations without valid waiver (BLOCKS)
    3 - Script error
"""

import re
import sys
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import yaml


class GuardConfig:
    """Load and parse guards.yml"""

    def __init__(self, config_path: Path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.g0_guards = {g['id']: g for g in self.config['g0']}
        self.g1_guards = {g['id']: g for g in self.config['g1']}
        self.action_requirements = self.config['action_types']

    def get_required_guards(self, action_type: str) -> Tuple[List[str], List[str]]:
        """Get required and conditional G0 guards for action type"""
        reqs = self.action_requirements.get(action_type, {})
        required = reqs.get('required_g0', [])
        conditional = reqs.get('conditional_g0', [])
        return required, conditional


class HandlerAnalyzer:
    """Analyze handler file for guard compliance"""

    def __init__(self, filepath: Path, guard_config: GuardConfig):
        self.filepath = filepath
        self.guard_config = guard_config

        with open(filepath, 'r', encoding='utf-8') as f:
            self.content = f.read()

        self.violations = []
        self.warnings = []

    def extract_guards_dict(self) -> Optional[Dict]:
        """Extract GUARDS dict from handler file using AST"""
        try:
            tree = ast.parse(self.content)

            for node in ast.walk(tree):
                # Look for class definition
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        # Look for async function definitions
                        if isinstance(item, ast.AsyncFunctionDef):
                            # Look for GUARDS dict in function body
                            for stmt in item.body:
                                if isinstance(stmt, ast.Assign):
                                    for target in stmt.targets:
                                        if isinstance(target, ast.Name) and target.id == 'GUARDS':
                                            # Extract dict literal
                                            if isinstance(stmt.value, ast.Dict):
                                                guards_dict = {}
                                                for k, v in zip(stmt.value.keys, stmt.value.values):
                                                    if isinstance(k, ast.Constant):
                                                        key = k.value
                                                        if isinstance(v, ast.Constant):
                                                            guards_dict[key] = v.value
                                                return guards_dict

            return None

        except Exception as e:
            print(f"Warning: Could not parse {self.filepath}: {e}")
            return None

    def detect_action_type(self) -> str:
        """Detect action type from file content"""
        if re.search(r'MUTATE_HIGH|Classification:\s*MUTATE_HIGH', self.content, re.IGNORECASE):
            return "MUTATE_HIGH"
        elif re.search(r'MUTATE_MEDIUM|Classification:\s*MUTATE_MEDIUM', self.content, re.IGNORECASE):
            return "MUTATE_MEDIUM"
        elif re.search(r'MUTATE_LOW|Classification:\s*MUTATE_LOW', self.content, re.IGNORECASE):
            return "MUTATE_LOW"
        elif re.search(r'READ|Classification:\s*READ', self.content, re.IGNORECASE):
            return "READ"
        else:
            # Default to strictest
            return "MUTATE_MEDIUM"

    def check_guards_dict_presence(self) -> bool:
        """Check if handler declares GUARDS dict"""
        guards_dict = self.extract_guards_dict()

        if not guards_dict:
            # Fallback: check for GUARDS in content
            if 'GUARDS = {' not in self.content and 'GUARDS={' not in self.content:
                self.violations.append({
                    "type": "missing_guards_dict",
                    "severity": "CRITICAL",
                    "message": "Handler does not declare GUARDS dict",
                    "fix": "Add GUARDS = {...} dict to handler function"
                })
                return False

        return True

    def check_required_function_calls(self, action_type: str) -> bool:
        """Check for required function calls based on action type"""
        required_guards, _ = self.guard_config.get_required_guards(action_type)

        all_passed = True

        for guard_id in required_guards:
            guard = self.guard_config.g0_guards.get(guard_id)
            if not guard:
                continue

            required_calls = guard.get('required_calls', [])

            for call_pattern in required_calls:
                if not re.search(call_pattern, self.content, re.MULTILINE):
                    self.violations.append({
                        "type": "missing_required_call",
                        "severity": "CRITICAL",
                        "guard": guard_id,
                        "message": f"{guard['name']}: Missing required pattern '{call_pattern}'",
                        "fix": guard.get('behavioral_check', 'See guards.yml for implementation')
                    })
                    all_passed = False
                    break  # One missing pattern is enough

        return all_passed

    def check_specific_guards(self) -> bool:
        """Check specific guard implementations"""
        all_passed = True

        # G0.1: Yacht Isolation (CRITICAL)
        if not re.search(r'yacht_id.*!=.*user.*yacht_id', self.content):
            if not re.search(r'require_yacht_isolation', self.content):
                self.violations.append({
                    "type": "missing_yacht_isolation",
                    "severity": "CRITICAL",
                    "guard": "G0.1",
                    "message": "Yacht isolation check not found",
                    "fix": "Add: if user['yacht_id'] != yacht_id: raise Forbidden(...)"
                })
                all_passed = False

        # G0.6: Audit Log (CRITICAL)
        if '_execute' in self.content:  # Only for mutation handlers
            if not re.search(r'create_audit_log|pms_audit_log', self.content):
                self.violations.append({
                    "type": "missing_audit_log",
                    "severity": "CRITICAL",
                    "guard": "G0.6",
                    "message": "Audit log creation not found",
                    "fix": "Add: await create_audit_log(...) after mutation"
                })
                all_passed = False

        # G0.9: Situation ID (for MUTATE_HIGH)
        action_type = self.detect_action_type()
        if action_type == "MUTATE_HIGH":
            if not re.search(r'situation_id|require_situation', self.content):
                self.violations.append({
                    "type": "missing_situation_id",
                    "severity": "CRITICAL",
                    "guard": "G0.9",
                    "message": "MUTATE_HIGH must require situation_id",
                    "fix": "Add: situation_id = params.get('situation_id'); if not situation_id: raise ..."
                })
                all_passed = False

        return all_passed

    def check_all(self) -> bool:
        """Run all checks"""
        action_type = self.detect_action_type()

        passed = True
        passed &= self.check_guards_dict_presence()
        passed &= self.check_required_function_calls(action_type)
        passed &= self.check_specific_guards()

        return passed


class WaiverValidator:
    """Validate waiver files"""

    def __init__(self, waivers_dir: Path):
        self.waivers_dir = waivers_dir
        self.violations = []

    def check_waivers(self) -> bool:
        """Check all waiver files for validity"""
        if not self.waivers_dir.exists():
            return True  # No waivers = OK

        all_passed = True

        for waiver_file in self.waivers_dir.glob("*.md"):
            passed = self.validate_waiver(waiver_file)
            if not passed:
                all_passed = False

        return all_passed

    def validate_waiver(self, waiver_path: Path) -> bool:
        """Validate single waiver file"""
        with open(waiver_path, 'r') as f:
            content = f.read()

        passed = True

        # Extract required fields
        guard_match = re.search(r'Guard:\s*(G\d+\.\d+)', content)
        reason_match = re.search(r'Reason:\s*(.+)', content)
        mitigation_match = re.search(r'Mitigation:\s*(.+)', content)
        expiry_match = re.search(r'Expiry:\s*(\d{4}-\d{2}-\d{2})', content)
        owner_match = re.search(r'Owner:\s*(@\w+)', content)

        # Check required fields present
        if not guard_match:
            self.violations.append({
                "file": waiver_path.name,
                "issue": "Missing 'Guard' field"
            })
            passed = False

        if not reason_match:
            self.violations.append({
                "file": waiver_path.name,
                "issue": "Missing 'Reason' field"
            })
            passed = False

        if not mitigation_match:
            self.violations.append({
                "file": waiver_path.name,
                "issue": "Missing 'Mitigation' field"
            })
            passed = False

        if not expiry_match:
            self.violations.append({
                "file": waiver_path.name,
                "issue": "Missing 'Expiry' field"
            })
            passed = False

        if not owner_match:
            self.violations.append({
                "file": waiver_path.name,
                "issue": "Missing 'Owner' field"
            })
            passed = False

        # Check expiry date
        if expiry_match:
            expiry_str = expiry_match.group(1)
            expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')

            if expiry_date < datetime.now():
                self.violations.append({
                    "file": waiver_path.name,
                    "issue": f"Waiver expired on {expiry_str}"
                })
                passed = False

        # Check if waiving G0 (NOT ALLOWED)
        if guard_match:
            guard_id = guard_match.group(1)
            if guard_id.startswith('G0.'):
                self.violations.append({
                    "file": waiver_path.name,
                    "issue": f"Cannot waive G0 guard ({guard_id}). G0 guards are mandatory."
                })
                passed = False

        return passed


class ApprovalValidator:
    """Validate approval files for dangerous operations"""

    def __init__(self, approvals_dir: Path):
        self.approvals_dir = approvals_dir
        self.violations = []

    def check_approval(self, action_name: str) -> bool:
        """Check if approval file exists and is valid"""
        approval_file = self.approvals_dir / f"{action_name}.approval"

        if not approval_file.exists():
            self.violations.append({
                "action": action_name,
                "issue": f"Missing approval file: {approval_file}"
            })
            return False

        with open(approval_file, 'r') as f:
            content = f.read()

        # Check for 3 required signatures
        product_match = re.search(r'Product:\s*@\w+\s+\d{4}-\d{2}-\d{2}', content)
        engineering_match = re.search(r'Engineering:\s*@\w+\s+\d{4}-\d{2}-\d{2}', content)
        security_match = re.search(r'Security:\s*@\w+\s+\d{4}-\d{2}-\d{2}', content)

        passed = True

        if not product_match:
            self.violations.append({
                "action": action_name,
                "issue": "Missing Product signature"
            })
            passed = False

        if not engineering_match:
            self.violations.append({
                "action": action_name,
                "issue": "Missing Engineering signature"
            })
            passed = False

        if not security_match:
            self.violations.append({
                "action": action_name,
                "issue": "Missing Security signature"
            })
            passed = False

        return passed


class ComplianceChecker:
    """Main compliance checker"""

    def __init__(self, project_root: Path, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose

        # Load config
        config_path = project_root / "guards.yml"
        if not config_path.exists():
            print(f"❌ ERROR: guards.yml not found at {config_path}")
            sys.exit(3)

        self.guard_config = GuardConfig(config_path)

        # Set up directories
        self.handlers_dir = project_root / "apps" / "api" / "handlers"
        self.waivers_dir = project_root / "waivers"
        self.approvals_dir = project_root / "approvals"

        self.all_violations = []

    def check_all_handlers(self) -> bool:
        """Check all mutation handlers"""
        handler_files = list(self.handlers_dir.glob("*_mutation_handlers.py"))

        if not handler_files:
            print(f"⚠️  WARNING: No mutation handler files found in {self.handlers_dir}")
            return True

        print(f"🔍 Checking {len(handler_files)} mutation handler files...\n")

        all_passed = True

        for handler_file in handler_files:
            analyzer = HandlerAnalyzer(handler_file, self.guard_config)
            passed = analyzer.check_all()

            if not passed:
                all_passed = False
                print(f"❌ FAILED: {handler_file.name}")

                for violation in analyzer.violations:
                    severity_icon = "🔴" if violation["severity"] == "CRITICAL" else "🟠"
                    print(f"   {severity_icon} [{violation.get('guard', 'N/A')}] {violation['message']}")

                    if self.verbose and violation.get('fix'):
                        print(f"      Fix: {violation['fix']}")

                    self.all_violations.append({
                        **violation,
                        "file": handler_file.name
                    })

                print()
            else:
                print(f"✅ PASSED: {handler_file.name}")

        return all_passed

    def check_waivers(self) -> bool:
        """Check all waivers"""
        print(f"\n🔍 Checking waivers...\n")

        validator = WaiverValidator(self.waivers_dir)
        passed = validator.check_waivers()

        if not passed:
            print(f"❌ WAIVER VIOLATIONS:")
            for violation in validator.violations:
                print(f"   🔴 {violation['file']}: {violation['issue']}")
                self.all_violations.append(violation)
        else:
            if self.waivers_dir.exists():
                waiver_count = len(list(self.waivers_dir.glob("*.md")))
                print(f"✅ All {waiver_count} waivers valid")
            else:
                print(f"✅ No waivers (none needed)")

        return passed

    def check_approvals(self, required_approvals: List[str]) -> bool:
        """Check required approval files"""
        if not required_approvals:
            return True

        print(f"\n🔍 Checking approvals...\n")

        validator = ApprovalValidator(self.approvals_dir)
        all_passed = True

        for action_name in required_approvals:
            passed = validator.check_approval(action_name)
            if not passed:
                all_passed = False

        if not all_passed:
            print(f"❌ APPROVAL VIOLATIONS:")
            for violation in validator.violations:
                print(f"   🔴 {violation['action']}: {violation['issue']}")
                self.all_violations.append(violation)

        return all_passed

    def print_summary(self):
        """Print summary"""
        print("\n" + "=" * 70)
        print("G0 COMPLIANCE CHECK SUMMARY")
        print("=" * 70)

        if not self.all_violations:
            print("\n✅ ALL CHECKS PASSED")
            print("\nAll handlers comply with guard requirements.")
            return

        # Group violations by severity
        critical = [v for v in self.all_violations if v.get("severity") == "CRITICAL"]
        high = [v for v in self.all_violations if v.get("severity") == "HIGH"]
        other = [v for v in self.all_violations if v.get("severity") not in ["CRITICAL", "HIGH"]]

        print(f"\n❌ VIOLATIONS FOUND:")
        print(f"   🔴 CRITICAL: {len(critical)}")
        print(f"   🟠 HIGH: {len(high)}")
        print(f"   ⚠️  OTHER: {len(other)}")

        print("\n" + "=" * 70)
        print("REQUIRED ACTIONS:")
        print("=" * 70)
        print("\n1. Fix all G0 violations (CRITICAL)")
        print("2. Add waivers for valid G1 exceptions")
        print("3. Get approvals for dangerous operations")
        print("4. Re-run this check")
        print("\nG0 guards are NON-NEGOTIABLE.")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Check G0 compliance")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", "-f", help="Check specific file")
    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    checker = ComplianceChecker(project_root, verbose=args.verbose)

    # Check handlers
    handlers_passed = checker.check_all_handlers()

    # Check waivers
    waivers_passed = checker.check_waivers()

    # Check approvals (add actions that require approval)
    required_approvals = ["import_data"]  # Add more as needed
    approvals_passed = checker.check_approvals(required_approvals)

    # Print summary
    checker.print_summary()

    # Determine exit code
    all_passed = handlers_passed and waivers_passed and approvals_passed

    if all_passed:
        print("\n✅ CI CHECK PASSED")
        sys.exit(0)
    else:
        # Check if only G1 violations
        critical_violations = [v for v in checker.all_violations if v.get("severity") == "CRITICAL"]
        if critical_violations:
            print("\n❌ CI CHECK FAILED - G0 VIOLATIONS")
            sys.exit(1)
        else:
            print("\n❌ CI CHECK FAILED - G1 VIOLATIONS WITHOUT WAIVER")
            sys.exit(2)


if __name__ == "__main__":
    main()
