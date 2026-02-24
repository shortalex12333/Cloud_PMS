# Integration Example: Create Work Order

This document shows how to implement a complete two-phase mutation endpoint using the prefill engine.

## Complete Implementation

### 1. Define Field Metadata

```python
# apps/api/mutations/work_orders/field_metadata.py

from common.field_metadata import FieldMetadata

WORK_ORDER_FIELD_METADATA = {
    # CONTEXT fields
    "yacht_id": FieldMetadata(
        name="yacht_id",
        classification="CONTEXT",
    ),
    "created_by": FieldMetadata(
        name="created_by",
        classification="CONTEXT",
    ),

    # BACKEND_AUTO fields
    "id": FieldMetadata(
        name="id",
        classification="BACKEND_AUTO",
    ),
    "title": FieldMetadata(
        name="title",
        classification="BACKEND_AUTO",
        auto_populate_from="equipment",
        compose_template="{equipment} - {symptom}",
    ),
    "created_at": FieldMetadata(
        name="created_at",
        classification="BACKEND_AUTO",
    ),

    # REQUIRED fields
    "equipment_id": FieldMetadata(
        name="equipment_id",
        classification="REQUIRED",
        auto_populate_from="equipment",
        lookup_required=True,
        description="Equipment UUID",
    ),

    # OPTIONAL fields
    "priority": FieldMetadata(
        name="priority",
        classification="OPTIONAL",
        auto_populate_from="query_text",
        value_map={
            "urgent": "critical",
            "asap": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        },
        default="medium",
        options=["low", "medium", "high", "critical"],
    ),
    "wo_type": FieldMetadata(
        name="wo_type",
        classification="OPTIONAL",
        default="corrective",
        options=["corrective", "preventive", "predictive", "emergency", "project"],
    ),
    "description": FieldMetadata(
        name="description",
        classification="OPTIONAL",
        auto_populate_from="query_text",
    ),
}
```

### 2. Create /prepare Endpoint

```python
# apps/api/routes/work_order_routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from integrations.supabase import get_supabase_client
from middleware.auth import get_current_user
from extraction.entity_extractor import extract_entities
from common.prefill_engine import build_mutation_preview
from mutations.work_orders.field_metadata import WORK_ORDER_FIELD_METADATA

router = APIRouter()


class PrepareWorkOrderRequest(BaseModel):
    """Request to prepare work order mutation."""
    query_text: str
    yacht_id: str
    entities: Optional[Dict[str, Any]] = None  # Optional pre-extracted entities


class PrepareWorkOrderResponse(BaseModel):
    """Response from prepare endpoint."""
    preview: Dict[str, Any]
    missing_required: List[str]
    warnings: List[str]
    dropdown_options: Dict[str, List[Dict[str, Any]]]
    ready_to_commit: bool
    extracted_entities: Dict[str, Any]


@router.post("/v1/work-orders/prepare", response_model=PrepareWorkOrderResponse)
async def prepare_work_order(
    request: PrepareWorkOrderRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Phase 1: Prepare work order mutation (preview).

    Extracts entities from NLP query and builds mutation preview.
    Returns pre-filled values, missing fields, and warnings.
    """
    try:
        # 1. Extract entities from query (or use pre-extracted)
        if request.entities:
            extracted_entities = request.entities
        else:
            extracted_entities = await extract_entities(request.query_text)

        # 2. Build mutation preview using prefill engine
        preview = await build_mutation_preview(
            query_text=request.query_text,
            extracted_entities=extracted_entities,
            field_metadata=WORK_ORDER_FIELD_METADATA,
            yacht_id=request.yacht_id,
            supabase_client=get_supabase_client(),
            user_id=current_user["id"],
        )

        # 3. Return preview to frontend
        return PrepareWorkOrderResponse(
            preview=preview["mutation_preview"],
            missing_required=preview["missing_required"],
            warnings=preview["warnings"],
            dropdown_options=preview["dropdown_options"],
            ready_to_commit=preview["ready_to_commit"],
            extracted_entities=extracted_entities,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
```

### 3. Create /commit Endpoint

```python
# apps/api/routes/work_order_routes.py (continued)

from common.prefill_engine import validate_mutation_preview


class CommitWorkOrderRequest(BaseModel):
    """Request to commit work order mutation."""
    mutation_preview: Dict[str, Any]
    yacht_id: str


class CommitWorkOrderResponse(BaseModel):
    """Response from commit endpoint."""
    success: bool
    work_order_id: str
    wo_number: str
    errors: Optional[List[str]] = None


@router.post("/v1/work-orders/commit", response_model=CommitWorkOrderResponse)
async def commit_work_order(
    request: CommitWorkOrderRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Phase 2: Commit work order mutation (execute).

    Validates preview and executes mutation in database.
    """
    try:
        # 1. Validate mutation preview
        validation = validate_mutation_preview(
            mutation_preview=request.mutation_preview,
            field_metadata=WORK_ORDER_FIELD_METADATA
        )

        if not validation["valid"]:
            raise HTTPException(status_code=400, detail={
                "errors": validation["errors"]
            })

        # 2. Verify yacht_id matches auth context (security check)
        if request.mutation_preview.get("yacht_id") != request.yacht_id:
            raise HTTPException(status_code=403, detail="Yacht ID mismatch")

        # 3. Execute mutation (INSERT into pms_work_orders)
        supabase = get_supabase_client()
        response = supabase.table("pms_work_orders") \
            .insert(request.mutation_preview) \
            .execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=500, detail="Insert failed")

        work_order = response.data[0]

        # 4. Log event
        await supabase.table("event_logs").insert({
            "yacht_id": request.yacht_id,
            "event_type": "work_order_created",
            "user_id": current_user["id"],
            "data": {
                "work_order_id": work_order["id"],
                "wo_number": work_order["wo_number"],
            },
        }).execute()

        # 5. Return success
        return CommitWorkOrderResponse(
            success=True,
            work_order_id=work_order["id"],
            wo_number=work_order["wo_number"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")
```

### 4. Frontend Integration

```typescript
// Frontend usage (TypeScript/React)

interface MutationPreview {
  preview: Record<string, any>;
  missing_required: string[];
  warnings: string[];
  dropdown_options: Record<string, Array<{id: string, name: string}>>;
  ready_to_commit: boolean;
  extracted_entities: Record<string, any>;
}

async function createWorkOrder(queryText: string, yachtId: string) {
  // Step 1: Prepare (get preview)
  const prepareResponse = await fetch('/v1/work-orders/prepare', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      query_text: queryText,
      yacht_id: yachtId,
    }),
  });

  const preview: MutationPreview = await prepareResponse.json();

  // Step 2: Show preview to user
  if (preview.ready_to_commit) {
    // All fields populated - show confirmation dialog
    const confirmed = await showConfirmationDialog(preview.preview);

    if (confirmed) {
      // Step 3: Commit
      const commitResponse = await fetch('/v1/work-orders/commit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          mutation_preview: preview.preview,
          yacht_id: yachtId,
        }),
      });

      const result = await commitResponse.json();
      return result;
    }
  } else {
    // Missing/ambiguous fields - show form
    const formData = await showInteractiveForm({
      preview: preview.preview,
      missing_required: preview.missing_required,
      warnings: preview.warnings,
      dropdown_options: preview.dropdown_options,
    });

    // User fills in missing fields
    const updatedPreview = {...preview.preview, ...formData};

    // Commit with updated preview
    const commitResponse = await fetch('/v1/work-orders/commit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        mutation_preview: updatedPreview,
        yacht_id: yachtId,
      }),
    });

    return await commitResponse.json();
  }
}
```

### 5. Interactive Form Example

```typescript
// React component for interactive form

function WorkOrderPreviewForm({
  preview,
  missing_required,
  warnings,
  dropdown_options,
  onSubmit,
}: {
  preview: Record<string, any>;
  missing_required: string[];
  warnings: string[];
  dropdown_options: Record<string, Array<{id: string, name: string}>>;
  onSubmit: (data: Record<string, any>) => void;
}) {
  const [formData, setFormData] = useState(preview);

  return (
    <form onSubmit={() => onSubmit(formData)}>
      <h2>Work Order Preview</h2>

      {/* Pre-filled fields (read-only or editable) */}
      <div className="field-group">
        <label>Title</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({...formData, title: e.target.value})}
          className="prefilled"
        />
        <span className="checkmark">✓ Auto-filled</span>
      </div>

      <div className="field-group">
        <label>Priority</label>
        <select
          value={formData.priority}
          onChange={(e) => setFormData({...formData, priority: e.target.value})}
          className="prefilled"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <span className="checkmark">✓ Auto-filled (mapped from "urgent")</span>
      </div>

      {/* Ambiguous fields (dropdown) */}
      {dropdown_options.equipment_id && (
        <div className="field-group ambiguous">
          <label>Equipment *</label>
          <select
            value={formData.equipment_id}
            onChange={(e) => setFormData({...formData, equipment_id: e.target.value})}
          >
            <option value="">-- Select Equipment --</option>
            {dropdown_options.equipment_id.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name} ({option.category})
              </option>
            ))}
          </select>
          <span className="warning">⚠ Multiple matches found</span>
        </div>
      )}

      {/* Missing required fields */}
      {missing_required.includes('description') && (
        <div className="field-group required">
          <label>Description *</label>
          <textarea
            value={formData.description || ''}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            required
          />
          <span className="error">Required field</span>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="warnings">
          <h3>Warnings</h3>
          <ul>
            {warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <button type="submit" disabled={missing_required.length > 0}>
        Create Work Order
      </button>
    </form>
  );
}
```

## Testing

### Unit Tests

```python
# tests/test_work_order_mutations.py

import pytest
from unittest.mock import Mock

from common.prefill_engine import build_mutation_preview
from mutations.work_orders.field_metadata import WORK_ORDER_FIELD_METADATA


@pytest.mark.asyncio
async def test_work_order_prepare_full_success():
    """Test work order preview with all fields populated."""
    # Mock Supabase client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [{"id": "eq-123", "name": "main engine"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value = mock_response

    preview = await build_mutation_preview(
        query_text="create urgent work order for main engine overheating",
        extracted_entities={
            "equipment": "main engine",
            "symptom": "overheating",
            "priority": "urgent",
        },
        field_metadata=WORK_ORDER_FIELD_METADATA,
        yacht_id="yacht-123",
        supabase_client=mock_client,
        user_id="user-456",
    )

    assert preview["ready_to_commit"] == True
    assert preview["mutation_preview"]["equipment_id"] == "eq-123"
    assert preview["mutation_preview"]["title"] == "main engine - overheating"
    assert preview["mutation_preview"]["priority"] == "critical"  # mapped
    assert len(preview["missing_required"]) == 0


@pytest.mark.asyncio
async def test_work_order_prepare_ambiguous_equipment():
    """Test work order preview with ambiguous equipment."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [
        {"id": "eq-1", "name": "main engine", "category": "propulsion"},
        {"id": "eq-2", "name": "auxiliary engine", "category": "power"},
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value = mock_response

    preview = await build_mutation_preview(
        query_text="create work order for engine",
        extracted_entities={"equipment": "engine"},
        field_metadata=WORK_ORDER_FIELD_METADATA,
        yacht_id="yacht-123",
        supabase_client=mock_client,
    )

    assert preview["ready_to_commit"] == False
    assert "equipment_id" in preview["dropdown_options"]
    assert len(preview["dropdown_options"]["equipment_id"]) == 2
```

### Integration Tests

```python
# tests/integration/test_work_order_endpoints.py

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_work_order_prepare_endpoint():
    """Test /prepare endpoint returns valid preview."""
    response = client.post("/v1/work-orders/prepare", json={
        "query_text": "create urgent work order for main engine overheating",
        "yacht_id": "yacht-123",
    })

    assert response.status_code == 200
    data = response.json()
    assert "preview" in data
    assert "missing_required" in data
    assert "ready_to_commit" in data


def test_work_order_commit_endpoint():
    """Test /commit endpoint creates work order."""
    # First prepare
    prepare_response = client.post("/v1/work-orders/prepare", json={
        "query_text": "create urgent work order for main engine overheating",
        "yacht_id": "yacht-123",
    })
    preview = prepare_response.json()

    # Then commit
    commit_response = client.post("/v1/work-orders/commit", json={
        "mutation_preview": preview["preview"],
        "yacht_id": "yacht-123",
    })

    assert commit_response.status_code == 200
    data = commit_response.json()
    assert data["success"] == True
    assert "work_order_id" in data
    assert "wo_number" in data
```

## Summary

This integration example demonstrates:

1. **Field Metadata Definition**: Define once, use for both /prepare and /commit
2. **Two-Phase Endpoints**: Separate preview and execution
3. **Frontend Integration**: Show interactive form with pre-filled values
4. **Validation**: Validate preview before commit
5. **Security**: RLS enforcement, yacht_id verification
6. **Testing**: Unit and integration tests

The prefill engine handles all the complexity of entity extraction, lookup resolution, value transformation, and validation, allowing endpoints to focus on business logic.
