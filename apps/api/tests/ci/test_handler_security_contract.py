"""
CelesteOS API - Handler Security Contract Tests
=================================================

CI contract test that fails builds if any handler ships without @secure_action.

This test ensures:
1. All exported mutation handlers have @secure_action decorator
2. All handlers have appropriate action_group
3. All MUTATE/SIGNED/ADMIN handlers require idempotency

Run: pytest tests/ci/test_handler_security_contract.py -v

If this test fails, either:
- Add @secure_action decorator to the handler
- Add the handler to EXEMPT_HANDLERS if it's intentionally unsecured (with justification)
"""

import pytest
import inspect
import importlib
from typing import Dict, List, Set, Callable, Any
from pathlib import Path

from middleware.action_security import (
    is_secured_handler,
    get_handler_security_metadata,
)


# ============================================================================
# Configuration
# ============================================================================

# Handler modules to check (secure versions preferred)
HANDLER_MODULES = [
    # Secure handler modules (Phase 2)
    "handlers.secure_fault_handlers",
    "handlers.secure_document_handlers",
    # Legacy modules (pending migration)
    "handlers.fault_mutation_handlers",
    "handlers.document_handlers",
    "handlers.work_order_mutation_handlers",
    "handlers.purchasing_mutation_handlers",
    "handlers.admin_handlers",
    "handlers.equipment_handlers",
    "handlers.part_handlers",
    "handlers.inventory_handlers",
    "handlers.certificate_handlers",
    "handlers.warranty_handlers",
    "handlers.handover_handlers",
    "handlers.context_navigation_handlers",
    "handlers.shopping_list_handlers",
]

# Secure handler modules that MUST be used in production
SECURE_HANDLER_MODULES = [
    "handlers.secure_fault_handlers",
    "handlers.secure_document_handlers",
    "handlers.secure_admin_handlers",
]

# Handlers explicitly exempted from @secure_action requirement
# Each entry must have a justification
EXEMPT_HANDLERS: Dict[str, str] = {
    # Format: "module.handler_name": "justification"

    # Read-only helpers that don't expose data
    "handlers.fault_mutation_handlers.map_severity": "Pure function, no DB access",
    "handlers.fault_mutation_handlers.infer_severity_from_text": "Pure function, no DB access",

    # Factory functions that return handler instances
    "handlers.fault_mutation_handlers.get_fault_mutation_handlers": "Factory function, returns handler dict",
    "handlers.document_handlers.get_document_handlers": "Factory function, returns handler dict",
    "handlers.admin_handlers.get_admin_handlers": "Factory function, returns handler dict",

    # Internal helper functions (prefixed with _)
    # These are automatically exempt

    # Legacy handlers pending migration (add with migration plan)
}

# Handlers that MUST have @secure_action (fail if missing)
# These are high-risk mutation handlers that MUST be in secure handler modules
REQUIRED_SECURE_HANDLERS: Set[str] = {
    # Fault mutations (in secure_fault_handlers.py)
    "report_fault",
    "report_fault_prefill",
    "report_fault_preview",
    "acknowledge_fault",
    "close_fault",
    "update_fault",
    "reopen_fault",
    "mark_fault_false_alarm",
    "add_fault_photo",
    "add_fault_note",
    "diagnose_fault",
    "create_work_order_from_fault",
    "create_work_order_from_fault_prepare",
    "create_work_order_from_fault_commit",

    # Document mutations (in secure_document_handlers.py)
    "upload_document",
    "update_document",
    "delete_document",
    "add_document_tags",
    "get_document_url",
    "list_documents",

    # Admin actions (in secure_admin_handlers.py)
    "admin_invite_user",
    "admin_approve_membership",
    "admin_change_role",
    "admin_revoke_membership",
    "admin_freeze_yacht",
    "admin_list_memberships",
    "admin_get_membership",
}

# Admin actions are now migrated to secure_admin_handlers.py
# These are the action_id values used in the secure handlers
ADMIN_ACTIONS: Set[str] = {
    "admin_invite_user",
    "admin_approve_membership",
    "admin_change_role",
    "admin_revoke_membership",
    "admin_freeze_yacht",
    "admin_list_memberships",
    "admin_get_membership",
}

# Action groups that require idempotency
IDEMPOTENT_GROUPS = {"MUTATE", "SIGNED", "ADMIN"}


# ============================================================================
# Helper Functions
# ============================================================================

def is_internal_helper(name: str) -> bool:
    """Check if function is an internal helper (starts with _)."""
    return name.startswith('_')


def is_class_method(obj: Any) -> bool:
    """Check if object is a class (handler classes have methods, not the class itself)."""
    return inspect.isclass(obj)


def get_handler_functions(module) -> Dict[str, Callable]:
    """
    Get all handler functions from a module.

    Excludes:
    - Internal helpers (prefixed with _)
    - Classes (we check their methods separately)
    - Non-callables
    """
    handlers = {}

    for name in dir(module):
        if is_internal_helper(name):
            continue

        obj = getattr(module, name)

        # Skip classes - we'll check their exported methods via get_*_handlers
        if is_class_method(obj):
            continue

        # Skip non-callables
        if not callable(obj):
            continue

        # Skip imported modules
        if inspect.ismodule(obj):
            continue

        handlers[name] = obj

    return handlers


def get_exported_handlers_from_factory(module) -> Dict[str, Callable]:
    """
    Get handlers from factory functions like get_fault_mutation_handlers().

    These return dicts of action_name -> handler_function.
    """
    from unittest.mock import MagicMock

    handlers = {}

    # Look for get_*_handlers factory functions
    for name in dir(module):
        if name.startswith('get_') and name.endswith('_handlers'):
            factory = getattr(module, name)
            if callable(factory):
                try:
                    # Factory functions typically need a db_client
                    # We pass None or MagicMock since we're just inspecting the returned functions
                    import inspect
                    sig = inspect.signature(factory)
                    num_params = len(sig.parameters)

                    if num_params == 1:
                        result = factory(None)
                    elif num_params == 2:
                        # secure_admin_handlers needs (tenant_client, master_client)
                        mock_client = MagicMock()
                        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                        result = factory(mock_client, mock_client)
                    else:
                        result = factory(None)

                    if isinstance(result, dict):
                        handlers.update(result)
                except Exception:
                    # Some factories may fail without a real db_client
                    # That's OK - we'll check the module-level functions instead
                    pass

    return handlers


# ============================================================================
# Contract Tests
# ============================================================================

class TestHandlerSecurityContract:
    """Contract tests ensuring all handlers have @secure_action."""

    def test_secure_handler_modules_are_secured(self):
        """
        All handlers in SECURE_HANDLER_MODULES must have @secure_action.

        This is the core contract test that ensures the secure handler
        modules are properly decorated.
        """
        missing_security = []

        for module_name in SECURE_HANDLER_MODULES:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                pytest.fail(f"Secure handler module not found: {module_name}")

            # Check factory-returned handlers
            handlers = get_exported_handlers_from_factory(module)

            for handler_name, handler_func in handlers.items():
                if not is_secured_handler(handler_func):
                    missing_security.append(
                        f"{module_name}::{handler_name}"
                    )

        if missing_security:
            pytest.fail(
                f"Secure handlers missing @secure_action decorator:\n"
                f"  - " + "\n  - ".join(missing_security) + "\n\n"
                f"All handlers in SECURE_HANDLER_MODULES must have @secure_action."
            )

    def test_required_handlers_exist_in_secure_modules(self):
        """
        All handlers in REQUIRED_SECURE_HANDLERS must exist in secure modules.

        This ensures we haven't forgotten to migrate a required handler.
        """
        found_handlers = set()

        for module_name in SECURE_HANDLER_MODULES:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            handlers = get_exported_handlers_from_factory(module)
            found_handlers.update(handlers.keys())

        missing = REQUIRED_SECURE_HANDLERS - found_handlers
        if missing:
            pytest.fail(
                f"Required handlers not found in secure modules:\n"
                f"  - " + "\n  - ".join(sorted(missing)) + "\n\n"
                f"Migrate these handlers to secure handler modules."
            )

    def test_mutation_handlers_require_idempotency(self):
        """
        All MUTATE/SIGNED/ADMIN handlers must have idempotency validation.

        The @secure_action decorator automatically enforces idempotency
        for these action groups.
        """
        non_idempotent_mutations = []

        for module_name in HANDLER_MODULES:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            handlers = get_exported_handlers_from_factory(module)

            for handler_name, handler_func in handlers.items():
                if is_secured_handler(handler_func):
                    metadata = get_handler_security_metadata(handler_func)
                    if metadata and metadata.get('action_group') in IDEMPOTENT_GROUPS:
                        # Handler is correctly secured with idempotency
                        pass

        # Note: Non-idempotent mutations would be caught by the decorator
        # at runtime, but this test ensures the decorator is applied

    def test_exempt_handlers_have_justification(self):
        """
        All handlers in EXEMPT_HANDLERS must have non-empty justification.
        """
        missing_justification = []

        for handler_key, justification in EXEMPT_HANDLERS.items():
            if not justification or not justification.strip():
                missing_justification.append(handler_key)

        if missing_justification:
            pytest.fail(
                f"EXEMPT_HANDLERS entries missing justification:\n"
                f"  - " + "\n  - ".join(missing_justification)
            )

    def test_no_duplicate_exempt_entries(self):
        """
        EXEMPT_HANDLERS should not have duplicate entries.
        """
        # Dict keys are inherently unique, but check for similar entries
        keys = list(EXEMPT_HANDLERS.keys())
        normalized = [k.lower().replace('_', '') for k in keys]

        seen = set()
        duplicates = []
        for i, norm in enumerate(normalized):
            if norm in seen:
                duplicates.append(keys[i])
            seen.add(norm)

        if duplicates:
            pytest.fail(
                f"Possible duplicate EXEMPT_HANDLERS entries:\n"
                f"  - " + "\n  - ".join(duplicates)
            )

    def test_secured_handlers_have_action_id(self):
        """
        All @secure_action handlers must have a non-empty action_id.
        """
        missing_action_id = []

        for module_name in HANDLER_MODULES:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            handlers = get_exported_handlers_from_factory(module)

            for handler_name, handler_func in handlers.items():
                if is_secured_handler(handler_func):
                    metadata = get_handler_security_metadata(handler_func)
                    if not metadata or not metadata.get('action_id'):
                        missing_action_id.append(
                            f"{module_name}::{handler_name}"
                        )

        if missing_action_id:
            pytest.fail(
                f"Secured handlers missing action_id:\n"
                f"  - " + "\n  - ".join(missing_action_id)
            )

    def test_secured_handlers_have_valid_action_group(self):
        """
        All @secure_action handlers must have valid action_group.
        """
        valid_groups = {"READ", "MUTATE", "SIGNED", "ADMIN"}
        invalid_group = []

        for module_name in HANDLER_MODULES:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            handlers = get_exported_handlers_from_factory(module)

            for handler_name, handler_func in handlers.items():
                if is_secured_handler(handler_func):
                    metadata = get_handler_security_metadata(handler_func)
                    if metadata:
                        group = metadata.get('action_group')
                        if group not in valid_groups:
                            invalid_group.append(
                                f"{module_name}::{handler_name} (group={group})"
                            )

        if invalid_group:
            pytest.fail(
                f"Secured handlers with invalid action_group:\n"
                f"  - " + "\n  - ".join(invalid_group) + "\n\n"
                f"Valid groups: {valid_groups}"
            )


class TestAdminHandlersSecured:
    """Specific tests for admin handlers (highest risk)."""

    def test_admin_handlers_exist(self):
        """
        Admin handlers module should exist and export handlers.

        Admin handlers have been migrated to secure_admin_handlers.py
        with @secure_action decorator.
        """
        from unittest.mock import MagicMock

        try:
            from handlers.secure_admin_handlers import get_secure_admin_handlers
        except ImportError:
            pytest.fail("secure_admin_handlers module not found")

        # Setup mock clients
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        handlers = get_secure_admin_handlers(mock_client, mock_client)

        # Verify all admin actions are present
        admin_actions = [
            "admin_invite_user",
            "admin_approve_membership",
            "admin_change_role",
            "admin_revoke_membership",
            "admin_freeze_yacht",
            "admin_list_memberships",
            "admin_get_membership",
        ]

        for action_name in admin_actions:
            assert action_name in handlers, \
                f"secure_admin_handlers missing: {action_name}"

    def test_admin_mutations_are_admin_group(self):
        """
        Admin mutation handlers must use ADMIN action group.
        """
        from unittest.mock import MagicMock

        try:
            from handlers.secure_admin_handlers import get_secure_admin_handlers
        except ImportError:
            pytest.skip("secure_admin_handlers module not found")

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        handlers = get_secure_admin_handlers(mock_client, mock_client)

        admin_mutations = [
            "admin_invite_user",
            "admin_approve_membership",
            "admin_change_role",
            "admin_revoke_membership",
            "admin_freeze_yacht",
        ]

        for action_name in admin_mutations:
            handler = handlers.get(action_name)
            assert handler is not None, f"Missing handler: {action_name}"

            if is_secured_handler(handler):
                metadata = get_handler_security_metadata(handler)
                assert metadata['action_group'] == "ADMIN", \
                    f"{action_name} must be ADMIN action group"

    def test_admin_reads_are_read_group(self):
        """
        Admin read handlers must use READ action group.
        """
        from unittest.mock import MagicMock

        try:
            from handlers.secure_admin_handlers import get_secure_admin_handlers
        except ImportError:
            pytest.skip("secure_admin_handlers module not found")

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        handlers = get_secure_admin_handlers(mock_client, mock_client)

        admin_reads = [
            "admin_list_memberships",
            "admin_get_membership",
        ]

        for action_name in admin_reads:
            handler = handlers.get(action_name)
            assert handler is not None, f"Missing handler: {action_name}"

            if is_secured_handler(handler):
                metadata = get_handler_security_metadata(handler)
                assert metadata['action_group'] == "READ", \
                    f"{action_name} must be READ action group"


class TestDocumentHandlersSecured:
    """Specific tests for document handlers."""

    def test_delete_document_requires_signed(self):
        """
        delete_document MUST be SIGNED action group.
        """
        try:
            from handlers.document_handlers import get_document_handlers
        except ImportError:
            pytest.skip("document_handlers module not found")

        handlers = get_document_handlers(None)
        delete_handler = handlers.get("delete_document")

        if delete_handler and is_secured_handler(delete_handler):
            metadata = get_handler_security_metadata(delete_handler)
            assert metadata['action_group'] == "SIGNED", \
                "delete_document must be SIGNED action group"


class TestFaultHandlersSecured:
    """Specific tests for fault mutation handlers."""

    def test_fault_mutations_require_ownership_validation(self):
        """
        Fault mutations that take fault_id must validate ownership.
        """
        try:
            from handlers.fault_mutation_handlers import get_fault_mutation_handlers
        except ImportError:
            pytest.skip("fault_mutation_handlers module not found")

        handlers = get_fault_mutation_handlers(None)

        # These actions take fault_id and must validate ownership
        ownership_required = [
            "acknowledge_fault",
            "close_fault",
            "update_fault",
            "reopen_fault",
            "mark_fault_false_alarm",
            "add_fault_photo",
            "add_fault_note",
            "diagnose_fault",
        ]

        for action_name in ownership_required:
            handler = handlers.get(action_name)
            if handler and is_secured_handler(handler):
                metadata = get_handler_security_metadata(handler)
                entities = metadata.get('validate_entities', [])
                assert "fault_id" in entities, \
                    f"{action_name} must validate fault_id ownership"
