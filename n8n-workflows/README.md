# Predictive Maintenance Engine - n8n Workflow

## Overview

This n8n workflow calculates equipment risk scores and generates predictive insights.

**Runs:** Every 6 hours (configurable)

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
