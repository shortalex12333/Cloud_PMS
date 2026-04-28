"""
Entity Lens Endpoint Integration Tests
=======================================

Tests GET /v1/entity/{type}/{id} for all 12 entity types.

Three tests per endpoint:
  200 — found, returns correct shape
  404 — nil UUID, returns not found
  401 — no token, auth rejected

LAW 17: in-memory testing via httpx.AsyncClient (no uvicorn required).
Auth injected via app.dependency_overrides; DB mocked via patch.
"""

import os
import sys
import uuid
import pytest
import pytest_asyncio
import httpx
from typing import Dict, Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_service import app
from middleware.auth import get_authenticated_user

# ── Constants ─────────────────────────────────────────────────────────────────

TEST_YACHT_A_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
NULL_UUID = "00000000-0000-0000-0000-000000000000"

_AUTH = {
    "user_id": TEST_USER_A_ID,
    "email": "test@yacht.test",
    "yacht_id": TEST_YACHT_A_ID,
    "org_id": TEST_YACHT_A_ID,
    "tenant_key_alias": "y85fe111",
    "role": "chief_engineer",
    "yacht_name": "M/Y Test",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Unauthenticated in-memory client (for 401 tests)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as c:
        yield c


@pytest_asyncio.fixture
async def auth_client():
    """
    Authenticated in-memory client.

    Overrides get_authenticated_user to return test auth context.
    Override is cleared after each test.
    """
    async def _mock_auth():
        return _AUTH

    app.dependency_overrides[get_authenticated_user] = _mock_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as c:
        yield c
    app.dependency_overrides.clear()


def _supabase_mock(main_data, sub_data=None):
    """
    Build a Supabase mock that returns main_data for .maybe_single()/.single()
    and sub_data (default []) for direct .execute() sub-queries.

    Handles unlimited .eq() chaining, .is_(), .in_(), .order(), .limit().
    """
    m = MagicMock()

    main_r = MagicMock()
    main_r.data = main_data

    sub_r = MagicMock()
    sub_r.data = sub_data if sub_data is not None else []

    chain = MagicMock()
    chain.maybe_single.return_value.execute.return_value = main_r
    chain.single.return_value.execute.return_value = main_r
    chain.execute.return_value = sub_r
    chain.is_.return_value.maybe_single.return_value.execute.return_value = main_r
    chain.order.return_value.execute.return_value = sub_r
    chain.order.return_value.limit.return_value.execute.return_value = sub_r
    chain.limit.return_value.execute.return_value = sub_r
    chain.in_.return_value.maybe_single.return_value.execute.return_value = sub_r

    # Allow infinite .eq() chaining
    chain.eq.return_value = chain

    m.table.return_value.select.return_value.eq.return_value = chain
    return m


# ── Work Order ─────────────────────────────────────────────────────────────────

WO_DATA = {
    "id": str(uuid.uuid4()),
    "title": "Replace fuel filter",
    "status": "planned",
    "wo_number": "WO-001",
    "priority": "high",
    "description": "Replace primary fuel filter",
    "equipment_id": None,
    "equipment_name": None,
    "assigned_to": None,
    "assigned_to_name": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "due_date": None,
    "completed_at": None,
    "completed_by": None,
    "fault_id": None,
}


class TestWorkOrderEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        wo_id = WO_DATA["id"]
        mock_sb = _supabase_mock(WO_DATA)
        with patch("routes.entity_routes.get_supabase_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/work_order/{wo_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == wo_id
        assert data["status"] == "planned"
        assert data["title"] == "Replace fuel filter"
        assert "available_actions" in data

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_supabase_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/work_order/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/work_order/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Fault ──────────────────────────────────────────────────────────────────────

FAULT_DATA = {
    "id": str(uuid.uuid4()),
    "title": "Engine overheating",
    "status": "open",
    "severity": "high",
    "description": "Main engine temperature exceeded threshold",
    "equipment_id": None,
    "equipment_name": None,
    "reported_at": "2026-01-01T00:00:00Z",
    "reporter": "Chief Engineer",
    "has_work_order": False,
    "ai_diagnosis": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class TestFaultEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        fault_id = FAULT_DATA["id"]
        mock_sb = _supabase_mock(FAULT_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/fault/{fault_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == fault_id
        assert data["status"] == "open"
        assert data["title"] == "Engine overheating"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/fault/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/fault/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Equipment ──────────────────────────────────────────────────────────────────

EQUIPMENT_DATA = {
    "id": str(uuid.uuid4()),
    "name": "Main Engine",
    "system_type": "Propulsion",
    "metadata": {"status": "operational", "category": "Engine"},
    "manufacturer": "Caterpillar",
    "model": "C18",
    "serial_number": "SN-12345",
    "location": "Engine Room",
    "criticality": "critical",
    "installed_date": "2020-01-01",
    "description": "Primary propulsion engine",
    "attention_flag": False,
    "attention_reason": None,
    "created_at": "2020-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class TestEquipmentEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        eq_id = EQUIPMENT_DATA["id"]
        mock_sb = _supabase_mock(EQUIPMENT_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/equipment/{eq_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == eq_id
        assert data["name"] == "Main Engine"
        assert data["status"] == "operational"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/equipment/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/equipment/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Part ───────────────────────────────────────────────────────────────────────

PART_DATA = {
    "id": str(uuid.uuid4()),
    "name": "Oil Filter",
    "part_number": "OF-001",
    "quantity_on_hand": 5,
    "minimum_quantity": 2,
    "location": "Store Room A",
    "metadata": {"unit_cost": 25.0, "supplier": "ACME Parts"},
    "category": "Consumables",
    "unit": "each",
    "manufacturer": "Fleetguard",
    "description": "Primary oil filter",
    "last_counted_at": None,
    "last_counted_by": None,
    "created_at": "2020-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class TestPartEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        part_id = PART_DATA["id"]
        mock_sb = _supabase_mock(PART_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/part/{part_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == part_id
        assert data["name"] == "Oil Filter"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/part/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/part/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Receiving ─────────────────────────────────────────────────────────────────

RECEIVING_DATA = {
    "id": str(uuid.uuid4()),
    "vendor_name": "Marine Parts Ltd",
    "vendor_reference": "INV-2026-001",
    "received_date": "2026-01-15",
    "status": "received",
    "total": 1250.00,
    "currency": "USD",
    "notes": "All items received in good condition",
    "received_by": TEST_USER_A_ID,
    "created_at": "2026-01-15T00:00:00Z",
    "updated_at": "2026-01-15T00:00:00Z",
}


class TestReceivingEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        rec_id = RECEIVING_DATA["id"]
        mock_sb = _supabase_mock(RECEIVING_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/receiving/{rec_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rec_id
        assert data["status"] == "received"
        assert data["vendor_name"] == "Marine Parts Ltd"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/receiving/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/receiving/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Certificate ───────────────────────────────────────────────────────────────

CERTIFICATE_DATA = {
    "id": str(uuid.uuid4()),
    "certificate_name": "Safety Management Certificate",
    "certificate_type": "ISM",
    "issuing_authority": "Lloyd's Register",
    "issue_date": "2024-01-01",
    "expiry_date": "2029-01-01",
    "status": "active",
    "certificate_number": "CERT-001",
    "properties": {},
    "created_at": "2024-01-01T00:00:00Z",
    "yacht_id": TEST_YACHT_A_ID,
}


class TestCertificateEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        cert_id = CERTIFICATE_DATA["id"]
        mock_sb = _supabase_mock(CERTIFICATE_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/certificate/{cert_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == cert_id
        assert data["name"] == "Safety Management Certificate"
        assert data["domain"] == "vessel"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/certificate/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/certificate/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Document ──────────────────────────────────────────────────────────────────

DOCUMENT_DATA = {
    "id": str(uuid.uuid4()),
    "filename": "engine_manual.pdf",
    "title": "Main Engine Manual",
    "description": "CAT C18 service manual",
    "content_type": "application/pdf",
    "storage_path": "/documents/engine_manual.pdf",
    "classification": "technical",
    "equipment_id": None,
    "equipment_name": None,
    "tags": ["engine", "manual"],
    "created_at": "2020-01-01T00:00:00Z",
    "created_by": TEST_USER_A_ID,
    "yacht_id": TEST_YACHT_A_ID,
    "deleted_at": None,
}


class TestDocumentEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        doc_id = DOCUMENT_DATA["id"]
        mock_sb = _supabase_mock(DOCUMENT_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/document/{doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert data["filename"] == "engine_manual.pdf"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/document/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/document/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Hours of Rest ─────────────────────────────────────────────────────────────

HOURS_DATA = {
    "id": str(uuid.uuid4()),
    "user_id": TEST_USER_A_ID,
    "record_date": "2026-01-15",
    "total_rest_hours": 10.5,
    "total_work_hours": 13.5,
    "is_daily_compliant": True,
    "weekly_rest_hours": 77.0,
    "daily_compliance_notes": None,
    "weekly_compliance_notes": None,
    "rest_periods": [{"id": "p1", "start_time": "2026-01-15T00:00:00", "end_time": "2026-01-15T06:00:00", "duration_hours": 6.0}],
    "yacht_id": TEST_YACHT_A_ID,
    "created_at": "2026-01-15T00:00:00Z",
    "updated_at": "2026-01-15T00:00:00Z",
}


class TestHoursOfRestEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        hor_id = HOURS_DATA["id"]
        mock_sb = _supabase_mock(HOURS_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/hours_of_rest/{hor_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == hor_id
        assert data["is_compliant"] is True
        assert isinstance(data["rest_periods"], list)

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/hours_of_rest/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/hours_of_rest/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Shopping List ─────────────────────────────────────────────────────────────

SHOPPING_DATA = {
    "id": str(uuid.uuid4()),
    "part_name": "Engine Oil 15W-40",
    "part_number": None,
    "manufacturer": None,
    "unit": "litres",
    "quantity_requested": 20,
    "urgency": "routine",
    "status": "pending",
    "required_by_date": None,
    "is_candidate_part": False,
    "created_by": TEST_USER_A_ID,
    "created_at": "2026-01-01T00:00:00Z",
    "yacht_id": TEST_YACHT_A_ID,
}


class TestShoppingListEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        item_id = SHOPPING_DATA["id"]
        mock_sb = _supabase_mock(SHOPPING_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/shopping_list/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == item_id
        assert data["status"] == "pending"
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/shopping_list/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/shopping_list/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Warranty ──────────────────────────────────────────────────────────────────
# No real test data in dev — 404 is the acceptable outcome.

class TestWarrantyEntity:

    @pytest.mark.asyncio
    async def test_404_no_test_data(self, auth_client):
        """Warranty 404 is acceptable — no test data in dev DB."""
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/warranty/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_200_when_data_exists(self, auth_client):
        warranty_data = {
            "id": str(uuid.uuid4()),
            "title": "Engine Warranty Claim",
            "claim_number": "WC-001",
            "vendor_name": "Caterpillar",
            "status": "open",
            "equipment_id": None,
            "fault_id": None,
            "work_order_id": None,
            "manufacturer": "Caterpillar",
            "part_number": None,
            "serial_number": None,
            "purchase_date": None,
            "warranty_expiry": "2027-01-01",
            "claimed_amount": 5000.0,
            "approved_amount": None,
            "currency": "USD",
            "description": "Engine failure under warranty",
            "claim_type": "parts",
            "created_at": "2026-01-01T00:00:00Z",
            "yacht_id": TEST_YACHT_A_ID,
        }
        wid = warranty_data["id"]
        mock_sb = _supabase_mock(warranty_data)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/warranty/{wid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == wid

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/warranty/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Handover Export ───────────────────────────────────────────────────────────

HANDOVER_DATA = {
    "id": str(uuid.uuid4()),
    "yacht_id": TEST_YACHT_A_ID,
    "review_status": "pending_review",
    "export_type": "handover",
    "export_status": "draft",
    "file_name": "handover_2026_01.pdf",
    "edited_content": {"sections": [{"title": "Open Work Orders", "items": []}]},
    "user_signature": None,
    "hod_signature": None,
    "exported_at": None,
    "created_at": "2026-01-01T00:00:00Z",
    "draft_id": None,
}


class TestHandoverExportEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        hid = HANDOVER_DATA["id"]
        mock_sb = _supabase_mock(HANDOVER_DATA)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/handover_export/{hid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == hid
        assert data["review_status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/handover_export/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/handover_export/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token


# ── Purchase Order ────────────────────────────────────────────────────────────

PO_DATA = {
    "id": str(uuid.uuid4()),
    "po_number": "PO-2026-001",
    "status": "sent",
    "supplier_name": "Marine Supplies Co",
    "order_date": "2026-01-10",
    "expected_delivery": "2026-01-20",
    "total_amount": 3500.00,
    "currency": "USD",
    "notes": "Urgent order for fuel filters",
    "created_at": "2026-01-10T00:00:00Z",
    "yacht_id": TEST_YACHT_A_ID,
}

PO_ITEMS = [
    {
        "id": str(uuid.uuid4()),
        "part_id": str(uuid.uuid4()),
        "name": "Fuel Filter",
        "quantity_ordered": 4,
        "quantity_received": 0,
        "unit_price": 875.00,
        "currency": "USD",
    }
]


class TestPurchaseOrderEntity:

    @pytest.mark.asyncio
    async def test_200_returns_correct_shape(self, auth_client):
        po_id = PO_DATA["id"]
        mock_sb = _supabase_mock(PO_DATA, sub_data=PO_ITEMS)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/purchase_order/{po_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == po_id
        assert data["status"] == "sent"
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_404_nil_uuid(self, auth_client):
        mock_sb = _supabase_mock(None)
        with patch("routes.entity_routes.get_tenant_client", return_value=mock_sb):
            resp = await auth_client.get(f"/v1/entity/purchase_order/{NULL_UUID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_401_no_token(self, client):
        resp = await client.get(f"/v1/entity/purchase_order/{NULL_UUID}")
        assert resp.status_code in (401, 422)  # 422 = required header missing (FastAPI), 401 = bad token
