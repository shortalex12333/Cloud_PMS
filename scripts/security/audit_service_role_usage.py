#!/usr/bin/env python3
"""
Security Audit: Service Role Usage

Purpose:
- Find all service role client creation patterns
- Verify yacht_id validation before DB writes
- Flag new service client usage without validators

Usage:
    python scripts/security/audit_service_role_usage.py
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Patterns to search for
SERVICE_ROLE_PATTERNS = [
    r"create_client\s*\([^)]*service[_-]?key",
    r"create_client\s*\([^)]*SERVICE[_-]?KEY",
    r"supabase\.create_client\s*\(",
    r"Client\s*\([^)]*service[_-]?role",
    r"SERVICE_KEY\s*=",
    r"service_role_key\s*=",
    r"apikey.*service",
    r"Authorization.*service",
]

# Files to check for yacht_id validation
VALIDATION_PATTERNS = [
    r"yacht_id\s*=",
    r"\.eq\s*\(\s*['\"]yacht_id['\"]",
    r"validate.*yacht",
    r"get_user_yacht_id",
    r"jwt_yacht_id",
]

# Directories to scan
SCAN_DIRS = [
    "apps/api",
    "tools/ops",
    "scripts",
]

# Directories to skip
SKIP_DIRS = [
    "node_modules",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
]

# File extensions to scan
SCAN_EXTENSIONS = [".py"]


def find_files(base_path: str, extensions: List[str]) -> List[Path]:
    """Find all files with given extensions."""
    files = []
    for ext in extensions:
        for path in Path(base_path).rglob(f"*{ext}"):
            # Skip excluded directories
            if any(skip in str(path) for skip in SKIP_DIRS):
                continue
            files.append(path)
    return files


def search_patterns(file_path: Path, patterns: List[str]) -> List[Tuple[int, str, str]]:
    """Search for patterns in a file. Returns list of (line_num, pattern, line)."""
    matches = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append((line_num, pattern, line.strip()[:100]))
                        break  # One match per line is enough
    except Exception as e:
        print(f"  Warning: Could not read {file_path}: {e}")
    return matches


def check_file_has_validation(file_path: Path) -> bool:
    """Check if file has yacht_id validation patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern in VALIDATION_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
    except Exception:
        pass
    return False


def audit_directory(base_path: str) -> Dict:
    """Audit a directory for service role usage."""
    results = {
        "files_scanned": 0,
        "service_role_usages": [],
        "missing_validation": [],
        "warnings": [],
    }

    if not os.path.exists(base_path):
        results["warnings"].append(f"Directory not found: {base_path}")
        return results

    files = find_files(base_path, SCAN_EXTENSIONS)
    results["files_scanned"] = len(files)

    for file_path in files:
        # Check for service role patterns
        matches = search_patterns(file_path, SERVICE_ROLE_PATTERNS)

        if matches:
            has_validation = check_file_has_validation(file_path)

            for line_num, pattern, line in matches:
                entry = {
                    "file": str(file_path),
                    "line": line_num,
                    "pattern": pattern,
                    "content": line,
                    "has_yacht_validation": has_validation,
                }
                results["service_role_usages"].append(entry)

                if not has_validation:
                    results["missing_validation"].append(entry)

    return results


def print_report(results: Dict, directory: str):
    """Print audit report for a directory."""
    print(f"\n{'=' * 70}")
    print(f"DIRECTORY: {directory}")
    print(f"{'=' * 70}")
    print(f"Files scanned: {results['files_scanned']}")
    print(f"Service role usages found: {len(results['service_role_usages'])}")
    print(f"Missing yacht validation: {len(results['missing_validation'])}")

    if results["warnings"]:
        print(f"\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")

    if results["service_role_usages"]:
        print(f"\n📋 Service Role Usages:")
        for entry in results["service_role_usages"]:
            validation_status = "✅" if entry["has_yacht_validation"] else "❌"
            print(f"  {validation_status} {entry['file']}:{entry['line']}")
            print(f"     {entry['content'][:80]}...")

    if results["missing_validation"]:
        print(f"\n🚨 MISSING YACHT VALIDATION (requires review):")
        for entry in results["missing_validation"]:
            print(f"  ❌ {entry['file']}:{entry['line']}")
            print(f"     {entry['content'][:80]}...")


def main():
    print("=" * 70)
    print("SERVICE ROLE USAGE SECURITY AUDIT")
    print("=" * 70)

    all_results = []
    total_issues = 0

    for directory in SCAN_DIRS:
        full_path = os.path.join(os.getcwd(), directory)
        results = audit_directory(full_path)
        all_results.append((directory, results))
        total_issues += len(results["missing_validation"])

    # Print reports
    for directory, results in all_results:
        print_report(results, directory)

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    total_files = sum(r["files_scanned"] for _, r in all_results)
    total_usages = sum(len(r["service_role_usages"]) for _, r in all_results)

    print(f"Total files scanned: {total_files}")
    print(f"Total service role usages: {total_usages}")
    print(f"Files missing yacht validation: {total_issues}")

    if total_issues > 0:
        print(f"\n❌ AUDIT FAILED: {total_issues} files need yacht_id validation")
        print("\nRecommended actions:")
        print("1. Add yacht_id validation before any DB write operations")
        print("2. Use jwt_yacht_id() or get_user_yacht_id() for yacht scoping")
        print("3. Consider adding a pre-commit hook to flag service role usage")
        sys.exit(1)
    else:
        print(f"\n✅ AUDIT PASSED: All service role usages have yacht validation")
        sys.exit(0)


if __name__ == "__main__":
    main()
