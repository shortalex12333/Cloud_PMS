# Part Lens Implementation - Complete Template

**Date**: 2026-01-30
**Status**: ✅ COMPLETE - Ready as Template for Other Engineers
**Owner**: Part Lens Team

---

## Executive Summary

Part Lens has been fully implemented with the new bulletproof architecture. This serves as the **template** for all other lens engineers to follow.

**What Was Built**:
1. ✅ Base infrastructure (capability + microaction registries)
2. ✅ Part Lens search capabilities (10 entity types, 6 capabilities)
3. ✅ Part Lens microaction logic (stock-based + role-based filtering)
4. ✅ Auto-discovery system (drop file → auto-registered)
5. ✅ Fail-fast validation (startup errors if config invalid)

**Key Benefits**:
- **Zero merge conflicts**: Each lens = separate file
- **Clear ownership**: Part Lens team only touches part_*.py files
- **Easy debugging**: Errors show lens name, file, line number
- **Type safety**: Pydantic validates at startup
- **Template ready**: Other engineers can copy Part Lens structure

---

## Files Created

### Base Infrastructure (All Lenses Use)

```
apps/api/prepare/
├── base_capability.py              # Base classes for search capabilities
├── capability_registry.py          # Auto-discovery for capabilities
└── capabilities/
    ├── __init__.py
    └── part_capabilities.py        # PART LENS OWNS

apps/api/microactions/
├── base_microaction.py             # Base classes for action suggestions
├── microaction_registry.py         # Auto-discovery for microactions
└── lens_microactions/
    ├── __init__.py
    └── part_microactions.py        # PART LENS OWNS
```

### Part Lens Specific Files

**1. `apps/api/prepare/capabilities/part_capabilities.py`** (290 lines)
- 10 entity type mappings
- 6 capability implementations
- Stock-aware search
- Scoring logic

**2. `apps/api/microactions/lens_microactions/part_microactions.py`** (368 lines)
- 3 entity types handled (part, inventory_stock, shopping_list_item)
- Stock-based action filtering
- Role-based action filtering
- Intent-based prioritization
- Prefill data generation

---

## Part Lens Capabilities

### Entity Types Handled

| Entity Type | Capability | Table | Column | Priority |
|-------------|-----------|--------|--------|----------|
| PART_NUMBER | part_by_part_number_or_name | pms_parts | part_number | 3 (high) |
| PART_NAME | part_by_part_number_or_name | pms_parts | name | 2 |
| PART | part_by_part_number_or_name | pms_parts | name | 2 |
| MANUFACTURER | part_by_manufacturer | pms_parts | manufacturer | 1 |
| PART_BRAND | part_by_manufacturer | pms_parts | manufacturer | 1 |
| PART_STORAGE_LOCATION | inventory_by_storage_location | pms_inventory_stock | storage_location | 1 |
| PART_CATEGORY | part_by_category | pms_parts | category | 1 |
| PART_SUBCATEGORY | part_by_category | pms_parts | subcategory | 1 |
| SHOPPING_LIST_ITEM | shopping_list_by_part | pms_shopping_list_items | part_name | 1 |
| PART_EQUIPMENT_USAGE | part_usage_by_equipment | pms_part_usage | equipment_name | 1 |

### Capabilities Implemented

1. **part_by_part_number_or_name**: Search parts by part number, name, or manufacturer
2. **part_by_manufacturer**: Search parts by manufacturer/brand
3. **inventory_by_storage_location**: Search inventory by storage location
4. **part_by_category**: Search parts by category or subcategory
5. **shopping_list_by_part**: Search shopping list items
6. **part_usage_by_equipment**: Search part usage by equipment

---

## Part Lens Microactions

### Action Filtering Logic

#### 1. Stock-Based Filtering

```python
# If on_hand = 0:
#   ❌ Hide: consume_part, transfer_part, write_off_part
#   ✅ Show: receive_part, add_to_shopping_list

# If on_hand <= min_level:
#   ⬆️  Boost priority: add_to_shopping_list (priority = 3)
```

#### 2. Role-Based Filtering

Already handled by action router:
- SIGNED actions (adjust_stock_quantity, write_off_part) → Captain/Manager only
- MUTATE actions (receive, consume, transfer) → Chief Engineer+
- READ actions → All roles

#### 3. Intent-Based Prioritization

```python
# If query_intent = "receive_part":
#   receive_part → priority = 5 (highest)
#   other actions → priority = 1-3
```

### Action Prefill Data

Each action gets pre-filled form data:

**receive_part**:
```json
{
  "part_id": "uuid",
  "part_name": "Engine Oil Filter",
  "part_number": "OF-1234",
  "location": "Engine Room",
  "current_stock": 10
}
```

**consume_part**:
```json
{
  "part_id": "uuid",
  "part_name": "Engine Oil Filter",
  "available_qty": 10,
  "max_quantity": 10,
  "location": "Engine Room"
}
```

**add_to_shopping_list**:
```json
{
  "part_id": "uuid",
  "part_name": "Engine Oil Filter",
  "quantity_requested": 15,  // Computed: round_up(max(min_level - on_hand, 1), reorder_multiple)
  "urgency": "high",          // Computed based on stock level
  "current_stock": 2,
  "min_level": 15
}
```

---

## How Other Engineers Use This Template

### Step 1: Copy Part Lens Files

```bash
# Certificate Lens engineer:
cp apps/api/prepare/capabilities/part_capabilities.py \
   apps/api/prepare/capabilities/certificate_capabilities.py

cp apps/api/microactions/lens_microactions/part_microactions.py \
   apps/api/microactions/lens_microactions/certificate_microactions.py
```

### Step 2: Find & Replace

In `certificate_capabilities.py`:
```bash
# Find: PartLensCapability
# Replace: CertificateLensCapability

# Find: lens_name = "part_lens"
# Replace: lens_name = "certificate_lens"

# Find: pms_parts
# Replace: pms_certificates (or your table name)
```

In `certificate_microactions.py`:
```bash
# Find: PartLensMicroactions
# Replace: CertificateLensMicroactions

# Find: lens_name = "part_lens"
# Replace: lens_name = "certificate_lens"

# Find: entity_types = ["part", "inventory_stock", "shopping_list_item"]
# Replace: entity_types = ["certificate", "certificate_renewal"]
```

### Step 3: Update Entity Mappings

From your lens spec (`docs/pipeline/entity_lenses/certificate_lens/v2/certificate_lens_v2_FINAL.md`):

**Extract tables** (PART 1: DATABASE SCHEMA):
- pms_certificates
- pms_certificate_renewals
- pms_certificate_holders

**Define entity types**:
- CERTIFICATE_TYPE
- CERTIFICATE_NUMBER
- CERTIFICATE_HOLDER
- CERTIFICATE_ISSUER
- CERTIFICATE_STATUS

**Map to capabilities**:
```python
def get_entity_mappings(self) -> List[CapabilityMapping]:
    return [
        CapabilityMapping(
            entity_type="CERTIFICATE_TYPE",
            capability_name="certificate_by_type_or_holder",
            table_name="pms_certificates",
            search_column="certificate_type",
            result_type="certificate",
            priority=3
        ),
        # ... more mappings
    ]
```

### Step 4: Implement Capabilities

Copy the structure from Part Lens:

```python
async def certificate_by_type_or_holder(
    self,
    yacht_id: str,
    search_term: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search certificates by type or holder."""
    try:
        result = self.db.table("pms_certificates").select(
            "id, certificate_type, holder_name, expiry_date, status"
        ).eq(
            "yacht_id", yacht_id
        ).or_(
            f"certificate_type.ilike.%{search_term}%,"
            f"holder_name.ilike.%{search_term}%"
        ).limit(limit).execute()

        certificates = result.data or []

        return [
            {
                "id": cert["id"],
                "type": "certificate",
                "title": f"{cert['certificate_type']} - {cert['holder_name']}",
                "score": 0.8,
                "source_table": "pms_certificates",
                "metadata": {
                    "certificate_type": cert["certificate_type"],
                    "holder_name": cert["holder_name"],
                    "expiry_date": cert.get("expiry_date"),
                    "status": cert.get("status"),
                }
            }
            for cert in certificates
        ]
    except Exception as e:
        raise RuntimeError(
            f"Certificate Lens: certificate_by_type_or_holder failed. "
            f"Table: pms_certificates. Error: {str(e)}"
        )
```

### Step 5: Implement Microactions

Copy the structure from Part Lens:

```python
async def get_suggestions(
    self,
    entity_type: str,
    entity_id: str,
    entity_data: Dict[str, Any],
    user_role: str,
    yacht_id: str,
    query_intent: Optional[str] = None
) -> List[ActionSuggestion]:
    """Get context-valid actions for a certificate."""

    # Get all certificate actions for user role
    from apps.api.action_router.registry import get_actions_for_domain
    all_actions = get_actions_for_domain("certificates", user_role)

    # Fetch certificate state
    cert_info = await self._get_certificate_info(entity_id, yacht_id)

    # Filter actions based on state
    suggestions = []

    for action in all_actions:
        # State-based filtering
        is_expired = cert_info.get("is_expired", False)

        if is_expired and action.action_id == "delete_certificate":
            continue  # Don't allow deleting expired certs

        if is_expired:
            # Boost renewal priority
            priority = 5 if action.action_id == "renew_certificate" else 1
        else:
            priority = 3 if action.action_id == query_intent else 1

        # Build suggestion
        suggestions.append(ActionSuggestion(
            action_id=action.action_id,
            label=action.label,
            variant=ActionVariant(action.variant.value),
            entity_id=entity_id,
            entity_type=entity_type,
            prefill_data=await self._get_prefill_data(action.action_id, entity_id, cert_info),
            priority=priority
        ))

    suggestions.sort(key=lambda s: s.priority, reverse=True)
    return suggestions
```

### Step 6: Test

```bash
# Validate registry
python -m apps.api.prepare.capability_registry
python -m apps.api.microactions.microaction_registry

# Run E2E tests
npm run test:e2e -- tests/e2e/certificates/
```

### Step 7: Submit PR

```bash
git checkout -b feature/certificate-lens-capabilities
git add apps/api/prepare/capabilities/certificate_capabilities.py
git add apps/api/microactions/lens_microactions/certificate_microactions.py
git commit -m "Add Certificate Lens capabilities and microactions

- Implemented certificate search capabilities
- Implemented expiry-based action filtering
- Added renewal action prefill logic
- Template from Part Lens

Ref: PART_LENS_IMPLEMENTATION_COMPLETE.md"
git push origin feature/certificate-lens-capabilities
```

---

## Validation Checklist

Before submitting PR, verify:

### Capabilities
- [ ] All entity types from lens spec mapped
- [ ] All capabilities implemented
- [ ] All SQL queries tested
- [ ] Proper error handling
- [ ] Scoring logic implemented
- [ ] Result formatting correct

### Microactions
- [ ] All entity types handled
- [ ] State-based filtering logic
- [ ] Role-based filtering (verify with action router)
- [ ] Intent prioritization
- [ ] Prefill data for all actions
- [ ] Urgency/priority calculation

### Registry
- [ ] File named `{lens_name}_capabilities.py`
- [ ] File named `{lens_name}_microactions.py`
- [ ] Class name matches pattern
- [ ] `lens_name` property set correctly
- [ ] `enabled = True`
- [ ] No duplicate entity types across lenses

### Testing
- [ ] Startup validation passes
- [ ] Registry auto-discovers lens
- [ ] Search returns results
- [ ] Actions filtered correctly
- [ ] Prefill data populated
- [ ] E2E tests pass

---

## Common Patterns

### Pattern 1: Expiry-Based Filtering

```python
# For certificates, documents, etc.
days_until_expiry = (expiry_date - datetime.now()).days

if days_until_expiry < 0:
    # Expired
    priority = 5 if action_id == "renew" else 1
    hide_actions = ["view_certificate"]  # Can't view expired
elif days_until_expiry < 30:
    # Expiring soon
    priority = 4 if action_id == "renew" else 2
else:
    # Valid
    priority = 1
```

### Pattern 2: Status-Based Filtering

```python
# For work orders, shopping lists, etc.
if status == "completed":
    hide_actions = ["edit", "delete"]
    show_actions = ["view_history", "duplicate"]
elif status == "in_progress":
    show_actions = ["edit", "mark_complete", "add_note"]
elif status == "pending":
    show_actions = ["start", "assign", "cancel"]
```

### Pattern 3: Quantity-Based Filtering

```python
# For parts, certificates (number of crew), etc.
if quantity == 0:
    hide_actions = ["consume", "transfer"]
    priority_boost = ["receive", "order"]
elif quantity <= threshold:
    priority_boost = ["order"]
else:
    # Normal priorities
    pass
```

---

## Troubleshooting

### Registry Not Finding Lens

**Symptom**: `No lenses registered!`

**Solution**:
1. Check file is in correct directory: `apps/api/prepare/capabilities/`
2. Check file name ends with `_capabilities.py`
3. Check class subclasses `BaseLensCapability`
4. Check `lens_name` property defined
5. Check `enabled = True`

### Duplicate Entity Type Error

**Symptom**: `Duplicate entity type 'CERTIFICATE_TYPE' claimed by both...`

**Solution**:
1. Check entity types across all lenses
2. Rename to be lens-specific: `CERT_TYPE` → `CERTIFICATE_TYPE`
3. Or assign entity type to only one lens

### Capability Not Found

**Symptom**: `Capability 'certificate_by_type' not found`

**Solution**:
1. Check method name matches `capability_name` in mapping
2. Check method signature: `async def capability_name(self, yacht_id, search_term, limit)`
3. Check method is not private (`_method_name`)

### SQL Query Fails

**Symptom**: `CapabilityExecutionError: column "cert_type" does not exist`

**Solution**:
1. Check column name matches database schema
2. Check table name is correct
3. Check join syntax (Supabase uses special syntax)
4. Test query directly in Supabase dashboard

---

## Success Metrics

**Part Lens**:
- ✅ 10 entity types registered
- ✅ 6 capabilities implemented
- ✅ 10 actions with prefill data
- ✅ Stock-based filtering working
- ✅ Role-based filtering working
- ✅ Auto-discovery working
- ✅ Startup validation passing
- ✅ Zero merge conflicts with other lenses

**Template Ready**: Other engineers can copy Part Lens structure and customize for their lens in <2 hours.

---

## Next Steps for Other Engineers

1. **Certificate Lens**: Copy Part Lens template, update for certificates
2. **Crew Lens**: Copy Part Lens template, update for crew
3. **Work Order Lens**: Copy Part Lens template, update for work orders
4. **Document Lens**: Copy Part Lens template, update for documents
5. **Equipment Lens**: Copy Part Lens template, update for equipment
6. **Fault Lens**: Copy Part Lens template, update for faults

**Timeline**: ~2 hours per lens (copy → customize → test → submit PR)

**Parallel Work**: All lens teams can work simultaneously (zero conflicts)

---

**Questions?** Refer to Part Lens files as working example:
- `apps/api/prepare/capabilities/part_capabilities.py`
- `apps/api/microactions/lens_microactions/part_microactions.py`
