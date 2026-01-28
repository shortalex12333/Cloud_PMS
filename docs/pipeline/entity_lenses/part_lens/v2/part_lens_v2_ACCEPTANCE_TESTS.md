# Part Lens: Acceptance Tests

**Version**: v2
**Date**: 2026-01-27
**Parent Document**: `part_lens_v2_FINAL.md`
**Reference**: `ACCEPTANCE_MATRIX.md`

---

# TEST CATEGORIES

Per the pipeline standard, all lenses must pass tests in these categories:

1. **Role & CRUD** — Exercise role permissions and deny-by-default
2. **Isolation & Storage** — Yacht isolation and safe storage prefixes
3. **Edge Cases** — Client error mapping (4xx never 500)
4. **Audit Invariant** — Signature semantics and ledger correctness

---

# CATEGORY 1: ROLE & CRUD

## 1.1 View Part (All Roles)

| Test | Role | Action | Expected |
|------|------|--------|----------|
| `test_crew_can_view_parts` | crew | GET /parts | 200 + results |
| `test_deckhand_can_view_parts` | deckhand | GET /parts | 200 + results |
| `test_chief_engineer_can_view_parts` | chief_engineer | GET /parts | 200 + results |

```python
def test_crew_can_view_parts():
    """All authenticated users can view parts."""
    response = client.get('/v1/parts', headers=crew_headers)
    assert response.status_code == 200
    assert 'items' in response.json()
```

---

## 1.2 Record Part Consumption

| Test | Role | Expected |
|------|------|----------|
| `test_crew_cannot_consume_parts` | crew | 403 Forbidden |
| `test_steward_cannot_consume_parts` | steward | 403 Forbidden |
| `test_deckhand_can_consume_parts` | deckhand | 200 OK |
| `test_bosun_can_consume_parts` | bosun | 200 OK |
| `test_eto_can_consume_parts` | eto | 200 OK |
| `test_chief_engineer_can_consume_parts` | chief_engineer | 200 OK |

```python
def test_crew_cannot_consume_parts():
    """Basic crew role cannot record part consumption."""
    response = client.post('/v1/actions/execute', headers=crew_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })
    assert response.status_code == 403
    assert response.json()['error'] == 'forbidden'

def test_deckhand_can_consume_parts():
    """Deckhand can record part consumption."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })
    assert response.status_code == 200
    assert response.json()['success'] == True
```

---

## 1.3 Adjust Stock Quantity

| Test | Role | Expected |
|------|------|----------|
| `test_crew_cannot_adjust_stock` | crew | 403 |
| `test_deckhand_cannot_adjust_stock` | deckhand | 403 |
| `test_bosun_cannot_adjust_stock` | bosun | 403 |
| `test_eto_can_adjust_stock_small` | eto | 200 |
| `test_chief_engineer_can_adjust_stock_small` | chief_engineer | 200 |
| `test_eto_cannot_adjust_stock_large_without_signature` | eto | 403 |
| `test_chief_engineer_can_adjust_stock_large_with_signature` | chief_engineer | 200 |

```python
def test_deckhand_cannot_adjust_stock():
    """Deckhand cannot adjust stock quantities."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': 10, 'reason': 'Count correction'}
    })
    assert response.status_code == 403

def test_eto_can_adjust_stock_small():
    """ETO can make small stock adjustments."""
    # Part has qty=10, adjusting to 11 (10% change)
    response = client.post('/v1/actions/execute', headers=eto_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': 11, 'reason': 'Found extra in store'}
    })
    assert response.status_code == 200

def test_eto_cannot_adjust_stock_large_without_signature():
    """ETO cannot make large adjustments without signature."""
    # Part has qty=10, adjusting to 2 (80% change) - requires signature
    response = client.post('/v1/actions/execute', headers=eto_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': 2, 'reason': 'Damaged units'}
    })
    # ETO cannot sign, so this should fail
    assert response.status_code == 403
    assert 'signature_required' in response.json().get('error', '')

def test_chief_engineer_can_adjust_stock_large_with_signature():
    """Chief Engineer can make large adjustments with signature."""
    response = client.post('/v1/actions/execute', headers=chief_engineer_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {
            'new_quantity': 2,
            'reason': 'Damaged units found during inspection',
            'signature': VALID_SIGNATURE_PAYLOAD
        }
    })
    assert response.status_code == 200
```

---

## 1.4 Add to Shopping List

| Test | Role | Expected |
|------|------|----------|
| `test_crew_cannot_add_to_shopping_list` | crew | 403 |
| `test_deckhand_can_add_to_shopping_list` | deckhand | 200 |
| `test_steward_can_add_to_shopping_list` | steward | 200 |
| `test_purser_can_add_to_shopping_list` | purser | 200 |

```python
def test_crew_cannot_add_to_shopping_list():
    """Basic crew cannot add to shopping list."""
    response = client.post('/v1/actions/execute', headers=crew_headers, json={
        'action': 'add_to_shopping_list',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'quantity_requested': 5}
    })
    assert response.status_code == 403

def test_steward_can_add_to_shopping_list():
    """Steward can add to shopping list."""
    response = client.post('/v1/actions/execute', headers=steward_headers, json={
        'action': 'add_to_shopping_list',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'quantity_requested': 5}
    })
    assert response.status_code == 200
```

---

## 1.5 Create Part

| Test | Role | Expected |
|------|------|----------|
| `test_crew_cannot_create_part` | crew | 403 |
| `test_deckhand_cannot_create_part` | deckhand | 403 |
| `test_eto_can_create_part` | eto | 200 |
| `test_chief_engineer_can_create_part` | chief_engineer | 200 |

```python
def test_deckhand_cannot_create_part():
    """Deckhand cannot create new parts."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'create_part',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'name': 'New Test Part'}
    })
    assert response.status_code == 403

def test_eto_can_create_part():
    """ETO can create new parts."""
    response = client.post('/v1/actions/execute', headers=eto_headers, json={
        'action': 'create_part',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'name': 'New Oil Filter',
            'part_number': 'OIL-123',
            'manufacturer': 'Cat',
            'initial_quantity': 5
        }
    })
    assert response.status_code == 200
    assert 'part_id' in response.json()
```

---

# CATEGORY 2: ISOLATION & STORAGE

## 2.1 Yacht Isolation

| Test | Description | Expected |
|------|-------------|----------|
| `test_cannot_view_other_yacht_parts` | Query with Yacht A JWT | Returns 0 for Yacht B part |
| `test_cannot_consume_other_yacht_part` | Consume with Yacht A JWT | 403 or 404 |
| `test_cannot_adjust_other_yacht_part` | Adjust with Yacht A JWT | 403 or 404 |

```python
def test_cannot_view_other_yacht_parts():
    """Cannot see parts from another yacht."""
    # Query as Yacht A user
    response = client.get(
        f'/v1/parts/{YACHT_B_PART_ID}',
        headers=yacht_a_headers
    )
    assert response.status_code == 404

def test_cannot_consume_other_yacht_part():
    """Cannot record consumption for other yacht's part."""
    response = client.post('/v1/actions/execute', headers=yacht_a_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_A_ID, 'part_id': YACHT_B_PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })
    # Should fail - either 403 (RLS) or 404 (not found)
    assert response.status_code in [403, 404]
```

## 2.2 Anon Access Denied

```python
def test_anon_cannot_view_parts():
    """Anonymous request cannot view parts."""
    response = client.get('/v1/parts')  # No auth header
    assert response.status_code in [401, 403]

def test_anon_cannot_consume_parts():
    """Anonymous request cannot consume parts."""
    response = client.post('/v1/actions/execute', json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })
    assert response.status_code in [401, 403]
```

## 2.3 Service Role Access

```python
def test_service_role_can_access_all_parts():
    """Service role bypasses RLS."""
    response = client.get('/v1/parts', headers=service_role_headers)
    assert response.status_code == 200
    # Should see parts from all yachts (in test DB)
```

---

# CATEGORY 3: EDGE CASES

All edge cases must return 4xx, never 500.

## 3.1 Insufficient Stock

```python
def test_consume_more_than_available():
    """Cannot consume more than quantity_on_hand."""
    # Part has qty=3
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 10}
    })
    assert response.status_code == 400
    assert response.json()['error'] == 'insufficient_stock'
    assert response.json()['available'] == 3
    assert response.json()['requested'] == 10
```

## 3.2 Invalid Work Order

```python
def test_consume_invalid_work_order():
    """Cannot consume for non-existent work order."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': 'fake-uuid', 'quantity': 1}
    })
    assert response.status_code == 404
    assert response.json()['error'] == 'work_order_not_found'

def test_consume_closed_work_order():
    """Cannot consume for completed work order."""
    # WO_CLOSED_ID is a work order with status='completed'
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_CLOSED_ID, 'quantity': 1}
    })
    assert response.status_code == 400
    assert response.json()['error'] == 'work_order_invalid_status'
    assert response.json()['current_status'] == 'completed'
```

## 3.3 Part Not Found

```python
def test_consume_nonexistent_part():
    """Cannot consume non-existent part."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': 'fake-uuid'},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })
    assert response.status_code == 404
    assert response.json()['error'] == 'part_not_found'

def test_adjust_nonexistent_part():
    """Cannot adjust non-existent part."""
    response = client.post('/v1/actions/execute', headers=eto_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': 'fake-uuid'},
        'payload': {'new_quantity': 10, 'reason': 'Test'}
    })
    assert response.status_code == 404
```

## 3.4 Invalid Quantity

```python
def test_negative_quantity_consumption():
    """Cannot consume negative quantity."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': -5}
    })
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_quantity'

def test_zero_quantity_consumption():
    """Cannot consume zero quantity."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 0}
    })
    assert response.status_code == 400

def test_negative_stock_adjustment():
    """Cannot adjust to negative stock."""
    response = client.post('/v1/actions/execute', headers=eto_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': -5, 'reason': 'Test'}
    })
    assert response.status_code == 400
```

## 3.5 Large Adjustment Without Signature

```python
def test_large_adjustment_requires_signature():
    """Adjustments >50% require signature."""
    # Part has qty=10, adjusting to 2 (80% reduction)
    response = client.post('/v1/actions/execute', headers=chief_engineer_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': 2, 'reason': 'Damaged'}
        # No signature provided
    })
    assert response.status_code == 400
    assert response.json()['error'] == 'signature_required'

def test_zero_out_requires_signature():
    """Zero-out adjustment requires signature."""
    response = client.post('/v1/actions/execute', headers=chief_engineer_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': 0, 'reason': 'All damaged'}
        # No signature provided
    })
    assert response.status_code == 400
    assert response.json()['error'] == 'signature_required'
```

## 3.6 Transfer Validation

```python
def test_transfer_more_than_source():
    """Cannot transfer more than source location has."""
    # Source location has 3 units
    response = client.post('/v1/actions/execute', headers=bosun_headers, json={
        'action': 'transfer_parts',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {
            'from_location': 'Forward Store',
            'to_location': 'Engine Room',
            'quantity': 10
        }
    })
    assert response.status_code == 400
    assert response.json()['error'] == 'insufficient_stock'

def test_transfer_invalid_source_location():
    """Cannot transfer from non-existent location."""
    response = client.post('/v1/actions/execute', headers=bosun_headers, json={
        'action': 'transfer_parts',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {
            'from_location': 'Fake Location',
            'to_location': 'Engine Room',
            'quantity': 1
        }
    })
    assert response.status_code == 404
    assert response.json()['error'] == 'location_not_found'
```

---

# CATEGORY 4: AUDIT INVARIANT

## 4.1 Non-Signed Actions Create Empty Signature

```python
def test_consumption_audit_has_empty_signature():
    """Part consumption creates audit entry with {} signature."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })
    assert response.status_code == 200

    # Check audit log
    audit = get_latest_audit_entry(entity_type='part', entity_id=PART_ID)
    assert audit['action'] == 'record_part_consumption'
    assert audit['signature'] == {}  # Empty object, not null
    assert audit['signature'] is not None

def test_small_adjustment_audit_has_empty_signature():
    """Small stock adjustment creates audit entry with {} signature."""
    response = client.post('/v1/actions/execute', headers=eto_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'new_quantity': 11, 'reason': 'Found extra'}
    })
    assert response.status_code == 200

    audit = get_latest_audit_entry(entity_type='part', entity_id=PART_ID)
    assert audit['signature'] == {}
```

## 4.2 Signed Actions Have Full Signature

```python
def test_large_adjustment_audit_has_signature():
    """Large adjustment creates audit entry with full signature."""
    response = client.post('/v1/actions/execute', headers=chief_engineer_headers, json={
        'action': 'adjust_stock_quantity',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {
            'new_quantity': 2,
            'reason': 'Damaged units',
            'signature': VALID_SIGNATURE_PAYLOAD
        }
    })
    assert response.status_code == 200

    audit = get_latest_audit_entry(entity_type='part', entity_id=PART_ID)
    assert audit['signature'] != {}
    assert 'user_id' in audit['signature']
    assert 'role_at_signing' in audit['signature']
    assert 'signature_type' in audit['signature']
    assert 'signed_at' in audit['signature']
    assert 'signature_hash' in audit['signature']
    assert audit['signature']['signature_type'] == 'stock_adjustment'
```

## 4.3 Audit Entry Completeness

```python
def test_audit_entry_has_required_fields():
    """All audit entries have required fields."""
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })

    audit = get_latest_audit_entry(entity_type='part', entity_id=PART_ID)

    # Required fields
    assert audit['id'] is not None
    assert audit['yacht_id'] == YACHT_ID
    assert audit['entity_type'] == 'part'
    assert audit['entity_id'] == PART_ID
    assert audit['action'] == 'record_part_consumption'
    assert audit['user_id'] is not None
    assert audit['created_at'] is not None
    assert audit['signature'] is not None  # Never null

    # Old/new values for quantity change
    assert 'quantity_on_hand' in audit['old_values']
    assert 'quantity_on_hand' in audit['new_values']

def test_audit_entry_yacht_isolation():
    """Cannot view other yacht's audit entries."""
    entries = client.get(
        f'/v1/parts/{YACHT_B_PART_ID}/history',
        headers=yacht_a_headers
    )
    # Either 404 (part not found) or empty results
    assert entries.status_code == 404 or len(entries.json()) == 0
```

---

# CATEGORY 5: ACTION LIST ENDPOINT

## 5.1 Actions Returned by Role

```python
def test_crew_sees_only_read_actions():
    """Crew role only sees READ variant actions."""
    response = client.get(
        '/v1/actions/list?domain=parts',
        headers=crew_headers
    )
    assert response.status_code == 200

    actions = response.json()['actions']
    for action in actions:
        # Crew should only see READ actions
        assert action['variant'] == 'READ'

def test_deckhand_sees_consume_action():
    """Deckhand sees record_part_consumption action."""
    response = client.get(
        '/v1/actions/list?domain=parts',
        headers=deckhand_headers
    )

    actions = response.json()['actions']
    action_ids = [a['action_id'] for a in actions]

    assert 'record_part_consumption' in action_ids
    assert 'add_to_shopping_list' in action_ids
    assert 'adjust_stock_quantity' not in action_ids  # Not allowed for deckhand

def test_chief_engineer_sees_all_part_actions():
    """Chief Engineer sees all part actions."""
    response = client.get(
        '/v1/actions/list?domain=parts',
        headers=chief_engineer_headers
    )

    actions = response.json()['actions']
    action_ids = [a['action_id'] for a in actions]

    assert 'record_part_consumption' in action_ids
    assert 'adjust_stock_quantity' in action_ids
    assert 'add_to_shopping_list' in action_ids
    assert 'create_part' in action_ids
```

## 5.2 Search Keywords Work

```python
def test_search_use_part():
    """Search 'use part' returns consumption action."""
    response = client.get(
        '/v1/actions/list?q=use+part&domain=parts',
        headers=deckhand_headers
    )

    actions = response.json()['actions']
    assert len(actions) >= 1
    assert actions[0]['action_id'] == 'record_part_consumption'

def test_search_order_parts():
    """Search 'order parts' returns shopping list action."""
    response = client.get(
        '/v1/actions/list?q=order+parts&domain=parts',
        headers=deckhand_headers
    )

    actions = response.json()['actions']
    action_ids = [a['action_id'] for a in actions]
    assert 'add_to_shopping_list' in action_ids
```

---

# CATEGORY 6: NOTIFICATIONS

## 6.1 Low Stock Creates Notification

```python
def test_low_stock_creates_notification():
    """Dropping below minimum creates notification."""
    # Part starts at qty=5, min=3
    # Consume 3 to drop to qty=2 (below min)
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 3}
    })
    assert response.status_code == 200

    # Check notification created for chief_engineer
    notifications = get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock')
    matching = [n for n in notifications if n['source_id'] == str(PART_ID)]
    assert len(matching) >= 1
    assert matching[0]['level'] == 'warning'

def test_stock_out_creates_critical_notification():
    """Zero stock creates critical notification."""
    # Consume all remaining stock
    response = client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 5}  # All of it
    })
    assert response.status_code == 200

    # Check critical notification created
    notifications = get_notifications(user_id=CAPTAIN_ID, topic='stock_out')
    matching = [n for n in notifications if n['source_id'] == str(PART_ID)]
    assert len(matching) >= 1
    assert matching[0]['level'] == 'critical'
```

## 6.2 Notification Idempotency

```python
def test_duplicate_low_stock_not_created():
    """Same low stock alert not sent twice in one day."""
    # Consume to trigger low stock
    client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })

    notifs_after_first = len(get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock'))

    # Consume again
    client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 1}
    })

    notifs_after_second = len(get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock'))

    # Should not have duplicate for same part/topic/day
    assert notifs_after_second == notifs_after_first
```

## 6.3 CTA Payload Correct

```python
def test_notification_cta_payload():
    """Notification CTA has correct prefill data."""
    # Trigger low stock
    client.post('/v1/actions/execute', headers=deckhand_headers, json={
        'action': 'record_part_consumption',
        'context': {'yacht_id': YACHT_ID, 'part_id': PART_ID},
        'payload': {'work_order_id': WO_ID, 'quantity': 4}
    })

    notifications = get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock')
    matching = [n for n in notifications if n['source_id'] == str(PART_ID)][0]

    assert matching['cta_action_id'] == 'add_to_shopping_list'
    assert matching['cta_payload']['part_id'] == str(PART_ID)
    assert 'quantity_requested' in matching['cta_payload']
    assert matching['cta_payload']['quantity_requested'] > 0
```

---

# TEST EXECUTION

## Docker Tests (Fast Loop)

```bash
# Run all part lens tests
cd apps/api
python -m pytest tests/docker/test_part_lens.py -v

# Run specific category
python -m pytest tests/docker/test_part_lens.py -v -k "role"
python -m pytest tests/docker/test_part_lens.py -v -k "edge"
python -m pytest tests/docker/test_part_lens.py -v -k "audit"
```

## Staging CI Tests (Real JWTs)

```bash
# Run staging acceptance
python tests/ci/staging_parts_acceptance.py

# Verify in CI workflow
# .github/workflows/staging-parts-acceptance.yml
```

## Test Data Setup

```python
# tests/fixtures/part_fixtures.py

TEST_PART = {
    'id': 'test-part-uuid',
    'name': 'CAT Fuel Filter 1R-0751',
    'part_number': '1R-0751',
    'manufacturer': 'Caterpillar',
    'quantity_on_hand': 5,
    'minimum_quantity': 3,
    'unit': 'ea',
    'location': 'Engine Room Store'
}

TEST_WORK_ORDER = {
    'id': 'test-wo-uuid',
    'wo_number': 'WO-2026-0045',
    'status': 'in_progress'
}

TEST_WORK_ORDER_CLOSED = {
    'id': 'test-wo-closed-uuid',
    'wo_number': 'WO-2026-0001',
    'status': 'completed'
}

VALID_SIGNATURE_PAYLOAD = {
    'user_id': 'chief-eng-uuid',
    'role_at_signing': 'chief_engineer',
    'signature_type': 'stock_adjustment',
    'reason': 'Test signature',
    'old_quantity': 10,
    'new_quantity': 2,
    'change_percentage': 0.8,
    'signed_at': '2026-01-27T10:00:00Z',
    'signature_hash': 'sha256:test123'
}
```

---

# SUCCESS CRITERIA

All tests in all categories must pass:

| Category | Tests | Status |
|----------|-------|--------|
| Role & CRUD | 15 | ⬜ |
| Isolation & Storage | 5 | ⬜ |
| Edge Cases | 12 | ⬜ |
| Audit Invariant | 5 | ⬜ |
| Action List | 4 | ⬜ |
| Notifications | 3 | ⬜ |
| **Total** | **44** | ⬜ |

**Rule**: No 500 errors in any test. All client errors must be 4xx with structured error response.

---

**END OF ACCEPTANCE TESTS**
