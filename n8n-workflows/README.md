# n8n Workflows for CelesteOS

## Overview

This folder contains n8n workflows for the predictive maintenance engine and dashboard API endpoints.

**Base URL:** `https://api.celeste7.ai/webhook`

---

## Workflows

### 1. Predictive Engine - MVP1 (Cron-Based)

| File | Trigger | Purpose |
|------|---------|---------|
| `predictive-engine-workflow.json` | Cron (every 6 hours) | Calculate risk scores for all equipment |
| `predictive-webhook-trigger.json` | POST `/predictive-run` | On-demand risk calculation |

### 2. Predictive Engine - MVP2 (Event-Driven)

| File | Trigger | Purpose |
|------|---------|---------|
| `predictive-event-handler.json` | POST `/internal/predictive-event` | Receive events from DB triggers |
| `predictive-recompute-equipment.json` | POST `/internal/predictive-recompute` | Recompute single equipment risk |
| `micro-action-dispatcher.json` | POST `/internal/micro-action-dispatch` | Trigger actions on threshold crossing |
| `predictive-cron-safety-pass.json` | Cron (daily) | Fallback full recalculation |

### 3. Dashboard API Endpoints

| File | Endpoint | Widget |
|------|----------|--------|
| `dashboard-predictive-top-risks.json` | GET `/v1/predictive/top-risks` | PredictiveOverview |
| `dashboard-work-orders-status.json` | GET `/v1/work-orders/status` | WorkOrderStatus |
| `dashboard-inventory-low-stock.json` | GET `/v1/inventory/low-stock` | InventoryStatus |
| `dashboard-equipment-overview.json` | GET `/v1/equipment/overview` | EquipmentOverview |

---

## Setup Instructions

### 1. Tables Already Exist

Tables `predictive_state` and `predictive_insights` already exist in Supabase.
**No SQL setup needed.**

See `schema_reference.sql` for table definitions and column types.

### 2. Add Postgres Credentials in n8n

In n8n, go to **Credentials** → **New** → **Postgres**

```
Name: Supabase Postgres
Host: db.vzsohavtuotocgrfkfyd.supabase.co
Database: postgres
User: postgres
Password: [your database password]
Port: 5432
SSL: Require
```

### 3. Import Workflow

1. Go to n8n dashboard
2. Click **Import from File**
3. Select `predictive-engine-workflow.json`
4. Update credential references if needed

### 4. Activate Workflow

Toggle the workflow to **Active**.

## Workflow Flow

```
[Every 6 Hours]
      │
      ├──► [Get All Equipment]
      ├──► [Get Fault Stats]
      ├──► [Get Work Order Stats]
      └──► [Get Notes Stats]
              │
              ▼
        [Merge All Data]
              │
              ▼
      [Calculate Risk Scores]
        risk = 0.35*faults + 0.25*work_orders + 0.15*notes + 0.15*corrective + 0.10*criticality
              │
              ▼
    [Save to predictive_state]
              │
              ▼
      [Filter High Risk ≥0.6]
              │
              ▼
      [Generate Insights]
              │
              ▼
    [Save to predictive_insights]
```

## Tables Used

### Reads From:
- `equipment` - equipment list with criticality
- `faults` - fault events (90-day window)
- `work_orders` - maintenance tasks, overdue status
- `notes` - crew notes linked to equipment

### Writes To:
- `predictive_state` - risk_score, confidence, contributing_factors (jsonb), last_calculated_at
- `predictive_insights` - title, description, recommendation, severity, metadata (jsonb)

## Risk Score Formula

```
risk_score =
  0.35 × fault_signal +
  0.25 × work_order_signal +
  0.15 × notes_signal +
  0.15 × corrective_signal +
  0.10 × criticality_signal
```

### Signal Normalization:
- `fault_signal`: faults in 90 days / 10 (capped at 1.0)
- `work_order_signal`: overdue count / 5 (capped at 1.0)
- `notes_signal`: note count / 10 (capped at 1.0)
- `corrective_signal`: corrective work orders / 5 (capped at 1.0)
- `criticality_signal`: high=1.0, medium=0.5, low=0.2

### Risk Categories:
- 0.75+ = HIGH (critical)
- 0.60-0.74 = EMERGING (high)
- 0.40-0.59 = MONITOR (medium)
- 0.00-0.39 = NORMAL (low)

## Manual Trigger

To run manually, click **Execute Workflow** in n8n.

## Webhook Trigger (Optional)

Add a Webhook node if you want to trigger via API:
```
POST https://api.celeste7.ai/webhook/predictive-run
```

---

## Dashboard API Response Formats

### GET /v1/predictive/top-risks
```json
{
  "risks": [
    {
      "equipment_id": "uuid",
      "equipment_name": "HVAC Chiller #3",
      "risk_score": 0.78,
      "summary": "High fault frequency, Overdue maintenance",
      "contributing_factors": ["5 faults in 90 days", "2 overdue tasks"]
    }
  ]
}
```

### GET /v1/work-orders/status
```json
{
  "total": 42,
  "overdue": 3,
  "in_progress": 8,
  "completed_this_week": 12,
  "overdue_items": [
    {
      "id": "uuid",
      "title": "Replace HVAC filters",
      "equipment_name": "HVAC System",
      "days_overdue": 5
    }
  ]
}
```

### GET /v1/inventory/low-stock
```json
{
  "low_stock_count": 5,
  "on_order": 8,
  "total_parts": 234,
  "low_stock_items": [
    {
      "id": "uuid",
      "name": "Racor 2040 Filter",
      "part_number": "2040N2",
      "quantity": 1,
      "min_quantity": 4,
      "system": "Fuel System"
    }
  ]
}
```

### GET /v1/equipment/overview
```json
{
  "total": 156,
  "critical": 12,
  "operational": 144,
  "needs_attention": 8
}
```

---

## MVP2 Event-Driven Architecture

### Flow
```
[Database Event: fault/wo/note/part change]
    ↓
[Supabase Trigger → HTTP POST]
    ↓
[predictive-event-handler]
    ↓
[predictive-recompute-equipment]
    ├── Query signals for SINGLE equipment
    ├── Calculate risk score
    ├── UPSERT predictive_state
    └── Check threshold crossing
          ↓
    [If crossed → micro-action-dispatcher]
          ├── Insert handover_items (critical/high)
          ├── Create notifications (critical)
          ├── Flag equipment attention (critical)
          └── Add search_suggestions (high/elevated)
```

### Events Supported
| Event | Source | Trigger |
|-------|--------|---------|
| `fault_created` | `faults` | INSERT |
| `fault_resolved` | `faults` | UPDATE (status→resolved) |
| `wo_created` | `work_orders` | INSERT |
| `wo_updated` | `work_orders` | UPDATE |
| `wo_overdue` | `work_orders` | due_date < NOW |
| `wo_completed` | `work_orders` | UPDATE (status→completed) |
| `note_added` | `notes` | INSERT (where equipment_id) |
| `part_used` | `parts` | UPDATE (quantity decreased) |

### Threshold Actions
| Threshold | Severity | Actions |
|-----------|----------|---------|
| ≥0.75 | critical | handover + notification + equipment_flag |
| ≥0.60 | high | handover + search_priority |
| ≥0.45 | elevated | search_priority |

### Setup MVP2
1. Run `supabase/migrations/predictive_event_triggers.sql` in Supabase
2. Import all MVP2 workflows into n8n
3. Activate workflows
4. Test with: `curl -X POST https://api.celeste7.ai/webhook/internal/predictive-event -d '{"event":"fault_created","equipment_id":"...","yacht_id":"..."}'`
