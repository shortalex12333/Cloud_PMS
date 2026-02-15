"""
Pytest configuration for API tests.

Handles conditional test collection to prevent module-level errors
when required environment variables are not set.
"""

import os

# Files that require SUPABASE_SERVICE_KEY at collection time
# These create Supabase clients at module level or in fixtures
INTEGRATION_TEST_FILES = [
    "test_equipment_lens_v2.py",
    "test_phase15_database_mutations.py",
    "test_email_transport.py",
    "test_message_render.py",
    "test_fault_lens_v1_evidence.py",
]


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests requiring live database"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (no external dependencies)"
    )


def pytest_ignore_collect(collection_path, config):
    """
    Skip collection of integration test files when SUPABASE_SERVICE_KEY is not set.

    This prevents ImportError during collection when test files create
    Supabase clients at module level.
    """
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # If service key is set and looks valid, allow collection
    if service_key and len(service_key) > 100:
        return False

    # Skip integration test files that require service key
    for filename in INTEGRATION_TEST_FILES:
        if str(collection_path).endswith(filename):
            return True

    return False
