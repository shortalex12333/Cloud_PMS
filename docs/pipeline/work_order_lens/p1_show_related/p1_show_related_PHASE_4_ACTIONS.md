# Work Order Lens P1: Show Related — PHASE 4: ACTIONS

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Define **action registry entries** and **handler signatures** for Show Related feature.

---

## Action Registry Entries

### Action 1: view_related_entities

```python
"view_related_entities": ActionDefinition(
    action_id="view_related_entities",
    label="View Related Entities",
    description="Show all related entities for a work order (parts, manuals, previous work, handovers, attachments)",
    variant=ActionVariant.READ,
    domain="work_orders",
    endpoint="/v1/related",
    method="GET",
    allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["yacht_id", "entity_type", "entity_id"],
    optional_fields=[],
    search_keywords=["related", "context", "parts", "manuals", "previous", "attachments", "handovers"],
    icon="link",
    display_order=20,
    is_bulk=False,
    storage_options=None
)
```

### Action 2: add_entity_link

```python
"add_entity_link": ActionDefinition(
    action_id="add_entity_link",
    label="Add Related Link",
    description="Manually link two entities (HOD/manager only)",
    variant=ActionVariant.MUTATE,
    domain="work_orders",
    endpoint="/v1/related/add",
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["yacht_id", "source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", "link_type"],
    optional_fields=["note"],
    search_keywords=["add", "link", "related", "reference", "evidence"],
    icon="link-plus",
    display_order=21,
    is_bulk=False,
    storage_options=None
)
```

---

## Handler Signatures

### RelatedHandlers Class

**File:** `apps/api/handlers/related_handlers.py` (new)

```python
class RelatedHandlers:
    """Handlers for Show Related feature."""

    def __init__(self, db_client):
        self.db = db_client

    async def list_related(
        self,
        yacht_id: str,
        entity_type: str,
        entity_id: str,
        user_id: str
    ) -> Dict:
        """
        Retrieve all related entities for a given entity.

        Args:
            yacht_id: Yacht UUID (for RLS scoping)
            entity_type: "work_order" (extensible to others)
            entity_id: Entity UUID
            user_id: Authenticated user UUID

        Returns:
            {
                "status": "success",
                "groups": [
                    {
                        "group_key": "parts",
                        "label": "Parts",
                        "count": 3,
                        "items": [...]
                    },
                    ...
                ],
                "add_related_enabled": bool,
                "missing_signals": []
            }

        Raises:
            HTTPException: 400 (invalid entity_type), 404 (entity not found)
        """

    async def add_entity_link(
        self,
        yacht_id: str,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        link_type: str,
        note: Optional[str],
        user_id: str
    ) -> Dict:
        """
        Create an explicit link between two entities.

        Args:
            yacht_id: Yacht UUID
            source_entity_type: "work_order" (or other)
            source_entity_id: Source entity UUID
            target_entity_type: "part"|"manual"|"work_order"|"handover"|"attachment"
            target_entity_id: Target entity UUID
            link_type: "explicit" (default)
            note: Optional context/reason
            user_id: Authenticated user UUID

        Returns:
            {
                "status": "success",
                "link_id": "uuid",
                "created_at": "2026-01-28T12:00:00Z"
            }

        Raises:
            HTTPException:
                400 - Invalid entity types
                403 - Not HOD/manager
                404 - Source or target not found
                409 - Link already exists
        """
```

---

## Route Handlers

**File:** `apps/api/routes/related_routes.py` (new)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from apps.api.handlers.related_handlers import RelatedHandlers
from apps.api.middleware.auth import get_current_user

router = APIRouter(prefix="/v1/related", tags=["related"])

@router.get("")
async def get_related_entities(
    entity_type: str = Query(..., description="Entity type (e.g., work_order)"),
    entity_id: str = Query(..., description="Entity UUID"),
    current_user = Depends(get_current_user)
):
    """
    GET /v1/related?entity_type=work_order&entity_id={uuid}

    Returns all related entities grouped by type.
    """
    yacht_id = current_user.get("yacht_id")
    user_id = current_user.get("sub")

    handlers = RelatedHandlers(db_client)
    result = await handlers.list_related(
        yacht_id=yacht_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id
    )

    return result

@router.post("/add")
async def add_entity_link(
    payload: dict,
    current_user = Depends(get_current_user)
):
    """
    POST /v1/related/add
    Body: {yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type, note?}

    Creates an explicit link between entities (HOD/manager only).
    """
    yacht_id = current_user.get("yacht_id")
    user_id = current_user.get("sub")
    user_role = current_user.get("role")

    # Role check: HOD or manager only
    if user_role not in ["chief_engineer", "chief_officer", "captain", "manager"]:
        raise HTTPException(status_code=403, detail="Only HOD/manager can add entity links")

    handlers = RelatedHandlers(db_client)
    result = await handlers.add_entity_link(
        yacht_id=yacht_id,
        source_entity_type=payload.get("source_entity_type"),
        source_entity_id=payload.get("source_entity_id"),
        target_entity_type=payload.get("target_entity_type"),
        target_entity_id=payload.get("target_entity_id"),
        link_type=payload.get("link_type", "explicit"),
        note=payload.get("note"),
        user_id=user_id
    )

    return result
```

---

## Handler Implementation Logic

### list_related() Flow

```python
async def list_related(self, yacht_id, entity_type, entity_id, user_id):
    # 1. Validate entity_type
    if entity_type != "work_order":
        raise HTTPException(400, "Invalid entity_type. Only 'work_order' supported.")

    # 2. Verify entity exists
    wo = self.db.table("pms_work_orders").select("*").eq("id", entity_id).eq("yacht_id", yacht_id).single().execute()
    if not wo.data:
        raise HTTPException(404, "Work order not found")

    # 3. Query related entities (6 queries)
    parts = await self._get_related_parts(entity_id, yacht_id)
    manuals = await self._get_related_manuals(wo.data, yacht_id)
    previous_work = await self._get_previous_work(wo.data, yacht_id, entity_id)
    handovers = await self._get_related_handovers(wo.data, yacht_id)
    attachments = await self._get_related_attachments(entity_id, yacht_id)
    explicit_links = await self._get_explicit_links(entity_id, yacht_id)

    # 4. Merge explicit links into groups
    merged = self._merge_results(parts, manuals, previous_work, handovers, attachments, explicit_links)

    # 5. Build response
    groups = self._build_groups(merged)

    # 6. Check if user can add links
    add_enabled = await self._can_add_links(user_id, yacht_id)

    return {
        "status": "success",
        "groups": groups,
        "add_related_enabled": add_enabled,
        "missing_signals": []
    }
```

### add_entity_link() Flow

```python
async def add_entity_link(self, yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type, note, user_id):
    # 1. Validate entity types
    valid_types = ["work_order", "part", "manual", "handover", "attachment", "equipment"]
    if source_entity_type not in valid_types or target_entity_type not in valid_types:
        raise HTTPException(400, "Invalid entity type")

    # 2. Verify source and target exist (and are in same yacht)
    # ... (check pms_work_orders, pms_parts, pms_documents, etc.)

    # 3. Check for duplicate link
    existing = self.db.table("pms_entity_links").select("id").match({
        "yacht_id": yacht_id,
        "source_entity_type": source_entity_type,
        "source_entity_id": source_entity_id,
        "target_entity_type": target_entity_type,
        "target_entity_id": target_entity_id,
        "link_type": link_type
    }).execute()

    if existing.data:
        raise HTTPException(409, "Link already exists")

    # 4. Insert link
    link = self.db.table("pms_entity_links").insert({
        "yacht_id": yacht_id,
        "source_entity_type": source_entity_type,
        "source_entity_id": source_entity_id,
        "target_entity_type": target_entity_type,
        "target_entity_id": target_entity_id,
        "link_type": link_type,
        "note": note,
        "created_by": user_id
    }).execute()

    # 5. Audit log
    await self._write_audit_log(yacht_id, user_id, "add_entity_link", link.data[0]["id"], {})

    return {
        "status": "success",
        "link_id": link.data[0]["id"],
        "created_at": link.data[0]["created_at"]
    }
```

---

## Error Handling

| Scenario | Status | Response |
|----------|--------|----------|
| Invalid entity_type | 400 | `{"detail": "Invalid entity_type. Only 'work_order' supported."}` |
| Missing required fields | 400 | `{"detail": "Missing required field: entity_id"}` |
| Entity not found | 404 | `{"detail": "Work order not found"}` |
| Cross-yacht entity | 404 | `{"detail": "Work order not found"}` (RLS blocks, looks like 404) |
| Crew tries to add link | 403 | `{"detail": "Only HOD/manager can add entity links"}` |
| Duplicate link | 409 | `{"detail": "Link already exists"}` |
| Unexpected error | 500 | Map to 4xx if possible; log error |

---

## Next Phase

**PHASE 5: SCENARIOS** - Define test scenarios and acceptance criteria.

---

**ACTIONS STATUS:** ✅ DEFINED
