# Part Lens: Ledger & Notifications Design

**Version**: v2
**Date**: 2026-01-27
**Parent Document**: `part_lens_v2_FINAL.md`

---

# LEDGER (pms_audit_log) — SOURCE OF TRUTH

## Purpose

The ledger provides:
1. **Immutable history** of every stock change, consumption, and adjustment
2. **Compliance evidence** for audits and inspections
3. **Forensic capability** to answer "what happened to part X?"
4. **Notification triggers** based on state changes

## Ledger Entries by Action

### 1. record_part_consumption

**When**: User records part usage for a work order

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "record_part_consumption",
  "user_id": "user-uuid",
  "old_values": {
    "quantity_on_hand": 5
  },
  "new_values": {
    "quantity_on_hand": 4,
    "usage_id": "usage-uuid"
  },
  "signature": {},
  "metadata": {
    "work_order_id": "wo-uuid",
    "work_order_number": "WO-2026-0045",
    "quantity_consumed": 1,
    "usage_reason": "Scheduled maintenance",
    "location_taken_from": "Engine Room Store"
  },
  "created_at": "2026-01-27T10:30:00Z"
}
```

**UI Render**:
```
10:30 AM — John Smith (Deckhand) used 1 unit for WO-2026-0045
Stock: 5 → 4
```

---

### 2. adjust_stock_quantity (Non-Signed)

**When**: Small adjustment (≤50% change)

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "adjust_stock_quantity",
  "user_id": "user-uuid",
  "old_values": {
    "quantity_on_hand": 10
  },
  "new_values": {
    "quantity_on_hand": 11
  },
  "signature": {},
  "metadata": {
    "reason": "Found extra unit in secondary location",
    "adjustment_type": "increase",
    "change_percentage": 0.10
  },
  "created_at": "2026-01-27T11:00:00Z"
}
```

**UI Render**:
```
11:00 AM — ETO adjusted stock: 10 → 11
Reason: Found extra unit in secondary location
```

---

### 3. adjust_stock_quantity (Signed - Large Adjustment)

**When**: Large adjustment (>50% change) OR zero-out

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "adjust_stock_quantity",
  "user_id": "user-uuid",
  "old_values": {
    "quantity_on_hand": 10
  },
  "new_values": {
    "quantity_on_hand": 2
  },
  "signature": {
    "user_id": "chief-eng-uuid",
    "role_at_signing": "chief_engineer",
    "signature_type": "stock_adjustment",
    "reason": "Found 8 units damaged during inspection",
    "old_quantity": 10,
    "new_quantity": 2,
    "change_percentage": 0.80,
    "signed_at": "2026-01-27T14:30:00Z",
    "signature_hash": "sha256:abc123..."
  },
  "metadata": {
    "adjustment_type": "decrease",
    "is_large_adjustment": true
  },
  "created_at": "2026-01-27T14:30:00Z"
}
```

**UI Render**:
```
2:30 PM — Chief Engineer SIGNED adjustment: 10 → 2 (80% reduction)
Reason: Found 8 units damaged during inspection
🔐 Signature verified
```

---

### 4. add_to_shopping_list

**When**: Part added to shopping list

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "add_to_shopping_list",
  "user_id": "user-uuid",
  "old_values": null,
  "new_values": {
    "shopping_list_item_id": "sli-uuid",
    "quantity_requested": 5
  },
  "signature": {},
  "metadata": {
    "source_type": "manual",
    "urgency": "normal",
    "current_stock": 1,
    "minimum_stock": 3
  },
  "created_at": "2026-01-27T09:00:00Z"
}
```

**UI Render**:
```
9:00 AM — Steward added 5 units to shopping list
Current stock: 1 | Min: 3
```

---

### 5. receive_parts

**When**: Parts received from delivery

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "receive_parts",
  "user_id": "user-uuid",
  "old_values": {
    "quantity_on_hand": 1
  },
  "new_values": {
    "quantity_on_hand": 6
  },
  "signature": {},
  "metadata": {
    "receiving_event_id": "recv-uuid",
    "receiving_number": "RCV-2026-0012",
    "quantity_received": 5,
    "purchase_order_id": "po-uuid",
    "storage_location": "Engine Room Store",
    "supplier": "West Marine"
  },
  "created_at": "2026-01-27T15:00:00Z"
}
```

**UI Render**:
```
3:00 PM — Bosun received 5 units from West Marine
Stock: 1 → 6 | Location: Engine Room Store
PO: PO-2026-0034
```

---

### 6. transfer_parts

**When**: Stock moved between locations

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "transfer_parts",
  "user_id": "user-uuid",
  "old_values": {
    "source_location_qty": 8,
    "dest_location_qty": 2
  },
  "new_values": {
    "source_location_qty": 5,
    "dest_location_qty": 5
  },
  "signature": {},
  "metadata": {
    "from_location": "Forward Store",
    "to_location": "Engine Room Store",
    "quantity_transferred": 3
  },
  "created_at": "2026-01-27T16:00:00Z"
}
```

**UI Render**:
```
4:00 PM — Bosun transferred 3 units
Forward Store (8→5) → Engine Room Store (2→5)
```

---

### 7. system_low_stock_detected (Auto-Generated)

**When**: System detects stock below minimum

```json
{
  "id": "audit-uuid",
  "yacht_id": "yacht-uuid",
  "entity_type": "part",
  "entity_id": "part-uuid",
  "action": "system_low_stock_detected",
  "user_id": null,
  "old_values": null,
  "new_values": {
    "current_quantity": 1,
    "minimum_quantity": 3
  },
  "signature": {},
  "metadata": {
    "trigger": "stock_below_minimum",
    "shortage": 2,
    "notification_sent_to": ["chief_engineer", "purser"],
    "auto_generated": true
  },
  "created_at": "2026-01-27T10:31:00Z"
}
```

**UI Render**:
```
10:31 AM — ⚠️ SYSTEM: Low stock alert triggered
Current: 1 | Minimum: 3 | Shortage: 2
Notified: Chief Engineer, Purser
```

---

## Ledger Query Patterns

### Part History (Single Part)

```sql
SELECT
    al.created_at,
    al.action,
    al.user_id,
    aup.name AS actor_name,
    aur.role AS actor_role,
    al.old_values,
    al.new_values,
    CASE WHEN al.signature = '{}'::jsonb THEN false ELSE true END AS is_signed,
    al.metadata
FROM pms_audit_log al
LEFT JOIN auth_users_profiles aup ON al.user_id = aup.id
LEFT JOIN auth_users_roles aur ON al.user_id = aur.user_id AND aur.is_active = true
WHERE al.entity_type = 'part'
  AND al.entity_id = :part_id
  AND al.yacht_id = public.get_user_yacht_id()
ORDER BY al.created_at DESC
LIMIT 100;
```

### User Activity (What I Did)

```sql
SELECT
    al.created_at,
    al.action,
    al.entity_type,
    al.entity_id,
    CASE
        WHEN al.entity_type = 'part' THEN (SELECT name FROM pms_parts WHERE id = al.entity_id)
        ELSE al.entity_id::text
    END AS entity_name,
    al.metadata
FROM pms_audit_log al
WHERE al.user_id = auth.uid()
  AND al.yacht_id = public.get_user_yacht_id()
  AND al.created_at > NOW() - INTERVAL '7 days'
ORDER BY al.created_at DESC
LIMIT 50;
```

### Recent Changes (Last 24 Hours)

```sql
SELECT
    al.created_at,
    al.action,
    al.entity_type,
    p.name AS part_name,
    aup.name AS actor_name,
    al.old_values->>'quantity_on_hand' AS old_qty,
    al.new_values->>'quantity_on_hand' AS new_qty,
    al.metadata->>'reason' AS reason
FROM pms_audit_log al
LEFT JOIN pms_parts p ON al.entity_id = p.id
LEFT JOIN auth_users_profiles aup ON al.user_id = aup.id
WHERE al.entity_type = 'part'
  AND al.yacht_id = public.get_user_yacht_id()
  AND al.created_at > NOW() - INTERVAL '24 hours'
ORDER BY al.created_at DESC;
```

### Signed Actions Audit

```sql
SELECT
    al.created_at,
    al.action,
    al.signature->>'role_at_signing' AS signer_role,
    al.signature->>'reason' AS signature_reason,
    al.signature->>'signed_at' AS signed_at,
    p.name AS part_name,
    al.old_values->>'quantity_on_hand' AS old_qty,
    al.new_values->>'quantity_on_hand' AS new_qty
FROM pms_audit_log al
LEFT JOIN pms_parts p ON al.entity_id = p.id
WHERE al.entity_type = 'part'
  AND al.yacht_id = public.get_user_yacht_id()
  AND al.signature != '{}'::jsonb
ORDER BY al.created_at DESC;
```

---

# NOTIFICATIONS (pms_notifications)

## Purpose

Proactive nudges to the right person at the right time:
- Low stock alerts
- Pending approvals
- Stale receiving events
- Action completion reminders

## Notification Triggers for Parts

### Trigger 1: Low Stock Alert

**Condition**: `quantity_on_hand <= minimum_quantity AND minimum_quantity > 0`

**Timing**: Within 1 minute of stock change

**Recipients**: chief_engineer, purser (via `allowed_roles` for `add_to_shopping_list`)

```json
{
  "id": "notif-uuid",
  "yacht_id": "yacht-uuid",
  "user_id": "chief-eng-uuid",
  "topic": "low_stock",
  "source": "part",
  "source_id": "part-uuid",
  "title": "Low Stock: CAT Fuel Filter 1R-0751",
  "body": "Current: 1 unit | Minimum: 3 units | Shortage: 2 units",
  "level": "warning",
  "cta_action_id": "add_to_shopping_list",
  "cta_payload": {
    "part_id": "part-uuid",
    "part_name": "CAT Fuel Filter 1R-0751",
    "quantity_requested": 3,
    "urgency": "normal"
  },
  "status": "pending",
  "send_after": "2026-01-27T10:31:00Z",
  "created_at": "2026-01-27T10:31:00Z"
}
```

**Frontend Render**:
```
┌─────────────────────────────────────────────┐
│ ⚠️ Low Stock Alert                          │
│ CAT Fuel Filter 1R-0751                     │
│ Current: 1 | Minimum: 3                     │
│                                             │
│ [Add to Shopping List]  [Dismiss]           │
└─────────────────────────────────────────────┘
```

---

### Trigger 2: Critical Stock Out

**Condition**: `quantity_on_hand = 0`

**Timing**: Immediate

**Recipients**: chief_engineer, captain

```json
{
  "id": "notif-uuid",
  "yacht_id": "yacht-uuid",
  "user_id": "captain-uuid",
  "topic": "stock_out",
  "source": "part",
  "source_id": "part-uuid",
  "title": "⛔ OUT OF STOCK: Main Engine Oil Filter",
  "body": "Critical part is completely out of stock. Immediate reorder recommended.",
  "level": "critical",
  "cta_action_id": "add_to_shopping_list",
  "cta_payload": {
    "part_id": "part-uuid",
    "urgency": "critical"
  },
  "status": "pending",
  "send_after": "2026-01-27T10:30:00Z"
}
```

---

### Trigger 3: Shopping List Item Pending

**Condition**: `pms_shopping_list_items.status = 'pending' AND created_at < NOW() - INTERVAL '24 hours'`

**Timing**: Once per day at 09:00

**Recipients**: purser, manager

```json
{
  "id": "notif-uuid",
  "yacht_id": "yacht-uuid",
  "user_id": "purser-uuid",
  "topic": "pending_approval",
  "source": "shopping_list_item",
  "source_id": "sli-uuid",
  "title": "Pending: 3 shopping list items need approval",
  "body": "Items have been waiting for approval for over 24 hours.",
  "level": "info",
  "cta_action_id": "approve_shopping_items",
  "cta_payload": {
    "filter": "pending",
    "older_than_hours": 24
  },
  "status": "pending",
  "send_after": "2026-01-27T09:00:00Z"
}
```

---

### Trigger 4: Received Parts Not Stowed

**Condition**: Receiving event committed but parts not assigned storage location for >4 hours

**Timing**: Check every hour

**Recipients**: bosun

```json
{
  "id": "notif-uuid",
  "yacht_id": "yacht-uuid",
  "user_id": "bosun-uuid",
  "topic": "stow_parts",
  "source": "receiving_event",
  "source_id": "recv-uuid",
  "title": "Parts need stowing: RCV-2026-0012",
  "body": "5 items received 4 hours ago have no storage location assigned.",
  "level": "info",
  "cta_action_id": "assign_storage_locations",
  "cta_payload": {
    "receiving_event_id": "recv-uuid"
  },
  "status": "pending",
  "send_after": "2026-01-27T19:00:00Z"
}
```

---

### Trigger 5: Large Adjustment Needs Review

**Condition**: Signed stock adjustment made within last 24 hours

**Timing**: Next morning at 09:00

**Recipients**: manager (for oversight)

```json
{
  "id": "notif-uuid",
  "yacht_id": "yacht-uuid",
  "user_id": "manager-uuid",
  "topic": "adjustment_review",
  "source": "part",
  "source_id": "part-uuid",
  "title": "Review: Large stock adjustment made",
  "body": "Chief Engineer reduced CAT Fuel Filter from 10 to 2 units (80% reduction).",
  "level": "info",
  "cta_action_id": "view_part_history",
  "cta_payload": {
    "part_id": "part-uuid"
  },
  "status": "pending",
  "send_after": "2026-01-28T09:00:00Z"
}
```

---

## Notification Delivery Flow

```
1. TRIGGER EVENT
   └── Stock drops below minimum

2. GENERATE NOTIFICATION
   └── INSERT INTO pms_notifications with:
       - user_id (based on action's allowed_roles)
       - topic, source, source_id
       - CTA action + payload
       - Idempotency key check

3. DELIVERY CHANNELS
   ├── IN-APP (immediate)
   │   └── Spotlight badge: "2 pending alerts"
   │   └── Notification panel
   │
   ├── EMAIL (batched, respects quiet hours)
   │   └── Digest at 09:00 and 17:00
   │
   └── PUSH (optional, respects preferences)
       └── Only for critical level

4. USER ACTION
   ├── CLICK CTA → Opens ActionModal prefilled
   ├── DISMISS → Mark status = 'dismissed'
   └── IGNORE → Escalation after N hours

5. CLOSE LOOP
   └── Mark notification status = 'read'
   └── Idempotency prevents re-notify
```

---

## Idempotency & Spam Prevention

### Unique Constraint

```sql
CREATE UNIQUE INDEX idx_notifications_idempotency
ON pms_notifications (
    user_id,
    source,
    source_id,
    topic,
    date_trunc('day', send_after)
);
```

This prevents:
- Same low stock alert sent multiple times per day
- Duplicate pending approval reminders
- Spam when quantity hovers around threshold

### Escalation Logic

```python
def should_escalate(notification):
    """Escalate if not read within threshold."""
    if notification.level == 'critical':
        threshold_hours = 4
    elif notification.level == 'warning':
        threshold_hours = 24
    else:
        threshold_hours = 48

    if notification.status == 'sent':
        age_hours = (now() - notification.sent_at).hours
        if age_hours > threshold_hours:
            return True
    return False

def escalate(notification):
    """Bump level or include in digest."""
    if notification.level == 'info':
        notification.level = 'warning'
    elif notification.level == 'warning':
        notification.level = 'critical'

    # Also notify manager for oversight
    create_notification(
        user_id=get_manager_user_id(),
        topic='escalated_' + notification.topic,
        source=notification.source,
        source_id=notification.source_id,
        title=f'ESCALATED: {notification.title}',
        body=f'Not acknowledged for {age_hours} hours. Original: {notification.body}',
        level='warning'
    )
```

---

## Notification SQL Patterns

### Create Low Stock Notification

```sql
-- Called when stock drops below minimum
INSERT INTO pms_notifications (
    id, yacht_id, user_id, topic, source, source_id,
    title, body, level, cta_action_id, cta_payload,
    status, send_after, created_at
)
SELECT
    gen_random_uuid(),
    p.yacht_id,
    aur.user_id,  -- For each allowed role
    'low_stock',
    'part',
    p.id,
    'Low Stock: ' || p.name,
    format('Current: %s | Minimum: %s', p.quantity_on_hand, p.minimum_quantity),
    CASE WHEN p.quantity_on_hand = 0 THEN 'critical' ELSE 'warning' END,
    'add_to_shopping_list',
    jsonb_build_object('part_id', p.id, 'quantity_requested', p.minimum_quantity - p.quantity_on_hand + 1),
    'pending',
    NOW(),
    NOW()
FROM pms_parts p
CROSS JOIN auth_users_roles aur
WHERE p.id = :part_id
  AND p.quantity_on_hand <= p.minimum_quantity
  AND aur.role IN ('chief_engineer', 'purser')
  AND aur.yacht_id = p.yacht_id
  AND aur.is_active = true
ON CONFLICT (user_id, source, source_id, topic, date_trunc('day', send_after))
DO NOTHING;  -- Idempotent
```

### Get User's Pending Notifications

```sql
SELECT
    n.id,
    n.topic,
    n.title,
    n.body,
    n.level,
    n.cta_action_id,
    n.cta_payload,
    n.created_at,
    CASE
        WHEN n.source = 'part' THEN (SELECT name FROM pms_parts WHERE id = n.source_id)
        ELSE n.source_id::text
    END AS source_name
FROM pms_notifications n
WHERE n.user_id = auth.uid()
  AND n.yacht_id = public.get_user_yacht_id()
  AND n.status IN ('pending', 'sent')
  AND n.send_after <= NOW()
ORDER BY
    CASE n.level WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
    n.created_at DESC
LIMIT 20;
```

### Mark Notification Read

```sql
UPDATE pms_notifications
SET
    status = 'read',
    read_at = NOW()
WHERE id = :notification_id
  AND user_id = auth.uid()
  AND yacht_id = public.get_user_yacht_id();
```

---

## Frontend Integration

### Spotlight Badge

```typescript
// useCelesteSearch.ts or dedicated hook
const { data: notifications } = useQuery({
  queryKey: ['notifications', 'pending'],
  queryFn: () => getNotifications({ status: ['pending', 'sent'] }),
  refetchInterval: 30000 // Poll every 30 seconds
});

const unreadCount = notifications?.length ?? 0;
const hasCritical = notifications?.some(n => n.level === 'critical');
```

### Notification Panel

```typescript
// NotificationPanel.tsx
function NotificationPanel() {
  const notifications = useNotifications();

  const handleCTA = async (notification: Notification) => {
    // Open ActionModal prefilled with CTA payload
    openActionModal({
      actionId: notification.cta_action_id,
      prefill: notification.cta_payload
    });

    // Mark as read
    await markNotificationRead(notification.id);
  };

  return (
    <div>
      {notifications.map(n => (
        <NotificationCard
          key={n.id}
          level={n.level}
          title={n.title}
          body={n.body}
          onCTA={() => handleCTA(n)}
          onDismiss={() => dismissNotification(n.id)}
        />
      ))}
    </div>
  );
}
```

---

## Acceptance Tests

### Ledger Tests

```python
def test_consumption_creates_audit_entry():
    """Record consumption creates ledger entry."""
    response = consume_part(part_id, work_order_id, quantity=2)
    assert response.status_code == 200

    audit = get_latest_audit_entry(entity_type='part', entity_id=part_id)
    assert audit['action'] == 'record_part_consumption'
    assert audit['old_values']['quantity_on_hand'] == 5
    assert audit['new_values']['quantity_on_hand'] == 3
    assert audit['signature'] == {}

def test_large_adjustment_has_signature():
    """Large adjustment must have signature in ledger."""
    response = adjust_stock(part_id, new_quantity=1, reason='Damage', signature=VALID_SIGNATURE)
    assert response.status_code == 200

    audit = get_latest_audit_entry(entity_type='part', entity_id=part_id)
    assert audit['action'] == 'adjust_stock_quantity'
    assert audit['signature'] != {}
    assert audit['signature']['signature_type'] == 'stock_adjustment'

def test_ledger_yacht_isolation():
    """Cannot view other yacht's ledger entries."""
    audit_entries = get_audit_entries(entity_type='part', jwt=YACHT_A_JWT)
    yacht_ids = set(e['yacht_id'] for e in audit_entries)
    assert len(yacht_ids) == 1
    assert YACHT_B_ID not in yacht_ids
```

### Notification Tests

```python
def test_low_stock_creates_notification():
    """Stock below minimum creates notification for chief_engineer."""
    # Consume to trigger low stock
    consume_part(part_id, work_order_id, quantity=4)  # 5 -> 1, min=3

    notifications = get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock')
    assert len(notifications) >= 1
    assert notifications[0]['source_id'] == str(part_id)
    assert notifications[0]['level'] == 'warning'

def test_notification_idempotency():
    """Same alert not sent twice in one day."""
    consume_part(part_id, work_order_id, quantity=1)  # Trigger 1
    notifs_1 = get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock')

    consume_part(part_id, work_order_id, quantity=1)  # Trigger 2
    notifs_2 = get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock')

    # Should not have duplicate
    assert len(notifs_2) == len(notifs_1)

def test_critical_stock_out():
    """Zero stock creates critical notification."""
    consume_part(part_id, work_order_id, quantity=5)  # 5 -> 0

    notifications = get_notifications(user_id=CAPTAIN_ID, topic='stock_out')
    assert len(notifications) >= 1
    assert notifications[0]['level'] == 'critical'

def test_cta_prefills_action():
    """CTA payload prefills action modal correctly."""
    notification = get_notifications(user_id=CHIEF_ENG_ID, topic='low_stock')[0]

    assert notification['cta_action_id'] == 'add_to_shopping_list'
    assert 'part_id' in notification['cta_payload']
    assert 'quantity_requested' in notification['cta_payload']
```

---

**END OF LEDGER & NOTIFICATIONS DESIGN**
