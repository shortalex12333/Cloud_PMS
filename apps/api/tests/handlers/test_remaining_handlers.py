"""
Unit tests for remaining Phase 4 handlers:
  - certificate_handler.py
  - document_handler.py
  - handover_handler.py
  - shopping_handler.py
  - pm_handler.py

Tests import from routes.handlers.* which must exist for tests to pass.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from routes.handlers.certificate_handler import HANDLERS as CERT_HANDLERS
from routes.handlers.document_handler import HANDLERS as DOC_HANDLERS
from routes.handlers.handover_handler import HANDLERS as HAND_HANDLERS
from routes.handlers.shopping_handler import HANDLERS as SHOP_HANDLERS
from routes.handlers.pm_handler import HANDLERS as PM_HANDLERS


# ============================================================================
# SHARED HELPERS
# ============================================================================

def make_db(rows=None):
    """Stub Supabase client — returns rows on any .execute() call."""
    db = MagicMock()
    rows = rows or [{"id": "item-1", "status": "draft"}]
    # update chains
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    # insert chains (ledger)
    db.table.return_value.insert.return_value.execute.return_value.data = rows
    # select chains (maybe_single)
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = rows[0] if rows else None
    # select chains (single)
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = rows[0] if rows else None
    # select chains (limit)
    db.table.return_value.select.return_value.eq.return_value.or_.return_value.limit.return_value.execute.return_value.data = rows
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = rows
    # select chains (all - for export_handover items)
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = rows
    # delete chains
    db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    return db


def make_db_empty():
    """Stub Supabase client — returns empty data."""
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.table.return_value.insert.return_value.execute.return_value.data = []
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    db.table.return_value.select.return_value.eq.return_value.or_.return_value.limit.return_value.execute.return_value.data = []
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    return db


def base_ctx():
    return {"yacht_id": "y-1"}


def base_uc(role="captain"):
    return {"role": role, "tenant_key_alias": "y85fe1119", "department": "engineering", "name": "Test User"}


# ============================================================================
# CERTIFICATE HANDLER — REGISTRY
# ============================================================================

class TestCertificateRegistry:
    def test_all_certificate_actions_registered(self):
        expected = [
            "add_certificate", "renew_certificate", "add_service_contract", "record_contract_claim",
            "create_vessel_certificate", "create_crew_certificate", "update_certificate",
            "link_document_to_certificate", "supersede_certificate",
        ]
        for name in expected:
            assert name in CERT_HANDLERS, f"Action '{name}' not in CERT_HANDLERS"


# ============================================================================
# CERTIFICATE HANDLER — BLOCKED ACTIONS
# ============================================================================

class TestCertificateBlocked:
    @pytest.mark.asyncio
    async def test_add_certificate_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["add_certificate"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_renew_certificate_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["renew_certificate"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_add_service_contract_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["add_service_contract"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_record_contract_claim_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["record_contract_claim"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501


# ============================================================================
# CERTIFICATE HANDLER — V2 ACTIONS (RBAC)
# ============================================================================

class TestCertificateV2Rbac:
    @pytest.mark.asyncio
    async def test_create_vessel_certificate_rbac_denied(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["create_vessel_certificate"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(role="crew"), db_client=make_db(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_supersede_certificate_requires_signature(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["supersede_certificate"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(role="captain"), db_client=make_db(),
            )
        assert exc.value.status_code == 400
        assert "signature" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_link_document_requires_document_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await CERT_HANDLERS["link_document_to_certificate"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(role="captain"), db_client=make_db(),
            )
        assert exc.value.status_code == 400


# ============================================================================
# DOCUMENT HANDLER — REGISTRY
# ============================================================================

class TestDocumentRegistry:
    def test_all_document_actions_registered(self):
        expected = [
            "view_related_documents", "view_document_section",
            "upload_document", "update_document", "delete_document",
            "add_document_tags", "get_document_url", "list_documents",
        ]
        for name in expected:
            assert name in DOC_HANDLERS, f"Action '{name}' not in DOC_HANDLERS"


# ============================================================================
# DOCUMENT HANDLER — INLINE ACTIONS
# ============================================================================

class TestDocumentInline:
    @pytest.mark.asyncio
    async def test_view_related_documents_missing_entity_type(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await DOC_HANDLERS["view_related_documents"](
                payload={"entity_id": "e-1"}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_view_related_documents_missing_entity_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await DOC_HANDLERS["view_related_documents"](
                payload={"entity_type": "fault"}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_view_related_documents_success(self):
        result = await DOC_HANDLERS["view_related_documents"](
            payload={"entity_type": "fault", "entity_id": "f-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
        assert result["status"] == "success"
        assert "documents" in result

    @pytest.mark.asyncio
    async def test_view_document_section_missing_document_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await DOC_HANDLERS["view_document_section"](
                payload={"section_id": "s-1"}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_view_document_section_missing_section_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await DOC_HANDLERS["view_document_section"](
                payload={"document_id": "d-1"}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_view_document_section_success(self):
        db = make_db([{"id": "d-1", "filename": "test.pdf", "metadata": {"sections": {"intro": {"content": "hello"}}}}])
        result = await DOC_HANDLERS["view_document_section"](
            payload={"document_id": "d-1", "section_id": "intro"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=db,
        )
        assert result["status"] == "success"
        assert result["document_id"] == "d-1"


# ============================================================================
# DOCUMENT HANDLER — V2 RBAC
# ============================================================================

class TestDocumentV2Rbac:
    @pytest.mark.asyncio
    async def test_delete_document_rbac_denied_for_crew(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await DOC_HANDLERS["delete_document"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(role="crew"), db_client=make_db(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_document_url_rbac_allowed_for_crew(self):
        """crew role should be allowed for get_document_url."""
        # Patch the lazy import target (handlers.document_handlers module)
        with patch("handlers.document_handlers.get_document_handlers") as mock_get:
            mock_fn = AsyncMock(return_value={"status": "success"})
            mock_get.return_value = {"get_document_url": mock_fn}
            result = await DOC_HANDLERS["get_document_url"](
                payload={"document_id": "d-1"}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(role="crew"), db_client=make_db(),
            )
            assert result["status"] == "success"


# ============================================================================
# HANDOVER HANDLER — REGISTRY
# ============================================================================

class TestHandoverRegistry:
    def test_all_handover_actions_registered(self):
        expected = [
            "create_handover", "acknowledge_handover", "update_handover",
            "delete_handover", "filter_handover",
            "add_to_handover", "add_document_to_handover",
            "add_predictive_insight_to_handover", "edit_handover_section",
            "export_handover", "regenerate_handover_summary",
        ]
        for name in expected:
            assert name in HAND_HANDLERS, f"Action '{name}' not in HAND_HANDLERS"


# ============================================================================
# HANDOVER HANDLER — BLOCKED ACTIONS
# ============================================================================

class TestHandoverBlocked:
    @pytest.mark.asyncio
    async def test_create_handover_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["create_handover"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_delete_handover_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["delete_handover"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501


# ============================================================================
# HANDOVER HANDLER — LIVE ACTIONS
# ============================================================================

class TestHandoverLive:
    @pytest.mark.asyncio
    async def test_add_to_handover_short_summary_400(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["add_to_handover"](
                payload={"summary": "short"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_document_to_handover_missing_handover_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["add_document_to_handover"](
                payload={"document_id": "d-1"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_document_to_handover_missing_document_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["add_document_to_handover"](
                payload={"handover_id": "h-1"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_document_to_handover_success(self):
        db = make_db([{"id": "h-1"}])
        result = await HAND_HANDLERS["add_document_to_handover"](
            payload={"handover_id": "h-1", "document_id": "d-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=db,
        )
        assert result["status"] == "success"
        assert result["handover_id"] == "h-1"

    @pytest.mark.asyncio
    async def test_add_predictive_insight_missing_handover_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["add_predictive_insight_to_handover"](
                payload={"insight_text": "some insight"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_predictive_insight_missing_text(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["add_predictive_insight_to_handover"](
                payload={"handover_id": "h-1"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_predictive_insight_success(self):
        db = make_db([{"id": "h-1", "metadata": {"predictive_insights": []}}])
        result = await HAND_HANDLERS["add_predictive_insight_to_handover"](
            payload={"handover_id": "h-1", "insight_text": "Engine temp trending up"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=db,
        )
        assert result["status"] == "success"
        assert result["insights_count"] == 1

    @pytest.mark.asyncio
    async def test_edit_handover_section_missing_handover_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["edit_handover_section"](
                payload={"section_name": "deck"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_edit_handover_section_missing_section_name(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["edit_handover_section"](
                payload={"handover_id": "h-1"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_edit_handover_section_success(self):
        db = make_db([{"id": "h-1", "metadata": {"sections": {}}}])
        result = await HAND_HANDLERS["edit_handover_section"](
            payload={"handover_id": "h-1", "section_name": "deck", "content": "All good"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=db,
        )
        assert result["status"] == "success"
        assert result["section_name"] == "deck"

    @pytest.mark.asyncio
    async def test_export_handover_missing_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["export_handover"](
                payload={},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_export_handover_success(self):
        db = make_db([{"id": "h-1", "metadata": {}}])
        result = await HAND_HANDLERS["export_handover"](
            payload={"handover_id": "h-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=db,
        )
        assert result["status"] == "success"
        assert "handover" in result

    @pytest.mark.asyncio
    async def test_regenerate_handover_summary_missing_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await HAND_HANDLERS["regenerate_handover_summary"](
                payload={},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_regenerate_handover_summary_success(self):
        db = make_db([{"id": "h-1", "metadata": {}}])
        result = await HAND_HANDLERS["regenerate_handover_summary"](
            payload={"handover_id": "h-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=db,
        )
        assert result["status"] == "success"


# ============================================================================
# SHOPPING HANDLER — REGISTRY
# ============================================================================

class TestShoppingRegistry:
    def test_all_shopping_actions_registered(self):
        expected = [
            "delete_shopping_item",
            "create_shopping_list_item", "approve_shopping_list_item",
            "reject_shopping_list_item", "promote_candidate_to_part",
            "view_shopping_list_history", "mark_shopping_list_ordered",
        ]
        for name in expected:
            assert name in SHOP_HANDLERS, f"Action '{name}' not in SHOP_HANDLERS"


# ============================================================================
# SHOPPING HANDLER — delete_shopping_item
# ============================================================================

class TestDeleteShoppingItem:
    @pytest.mark.asyncio
    async def test_delete_rbac_denied(self):
        result = await SHOP_HANDLERS["delete_shopping_item"](
            payload={"item_id": "00000000-0000-0000-0000-000000000001"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="crew"), db_client=make_db(),
        )
        assert result["success"] is False
        assert result["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_delete_missing_item_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await SHOP_HANDLERS["delete_shopping_item"](
                payload={},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_invalid_uuid(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await SHOP_HANDLERS["delete_shopping_item"](
                payload={"item_id": "REAL_SHOPPING_ITEM_ID"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400
        assert "UUID" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_delete_success(self):
        result = await SHOP_HANDLERS["delete_shopping_item"](
            payload={"item_id": "00000000-0000-0000-0000-000000000001"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await SHOP_HANDLERS["delete_shopping_item"](
                payload={"item_id": "00000000-0000-0000-0000-000000000001"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db_empty(),
            )
        assert exc.value.status_code == 404


# ============================================================================
# SHOPPING HANDLER — mark_shopping_list_ordered
# ============================================================================

class TestMarkShoppingListOrdered:
    @pytest.mark.asyncio
    async def test_mark_ordered_rbac_denied(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await SHOP_HANDLERS["mark_shopping_list_ordered"](
                payload={"item_id": "item-1"},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(role="crew"), db_client=make_db(),
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_mark_ordered_missing_item_id(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await SHOP_HANDLERS["mark_shopping_list_ordered"](
                payload={},
                context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_mark_ordered_success(self):
        result = await SHOP_HANDLERS["mark_shopping_list_ordered"](
            payload={"item_id": "item-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_mark_ordered_update_fails(self):
        result = await SHOP_HANDLERS["mark_shopping_list_ordered"](
            payload={"item_id": "item-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db_empty(),
        )
        assert result["status"] == "error"
        assert result["error_code"] == "UPDATE_FAILED"


# ============================================================================
# SHOPPING HANDLER — LENS V1 RBAC
# ============================================================================

class TestShoppingListLensRbac:
    @pytest.mark.asyncio
    async def test_create_shopping_list_item_rbac_denied_for_deckhand(self):
        """deckhand is not in create_shopping_list_item allowed roles."""
        result = await SHOP_HANDLERS["create_shopping_list_item"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="deckhand"), db_client=make_db(),
        )
        assert result["success"] is False
        assert result["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_approve_shopping_list_item_rbac_denied_for_crew(self):
        """crew is not in approve_shopping_list_item allowed roles."""
        result = await SHOP_HANDLERS["approve_shopping_list_item"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="crew"), db_client=make_db(),
        )
        assert result["success"] is False
        assert result["code"] == "FORBIDDEN"


# ============================================================================
# PM HANDLER — REGISTRY
# ============================================================================

class TestPmRegistry:
    def test_all_pm_actions_registered(self):
        expected = [
            "create_pm_schedule", "record_pm_completion", "defer_pm_task",
            "update_pm_schedule", "view_pm_due_list",
        ]
        for name in expected:
            assert name in PM_HANDLERS, f"Action '{name}' not in PM_HANDLERS"


# ============================================================================
# PM HANDLER — BLOCKED ACTIONS
# ============================================================================

class TestPmBlocked:
    @pytest.mark.asyncio
    async def test_create_pm_schedule_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await PM_HANDLERS["create_pm_schedule"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_record_pm_completion_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await PM_HANDLERS["record_pm_completion"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_defer_pm_task_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await PM_HANDLERS["defer_pm_task"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_update_pm_schedule_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await PM_HANDLERS["update_pm_schedule"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501

    @pytest.mark.asyncio
    async def test_view_pm_due_list_blocked(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await PM_HANDLERS["view_pm_due_list"](
                payload={}, context=base_ctx(), yacht_id="y-1", user_id="u-1",
                user_context=base_uc(), db_client=make_db(),
            )
        assert exc.value.status_code == 501
