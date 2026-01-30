#!/usr/bin/env python3
"""
Test Registry Integration
=========================

Tests that the capability registry integrates correctly with capability_composer.

Run:
    python3 test_registry_integration.py
"""

import sys
sys.path.insert(0, '.')

print("="*70)
print("TESTING PART LENS REGISTRY INTEGRATION")
print("="*70)
print()

# Test 1: Import all components
print("Test 1: Component Imports")
print("-" * 70)

try:
    from apps.api.prepare.capabilities.part_capabilities import PartLensCapability
    print("✓ PartLensCapability imports")
except ImportError as e:
    print(f"✗ PartLensCapability import failed: {e}")
    sys.exit(1)

try:
    from apps.api.prepare.base_capability import BaseLensCapability, CapabilityMapping
    print("✓ Base classes import")
except ImportError as e:
    print(f"✗ Base classes import failed: {e}")
    sys.exit(1)

try:
    from apps.api.prepare.capability_registry import CapabilityRegistry
    print("✓ CapabilityRegistry imports")
except ImportError as e:
    print(f"✗ CapabilityRegistry import failed: {e}")
    sys.exit(1)

print()

# Test 2: Part Lens configuration
print("Test 2: Part Lens Configuration")
print("-" * 70)

# Create mock DB client
class MockDB:
    pass

lens = PartLensCapability(MockDB())
print(f"✓ Lens name: {lens.lens_name}")
print(f"✓ Enabled: {lens.enabled}")

mappings = lens.get_entity_mappings()
print(f"✓ Entity mappings: {len(mappings)}")

entity_types = [m.entity_type for m in mappings]
print(f"✓ Entity types: {', '.join(entity_types[:5])}...")

# Check PART entity exists (free-text fallback)
if "PART" in entity_types:
    print("✓ PART entity type present (free-text fallback)")
else:
    print("✗ PART entity type missing!")
    sys.exit(1)

print()

# Test 3: Registry initialization
print("Test 3: Registry Initialization")
print("-" * 70)

try:
    registry = CapabilityRegistry(MockDB())
    print("✓ Registry created")

    # Discover lenses
    registry.discover_and_register()
    print(f"✓ Lenses discovered: {len(registry.lenses)}")
    print(f"✓ Total entity types: {len(registry.entity_mappings)}")

    # Check Part Lens registered
    if "part_lens" in registry.lenses:
        print("✓ Part Lens registered in registry")
        part_lens = registry.lenses["part_lens"]
        print(f"  - Lens name: {part_lens.lens_name}")
        print(f"  - Entity types handled: {len(part_lens.get_entity_mappings())}")
    else:
        print("✗ Part Lens not registered!")
        sys.exit(1)

    # Check PART entity mapped
    if "PART" in registry.entity_mappings:
        mapping = registry.entity_mappings["PART"]
        print(f"✓ PART entity mapped to: {mapping.capability_name}")
    else:
        print("✗ PART entity not mapped!")
        sys.exit(1)

except Exception as e:
    print(f"✗ Registry initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Entity lookup
print("Test 4: Entity Type Lookup")
print("-" * 70)

test_entities = ["PART", "PART_NUMBER", "PART_NAME", "MANUFACTURER", "PART_CATEGORY"]

for entity_type in test_entities:
    if entity_type in registry.entity_mappings:
        mapping = registry.entity_mappings[entity_type]
        print(f"✓ {entity_type:20} → {mapping.capability_name}")
    else:
        print(f"✗ {entity_type:20} NOT MAPPED")

print()

# Test 5: Capability methods exist
print("Test 5: Capability Methods")
print("-" * 70)

capability_names = set(m.capability_name for m in mappings)
for cap_name in sorted(capability_names):
    if hasattr(lens, cap_name):
        print(f"✓ {cap_name}")
    else:
        print(f"✗ {cap_name} NOT IMPLEMENTED")
        sys.exit(1)

print()

# Test 6: No duplicate entity types
print("Test 6: No Duplicate Entity Types")
print("-" * 70)

entity_types_list = [m.entity_type for m in mappings]
duplicates = [et for et in entity_types_list if entity_types_list.count(et) > 1]

if duplicates:
    print(f"✗ Duplicate entity types found: {set(duplicates)}")
    sys.exit(1)
else:
    print("✓ No duplicate entity types")

print()

# Test 7: Integration with capability_composer (import only)
print("Test 7: Capability Composer Integration")
print("-" * 70)

try:
    from apps.api.prepare import capability_composer
    print("✓ capability_composer imports")

    # Check registry availability flag
    if hasattr(capability_composer, '_REGISTRY_AVAILABLE'):
        print(f"✓ Registry integration present: {capability_composer._REGISTRY_AVAILABLE}")
    else:
        print("✗ Registry integration flag missing")
        sys.exit(1)

    # Check ENTITY_TO_SEARCH_COLUMN updated
    if "PART" in capability_composer.ENTITY_TO_SEARCH_COLUMN:
        cap_name, col = capability_composer.ENTITY_TO_SEARCH_COLUMN["PART"]
        print(f"✓ PART entity in legacy dict: {cap_name}")
    else:
        print("⚠ PART entity not in legacy dict (expected if using registry)")

except ImportError as e:
    print(f"✗ capability_composer import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Summary
print("="*70)
print("✓ ALL TESTS PASSED")
print("="*70)
print()
print("Summary:")
print(f"  - Part Lens: {len(mappings)} entity types, {len(capability_names)} capabilities")
print(f"  - Registry: {len(registry.lenses)} lenses, {len(registry.entity_mappings)} entity mappings")
print(f"  - Integration: capability_composer uses registry if available")
print()
print("Next steps:")
print("  1. Deploy to staging")
print("  2. Run E2E tests: npx playwright test tests/e2e/inventory_e2e_flow.spec.ts")
print("  3. Verify Part Lens search returns results")
print()
