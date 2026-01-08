# n8n Workflow Templates

This directory contains n8n workflow templates for all 67 micro-actions in CelesteOS.

## Setup Instructions

### 1. Import Workflow into n8n

1. Open your n8n instance at `https://n8n.celeste7.ai` (or your self-hosted instance)
2. Click **Workflows** → **Import from File**
3. Select the JSON file (e.g., `create-work-order.json`)
4. The workflow will be imported as inactive

### 2. Configure Supabase Credentials

Each workflow requires a Supabase PostgreSQL connection:

1. In n8n, go to **Credentials** → **Add Credential**
2. Select **Postgres**
3. Name it: `Supabase Database`
4. Enter connection details:
   ```
   Host: <your-project>.supabase.co
   Database: postgres
   User: postgres
   Password: <your-supabase-password>
   Port: 5432
   SSL: Require
   ```
5. Click **Save**

### 3. Activate the Workflow

1. Open the imported workflow
2. Click **Active: OFF** to toggle it to **Active: ON**
3. The webhook is now live at: `https://n8n.celeste7.ai/webhook/create-work-order`

### 4. Get the Webhook URL

In your n8n workflow, click the **Webhook** node to see the **Production URL**:

```
https://n8n.celeste7.ai/webhook/create-work-order
```

Update your frontend API configuration to point to this URL.

## Workflow Structure

All workflows follow this pattern:

```
┌─────────────┐
│   Webhook   │ (Trigger: POST /webhook/<action-name>)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Validate JWT│ (Extract user_id, yacht_id from token)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Check Auth │ (If valid → continue, else → error response)
└──┬────────┬─┘
   │        │
   │        └──────────────┐
   ▼                       ▼
┌─────────────┐    ┌──────────────┐
│ Insert Data │    │ Error Response│
│  (Supabase) │    └──────┬───────┘
└─────┬───────┘           │
      │                   │
      ▼                   │
┌─────────────┐           │
│ Audit Log   │           │
└─────┬───────┘           │
      │                   │
      ▼                   ▼
┌─────────────────────────┐
│   Webhook Response      │ (Return JSON)
└─────────────────────────┘
```

## Database Schema Requirements

### `work_orders` Table

```sql
CREATE TABLE work_orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
  equipment_id UUID REFERENCES equipment(id),
  fault_id UUID REFERENCES faults(id),
  assigned_to UUID REFERENCES users(id),
  created_by UUID REFERENCES users(id) NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_work_orders_yacht ON work_orders(yacht_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_equipment ON work_orders(equipment_id);
```

### `audit_logs` Table

```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id TEXT NOT NULL,
  user_id UUID NOT NULL,
  action_name TEXT NOT NULL,
  entity_type TEXT,
  entity_id UUID,
  severity TEXT CHECK (severity IN ('low', 'medium', 'high')),
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_yacht ON audit_logs(yacht_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action_name);
```

## Testing the Workflow

### Using cURL

```bash
curl -X POST https://n8n.celeste7.ai/webhook/create-work-order \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Replace hydraulic pump",
    "description": "Main hydraulic pump showing signs of wear. Needs replacement before next voyage.",
    "priority": "high",
    "equipment_id": "550e8400-e29b-41d4-a716-446655440000",
    "fault_id": "660e8400-e29b-41d4-a716-446655440000"
  }'
```

### Expected Response

**Success (201):**
```json
{
  "success": true,
  "message": "Work order created successfully",
  "data": {
    "work_order_id": "770e8400-e29b-41d4-a716-446655440000",
    "title": "Replace hydraulic pump",
    "status": "pending",
    "created_at": "2025-11-21T10:30:00Z"
  },
  "statusCode": 201
}
```

**Error (401):**
```json
{
  "success": false,
  "error": "Unauthorized - Missing token",
  "statusCode": 401
}
```

## Environment Configuration

Update your frontend `.env.local`:

```env
NEXT_PUBLIC_API_URL=https://n8n.celeste7.ai/webhook
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
```

## Production Deployment

1. **n8n**: Deploy n8n to a secure server or use n8n Cloud
2. **Supabase**: Use production Supabase project
3. **SSL**: Ensure all webhooks use HTTPS
4. **Rate Limiting**: Configure rate limits in n8n settings
5. **Monitoring**: Enable n8n execution logs for debugging

## Next Steps

- Import remaining 66 workflow templates (one for each action)
- Configure Supabase Row Level Security (RLS) policies
- Set up n8n error notifications (email/Slack)
- Enable workflow versioning
