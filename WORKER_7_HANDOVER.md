# Worker 7 - Predictive Engine Handover

**Branch:** `claude/read-repo-01Qpdiy89cgvucpL3gr2fcui`
**Date:** 2024-11-23
**Author:** Claude (AI Worker 7)

---

## Summary

Built the **Predictive Maintenance Engine** for CelesteOS. This calculates equipment risk scores and generates maintenance insights.

**Delivery Format:** n8n workflows (NOT Python server)

---

## Files Created

### n8n Workflows (USE THESE)
```
n8n-workflows/
├── predictive-engine-workflow.json    # Cron: runs every 6 hours
├── predictive-webhook-trigger.json    # Webhook: on-demand trigger
├── create_predictive_tables.sql       # SQL: run in Supabase first
└── README.md                          # Setup instructions
```

### Python Files (DEPRECATED - ignore these)
```
predictive-engine/                      # NOT USING - was built before
├── main.py                            # n8n asked for, so ignore
├── worker.py
├── services/
├── router/
└── ...
```

**The Python `predictive-engine/` folder can be deleted.** We're using n8n instead.

---

## What It Does

```
┌─────────────────────────────────────────────────────────────────┐
│                     PREDICTIVE ENGINE                           │
│                                                                 │
│  INPUT (reads from Supabase):                                   │
│    - equipment                                                  │
│    - faults                                                     │
│    - work_orders                                                │
│    - work_order_history (notes column)                          │
│                                                                 │
│  PROCESS:                                                       │
│    risk = 0.35×faults + 0.25×overdue + 0.15×notes + ...        │
│                                                                 │
│  OUTPUT (writes to Supabase):                                   │
│    - predictive_state (risk scores)                             │
│    - predictive_insights (recommendations)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup Steps

### 1. Create Tables in Supabase

Run `n8n-workflows/create_predictive_tables.sql` in Supabase SQL Editor:

```sql
CREATE TABLE predictive_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID NOT NULL,
    equipment_name TEXT,
    risk_score NUMERIC(5,4) NOT NULL,
    trend VARCHAR(1) NOT NULL DEFAULT '→',
    fault_signal NUMERIC(5,4) DEFAULT 0,
    work_order_signal NUMERIC(5,4) DEFAULT 0,
    crew_signal NUMERIC(5,4) DEFAULT 0,
    part_signal NUMERIC(5,4) DEFAULT 0,
    global_signal NUMERIC(5,4) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_yacht_equipment UNIQUE (yacht_id, equipment_id)
);

CREATE TABLE predictive_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    equipment_id UUID,
    equipment_name TEXT,
    insight_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    summary TEXT NOT NULL,
    explanation TEXT,
    recommended_action TEXT,
    contributing_signals JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Add Postgres Credential in n8n

```
Name: Supabase Postgres
Host: db.vzsohavtuotocgrfkfyd.supabase.co
Database: postgres
User: postgres
Password: [get from Supabase dashboard]
Port: 5432
SSL: Require
```

### 3. Import Workflows

1. Go to n8n (https://api.celeste7.ai or your n8n instance)
2. Import `predictive-engine-workflow.json` (cron)
3. Import `predictive-webhook-trigger.json` (webhook)
4. Link Postgres credentials to each workflow
5. Activate both

### 4. Test Webhook

```bash
curl -X POST https://api.celeste7.ai/webhook/predictive-run \
  -H "Content-Type: application/json" \
  -d '{"yacht_id": "YOUR-YACHT-UUID"}'
```

---

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
| Signal | Calculation | Max |
|--------|-------------|-----|
| fault_signal | fault_count / 10 | 1.0 |
| work_order_signal | overdue_count / 5 | 1.0 |
| notes_signal | note_count / 10 | 1.0 |
| corrective_signal | corrective_count / 5 | 1.0 |
| criticality_signal | high=1, med=0.5, low=0.2 | 1.0 |

### Risk Categories:
| Score | Category |
|-------|----------|
| 0.75+ | HIGH (critical) |
| 0.60-0.74 | EMERGING (high) |
| 0.40-0.59 | MONITOR (medium) |
| 0.00-0.39 | NORMAL (low) |

---

## Tables Required in Supabase

### Must Already Exist (Worker 1):
- `equipment` - id, yacht_id, name, criticality
- `faults` - id, equipment_id, yacht_id, fault_code, detected_at
- `work_orders` - id, equipment_id, yacht_id, status, due_date, type, created_at
- `work_order_history` - id, equipment_id, yacht_id, notes, completed_at

### Created by This Worker:
- `predictive_state` - stores risk scores
- `predictive_insights` - stores recommendations

---

## Known Issues / Limitations

1. **NOT TESTED against live Supabase** - API returned 403 (IP restricted?)
2. **Column names assumed** from `table_configs.md` - may need adjustment
3. **Trend calculation** is placeholder (always `→`) - needs historical comparison
4. **No ML** - purely statistical/rule-based as per spec

---

## What's NOT Done

1. **API endpoints** - Not needed since frontend can query Supabase directly
2. **Python server** - Replaced with n8n workflows
3. **Render.com deployment** - Not needed (using n8n instead)

---

## Commits

```
ae16483 feat(predictive): Add webhook trigger workflow for on-demand computation
3618389 feat(predictive): Add n8n workflow for predictive maintenance engine
f1ac1bf fix(predictive): Query work_order_history.notes instead of non-existent notes table
580f654 feat(predictive): Add GET /v1/predictive/top-risks endpoint
502c7f9 docs: Add Task 7 verification document
```

---

## Questions for Review

1. Should `predictive-engine/` Python folder be deleted?
2. Are the column names in SQL queries correct for your actual tables?
3. Do you need the webhook path to be different from `/webhook/predictive-run`?
4. Should insights be deduplicated (currently creates new row each run)?

---

## Contact

This was built by Claude AI (Worker 7). If issues arise, re-run the Claude session with:
- This handover doc
- Actual Supabase table schemas
- Any error messages from n8n

---

**Ready to merge:** Yes, after Supabase tables are created and n8n credentials configured.
