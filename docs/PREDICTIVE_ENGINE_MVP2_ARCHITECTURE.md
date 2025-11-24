# CelesteOS Predictive Engine - MVP2 Architecture

## Current State (MVP1) - Cron-Based

```
[Cron: Every 6 hours]
    ↓
[Query all equipment]
    ↓
[Calculate risk scores]
    ↓
[Write to predictive_state]
    ↓
[Dashboard pulls via GET endpoints]
```

**Problem:** Reactive, interval-based, user must pull data.

---

## Target State (MVP2) - Event-Driven

```
[Event: fault_created / wo_updated / note_added]
    ↓
[Trigger: Recompute risk for ONLY affected equipment]
    ↓
[Check threshold crossing]
    ↓
[If crossed → Emit INSIGHT]
    ↓
[Micro-action triggers automatically]
```

**Goal:** Proactive, real-time, system pushes insights.

---

## Event Sources

| Event | Source Table | Trigger |
|-------|--------------|---------|
| `fault_created` | `faults` | INSERT |
| `fault_resolved` | `faults` | UPDATE (status → resolved) |
| `wo_created` | `work_orders` | INSERT |
| `wo_overdue` | `work_orders` | UPDATE (due_date < NOW) |
| `wo_completed` | `work_orders` | UPDATE (status → completed) |
| `note_added` | `notes` | INSERT (where equipment_id IS NOT NULL) |
| `part_used` | `parts` | UPDATE (quantity decreased) |
| `sensor_spike` | `sensor_readings` | INSERT (value > threshold) |

---

## Implementation Options

### Option A: Supabase Database Triggers + Edge Functions

```sql
-- Trigger on fault insert
CREATE OR REPLACE FUNCTION on_fault_created()
RETURNS TRIGGER AS $$
BEGIN
  -- Call edge function to recompute risk for this equipment
  PERFORM net.http_post(
    'https://api.celeste7.ai/webhook/predictive-event',
    jsonb_build_object(
      'event', 'fault_created',
      'equipment_id', NEW.equipment_id,
      'yacht_id', NEW.yacht_id
    )
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fault_created_trigger
AFTER INSERT ON faults
FOR EACH ROW EXECUTE FUNCTION on_fault_created();
```

### Option B: Supabase Realtime + n8n Webhook

```javascript
// Frontend or backend listener
supabase
  .channel('faults')
  .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'faults' },
    (payload) => {
      fetch('https://api.celeste7.ai/webhook/predictive-event', {
        method: 'POST',
        body: JSON.stringify({
          event: 'fault_created',
          equipment_id: payload.new.equipment_id
        })
      });
    }
  )
  .subscribe();
```

### Option C: n8n Postgres Trigger Node (Polling)

n8n can poll for new rows every 1-5 minutes - less real-time but simpler.

---

## n8n Workflow: Event-Driven Risk Update

```
[Webhook: POST /predictive-event]
    ↓
[Switch: event type]
    ├── fault_created → weight +0.35
    ├── wo_overdue → weight +0.25
    ├── note_added → weight +0.15
    └── part_used → weight +0.10
    ↓
[Query current risk for equipment_id]
    ↓
[Recalculate risk (incremental)]
    ↓
[Update predictive_state]
    ↓
[Check: risk_score crossed threshold?]
    ├── No → END
    └── Yes → [Emit Insight + Trigger Micro-Actions]
```

---

## Micro-Action Triggers

When risk threshold is crossed (e.g., > 0.6):

| Action | Implementation |
|--------|----------------|
| Add to Handover | INSERT into `handover_items` |
| Push notification | Supabase Realtime / OneSignal |
| Surface in Search | Add to `search_suggestions` with priority |
| Auto-create WO draft | INSERT into `work_orders` (status: draft) |
| Flag equipment card | UPDATE `equipment` set `attention_flag = true` |
| Email digest | Queue for daily summary (not immediate) |

---

## Threshold Configuration

```sql
-- Store in settings table or environment
{
  "risk_thresholds": {
    "critical": 0.75,    -- Immediate action required
    "high": 0.60,        -- Schedule inspection
    "elevated": 0.45,    -- Monitor closely
    "normal": 0.00       -- No action
  },
  "micro_actions": {
    "critical": ["handover", "notification", "wo_draft"],
    "high": ["handover", "search_priority"],
    "elevated": ["search_priority"]
  }
}
```

---

## Migration Path

### Phase 1 (Current - MVP1)
- ✅ Cron-based risk calculation every 6 hours
- ✅ Dashboard GET endpoints
- ✅ Manual refresh

### Phase 2 (MVP2)
- Add database triggers on key tables
- Create `/predictive-event` webhook
- Implement incremental risk update
- Add threshold-based micro-actions

### Phase 3 (MVP3)
- Full Supabase Realtime integration
- Real-time dashboard updates (no polling)
- ML model integration for trend prediction
- Anomaly detection on sensor streams

---

## Files to Create for MVP2

```
n8n-workflows/
├── predictive-event-handler.json     # Webhook for event-driven updates
├── micro-action-dispatcher.json      # Routes insights to actions
└── threshold-config.json             # Configurable thresholds

supabase/
├── migrations/
│   ├── add_fault_trigger.sql
│   ├── add_wo_trigger.sql
│   └── add_note_trigger.sql
└── functions/
    └── predictive-event/index.ts     # Edge function (optional)
```

---

## Summary

| Aspect | MVP1 (Current) | MVP2 (Target) |
|--------|----------------|---------------|
| Trigger | Cron (6 hours) | Event (real-time) |
| Scope | All equipment | Affected equipment only |
| User action | Pull (refresh dashboard) | Push (notifications) |
| Latency | 0-6 hours | Seconds |
| Architecture | Report generator | Predictive OS |

---

## Next Steps

1. **Keep MVP1 workflows active** - they're correct and operational
2. **Add Supabase triggers** on `faults`, `work_orders`, `notes`
3. **Create event handler workflow** in n8n
4. **Implement micro-action dispatcher**
5. **Test with real events**
