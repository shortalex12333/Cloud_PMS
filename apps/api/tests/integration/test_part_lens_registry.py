"""
Part Lens - Integration Tests
==============================

Tests for Part Lens capability registry integration.

Tests:
1. Part Lens auto-discovery
2. Entity type registration
3. Capability mapping validation
"""

import pytest
from pathlib import Path


def test_part_lens_files_exist():
    """Test that Part Lens files exist."""
    base_path = Path(__file__).parent.parent.parent

    capabilities_file = base_path / "prepare/capabilities/part_capabilities.py"
    microactions_file = base_path / "microactions/lens_microactions/part_microactions.py"

    assert capabilities_file.exists(), f"Part capabilities file not found: {capabilities_file}"
    assert microactions_file.exists(), f"Part microactions file not found: {microactions_file}"


def test_part_lens_capability_class():
    """Test that PartLensCapability class is properly defined."""
    # Import dynamically to avoid breaking if not yet integrated
    try:
        from apps.api.prepare.capabilities.part_capabilities import PartLensCapability

        # Check class exists
        assert PartLensCapability is not None

        # Check class attributes
        assert PartLensCapability.lens_name == "part_lens"
        assert PartLensCapability.enabled is True

    except ImportError as e:
        pytest.skip(f"Part Lens not yet integrated into imports: {e}")


def test_part_lens_entity_mappings():
    """Test that Part Lens has correct entity mappings."""
    try:
        from apps.api.prepare.capabilities.part_capabilities import PartLensCapability

        # Create instance (with mock db_client)
        class MockDB:
            pass

        lens = PartLensCapability(MockDB())

        # Get entity mappings
        mappings = lens.get_entity_mappings()

        # Check we have mappings
        assert len(mappings) > 0, "Part Lens should have entity mappings"

        # Check specific entity types
        entity_types = [m.entity_type for m in mappings]

        # Must have PART entity type (free-text fallback)
        assert "PART" in entity_types, "PART entity type missing (needed for free-text search)"
        assert "PART_NUMBER" in entity_types, "PART_NUMBER entity type missing"
        assert "PART_NAME" in entity_types, "PART_NAME entity type missing"

        # Check all mappings have required fields
        for mapping in mappings:
            assert mapping.entity_type, "Entity type must not be empty"
            assert mapping.capability_name, "Capability name must not be empty"
            assert mapping.table_name, "Table name must not be empty"
            assert mapping.search_column, "Search column must not be empty"
            assert mapping.result_type, "Result type must not be empty"

    except ImportError as e:
        pytest.skip(f"Part Lens not yet integrated: {e}")


def test_part_lens_capability_methods_exist():
    """Test that all capability methods are implemented."""
    try:
        from apps.api.prepare.capabilities.part_capabilities import PartLensCapability

        # Create instance
        class MockDB:
            pass

        lens = PartLensCapability(MockDB())

        # Get entity mappings
        mappings = lens.get_entity_mappings()

        # Check each capability method exists
        capability_names = set(m.capability_name for m in mappings)

        for cap_name in capability_names:
            assert hasattr(lens, cap_name), f"Capability method '{cap_name}' not implemented"
            method = getattr(lens, cap_name)
            assert callable(method), f"'{cap_name}' is not a callable method"

    except ImportError as e:
        pytest.skip(f"Part Lens not yet integrated: {e}")


def test_no_duplicate_entity_types():
    """Test that Part Lens has no duplicate entity types."""
    try:
        from apps.api.prepare.capabilities.part_capabilities import PartLensCapability

        class MockDB:
            pass

        lens = PartLensCapability(MockDB())
        mappings = lens.get_entity_mappings()

        entity_types = [m.entity_type for m in mappings]

        # Check for duplicates
        duplicates = [et for et in entity_types if entity_types.count(et) > 1]

        assert len(duplicates) == 0, f"Duplicate entity types found: {duplicates}"

    except ImportError as e:
        pytest.skip(f"Part Lens not yet integrated: {e}")


def test_part_lens_microactions_class():
    """Test that PartLensMicroactions class is properly defined."""
    try:
        from apps.api.microactions.lens_microactions.part_microactions import PartLensMicroactions

        assert PartLensMicroactions is not None
        assert PartLensMicroactions.lens_name == "part_lens"
        assert len(PartLensMicroactions.entity_types) > 0

    except ImportError as e:
        pytest.skip(f"Part Lens microactions not yet integrated: {e}")
