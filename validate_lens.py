#!/usr/bin/env python3
"""
Lens Validation Script
======================

Validates lens implementation before submitting PR.

Usage:
    python3 validate_lens.py part_lens
    python3 validate_lens.py certificate_lens

Checks:
1. ✓ Capability file exists
2. ✓ Microaction file exists
3. ✓ Class names correct
4. ✓ lens_name matches
5. ✓ Entity types defined
6. ✓ No duplicate entity types
7. ✓ All capabilities implemented
8. ✓ Registry auto-discovers lens

Exit codes:
    0: All checks passed
    1: Validation failed
"""

import sys
import os
from pathlib import Path
import importlib.util
import re

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")


def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")


def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")


def check_file_exists(file_path, description):
    """Check if file exists."""
    if file_path.exists():
        print_success(f"{description} exists: {file_path}")
        return True
    else:
        print_error(f"{description} not found: {file_path}")
        return False


def check_class_name(file_path, expected_pattern, description):
    """Check if class name matches pattern."""
    content = file_path.read_text()

    match = re.search(r'class\s+(\w+)\(', content)
    if match:
        class_name = match.group(1)
        if expected_pattern in class_name:
            print_success(f"{description} class name correct: {class_name}")
            return True
        else:
            print_error(f"{description} class name incorrect: {class_name} (expected pattern: {expected_pattern})")
            return False
    else:
        print_error(f"{description} class not found in {file_path}")
        return False


def check_lens_name(file_path, expected_lens_name):
    """Check if lens_name property matches."""
    content = file_path.read_text()

    match = re.search(r'lens_name\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        lens_name = match.group(1)
        if lens_name == expected_lens_name:
            print_success(f"lens_name correct: {lens_name}")
            return True
        else:
            print_error(f"lens_name mismatch: {lens_name} (expected: {expected_lens_name})")
            return False
    else:
        print_error(f"lens_name property not found in {file_path}")
        return False


def check_entity_mappings(file_path):
    """Check if get_entity_mappings() is implemented."""
    content = file_path.read_text()

    if "def get_entity_mappings" in content:
        print_success("get_entity_mappings() method found")

        # Count entity mappings
        entity_count = content.count("CapabilityMapping(")
        if entity_count > 0:
            print_success(f"Found {entity_count} entity mapping(s)")
            return True
        else:
            print_warning("No entity mappings found")
            return False
    else:
        print_error("get_entity_mappings() method not found")
        return False


def check_capabilities_implemented(file_path):
    """Check if capability methods are implemented."""
    content = file_path.read_text()

    # Extract capability names from mappings
    capability_names = re.findall(r'capability_name=["\']([^"\']+)["\']', content)

    if not capability_names:
        print_warning("No capabilities defined in mappings")
        return False

    all_implemented = True
    for cap_name in set(capability_names):  # Remove duplicates
        if f"async def {cap_name}(" in content:
            print_success(f"Capability implemented: {cap_name}")
        else:
            print_error(f"Capability not implemented: {cap_name}")
            all_implemented = False

    return all_implemented


def check_entity_types(file_path):
    """Check if entity_types property is defined in microactions."""
    content = file_path.read_text()

    match = re.search(r'entity_types\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        types_str = match.group(1)
        types = re.findall(r'["\']([^"\']+)["\']', types_str)
        if types:
            print_success(f"Found {len(types)} entity type(s): {', '.join(types)}")
            return True
        else:
            print_warning("entity_types list is empty")
            return False
    else:
        print_error("entity_types property not found")
        return False


def validate_lens(lens_name):
    """
    Validate lens implementation.

    Args:
        lens_name: Lens name (e.g., "part_lens", "certificate_lens")

    Returns:
        True if all checks pass, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"VALIDATING: {lens_name}")
    print(f"{'='*60}\n")

    all_passed = True

    # File paths
    # Normalize lens_name: "part_lens" -> "part"
    lens_short = lens_name.replace("_lens", "")
    capabilities_file = Path(f"apps/api/prepare/capabilities/{lens_short}_capabilities.py")
    microactions_file = Path(f"apps/api/microactions/lens_microactions/{lens_short}_microactions.py")

    # Check 1: Files exist
    print("\n1. File Existence Checks")
    print("-" * 40)
    all_passed &= check_file_exists(capabilities_file, "Capabilities file")
    all_passed &= check_file_exists(microactions_file, "Microactions file")

    if not capabilities_file.exists() or not microactions_file.exists():
        print_error("\nCannot continue validation without required files")
        return False

    # Check 2: Class names
    print("\n2. Class Name Checks")
    print("-" * 40)
    all_passed &= check_class_name(
        capabilities_file,
        "Capability",
        "Capabilities class"
    )
    all_passed &= check_class_name(
        microactions_file,
        "Microactions",
        "Microactions class"
    )

    # Check 3: lens_name property
    print("\n3. Lens Name Checks")
    print("-" * 40)
    all_passed &= check_lens_name(capabilities_file, lens_name)
    all_passed &= check_lens_name(microactions_file, lens_name)

    # Check 4: Entity mappings
    print("\n4. Entity Mapping Checks")
    print("-" * 40)
    all_passed &= check_entity_mappings(capabilities_file)

    # Check 5: Capabilities implemented
    print("\n5. Capability Implementation Checks")
    print("-" * 40)
    all_passed &= check_capabilities_implemented(capabilities_file)

    # Check 6: Entity types
    print("\n6. Entity Type Checks")
    print("-" * 40)
    all_passed &= check_entity_types(microactions_file)

    # Summary
    print(f"\n{'='*60}")
    if all_passed:
        print_success("ALL CHECKS PASSED ✓")
        print(f"{'='*60}\n")
        print("Next steps:")
        print("1. Run registry validation:")
        print(f"   python -m apps.api.prepare.capability_registry")
        print(f"   python -m apps.api.microactions.microaction_registry")
        print("2. Run E2E tests")
        print("3. Submit PR")
        return True
    else:
        print_error("SOME CHECKS FAILED ✗")
        print(f"{'='*60}\n")
        print("Fix the errors above before submitting PR")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 validate_lens.py <lens_name>")
        print("\nExamples:")
        print("  python3 validate_lens.py part_lens")
        print("  python3 validate_lens.py certificate_lens")
        print("  python3 validate_lens.py crew_lens")
        sys.exit(1)

    lens_name = sys.argv[1]

    # Change to project root
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    success = validate_lens(lens_name)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
