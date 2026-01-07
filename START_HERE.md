# Start Here - CelesteOS Development Guide

**Welcome to CelesteOS!** This guide will help you get up and running quickly.

---

## What is CelesteOS?

CelesteOS is a cloud-first AI-driven engineering intelligence platform for superyachts. It provides:
- **Semantic search** across all vessel documentation
- **67 micro-actions** for maintenance, inventory, compliance, and procurement
- **AI-powered diagnostics** and predictive maintenance
- **Handover generation** for crew transitions

---

## Quick Start

### 1. Understand the Architecture

**Read this first:** `docs/ARCHITECTURE_UNIFIED.md`

**Key concepts:**
- **Micro-actions**: 67 atomic operations (create work order, diagnose fault, etc.)
- **Card types**: 12 entity types (fault, work_order, equipment, etc.)
- **Action router**: Python backend that validates and dispatches actions
- **n8n workflows**: 67 workflows that execute actions
- **Unified contract**: All actions follow the same JSON envelope

### 2. Set Up Your Development Environment

#### Prerequisites
- **Node.js** 18+ (for frontend)
- **Python** 3.11+ (for backend)
- **PostgreSQL** 15+ (via Supabase or local)
- **n8n** (self-hosted or cloud)

#### Clone & Install

```bash
# Clone repository
git clone <repository-url>
cd Cloud_PMS

# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

#### Environment Setup

```bash
# Copy environment templates
cp .env.example .env
cp frontend/.env.example frontend/.env.local

# Edit .env files with your credentials:
# - SUPABASE_URL
# - SUPABASE_ANON_KEY
# - N8N_WEBHOOK_BASE_URL
```

### 3. Run the Development Servers

#### Frontend (Next.js)
```bash
cd frontend
npm run dev
# → Open http://localhost:3000
```

#### Backend (Python)
```bash
cd backend
python -m uvicorn src.action_router.router:app --reload --port 8000
# → API available at http://localhost:8000
```

#### Database
```bash
# Using Supabase: No local setup needed
# Using local PostgreSQL: Run migrations
psql -U postgres -d celesteos < database/migrations/00_enable_extensions.sql
psql -U postgres -d celesteos < database/migrations/01_core_tables_v2_secure.sql
```

---

## Repository Structure

```
Cloud_PMS/
├── docs/                      # 📚 All documentation
│   ├── ARCHITECTURE_UNIFIED.md  # ⭐ Start here for architecture
│   ├── /micro-actions/       # Micro-action specifications
│   ├── /specs/               # API & technical specs
│   ├── /architecture/        # Architecture & design docs
│   └── /domain/              # Domain knowledge (maritime)
│
├── frontend/                  # ⚛️ Next.js 15 + React 19 + TypeScript
│   ├── src/app/              # Pages (App Router)
│   ├── src/components/       # React components
│   ├── src/types/            # TypeScript types (67 actions)
│   ├── src/lib/              # API clients & utilities
│   └── package.json
│
├── backend/                   # 🐍 Python action router
│   ├── src/action_router/    # Router, validators, dispatchers
│   ├── src/integrations/     # Supabase, search, predictive
│   ├── src/middleware/       # Auth middleware
│   └── requirements.txt
│
└── database/                  # 🗄️ PostgreSQL migrations
    ├── migrations/           # SQL migration files
    └── SECURITY_ARCHITECTURE.md
```

---

## Key Files to Understand

### Frontend

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/src/types/actions.ts` | **67 micro-action definitions** | 996 |
| `frontend/src/components/SearchBar.tsx` | Main search interface | 190 |
| `frontend/src/components/ResultCard.tsx` | Dynamic card renderer | 88 |
| `frontend/src/components/MicroActions.tsx` | Action button system | 130 |
| `frontend/src/lib/api.ts` | Typed API client | 169 |
| `frontend/src/lib/auth.ts` | Supabase auth utilities | 158 |

### Backend

| File | Purpose | Lines |
|------|---------|-------|
| `backend/src/action_router/router.py` | Main action router | ~200 |
| `backend/src/action_router/validators/jwt_validator.py` | JWT validation | ~100 |
| `backend/src/action_router/validators/role_validator.py` | RBAC enforcement | ~80 |
| `backend/src/action_router/dispatchers/n8n_dispatcher.py` | n8n webhook dispatcher | ~120 |

### Documentation

| File | Purpose |
|------|---------|
| `docs/ARCHITECTURE_UNIFIED.md` | **Comprehensive architecture** (read first!) |
| `docs/micro-actions/MICRO_ACTION_REGISTRY.md` | 67 micro-action specifications |
| `docs/micro-actions/ACTION_OFFERING_RULES.md` | Intent-based action offering logic |
| `docs/specs/api-spec.md` | REST API specification |

---

## Development Workflow

### 1. Adding a New Micro-Action

**Example:** Add `view_equipment_manual` action

#### Step 1: Define in Type System
**File:** `frontend/src/types/actions.ts`

```typescript
export const ACTION_REGISTRY: Record<MicroAction, ActionMetadata> = {
  // ... existing actions
  view_equipment_manual: {
    action_name: 'view_equipment_manual',
    label: 'View Manual',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'BookOpen',
    description: 'Open equipment manual PDF',
  },
}
```

#### Step 2: Add to Card Offering Map
**File:** `docs/micro-actions/ACTION_OFFERING_MAP.md`

```markdown
### equipment card
- view_equipment_details (always)
- view_equipment_history (always)
- view_equipment_manual (if manual exists) ← ADD THIS
```

#### Step 3: Create n8n Workflow
**Webhook:** `POST /api/actions/view_equipment_manual`

**Workflow nodes:**
1. Webhook (receive request)
2. Validate JWT
3. Query database for manual URL
4. Return presigned S3 URL

#### Step 4: Register in Backend Router
**File:** `backend/src/action_router/registry.py`

```python
ACTION_REGISTRY = {
    # ... existing actions
    'view_equipment_manual': {
        'dispatcher': 'n8n',
        'webhook_path': '/api/actions/view_equipment_manual',
        'validation': ['jwt', 'yacht_isolation'],
    },
}
```

#### Step 5: Test End-to-End
```bash
# 1. Search for equipment
POST /v1/search
{"query": "main engine generator"}

# 2. Receive equipment card with actions
# → Includes view_equipment_manual button

# 3. Click button → executes action
POST /api/actions/view_equipment_manual
{
  "action_name": "view_equipment_manual",
  "user_id": "...",
  "yacht_id": "...",
  "context": {"equipment_id": "..."}
}

# 4. Receive presigned URL
{"success": true, "data": {"manual_url": "https://..."}}
```

### 2. Testing

#### Frontend Tests
```bash
cd frontend
npm test                    # Run all tests
npm test -- SearchBar       # Test specific component
npm run test:coverage       # Coverage report
```

#### Backend Tests
```bash
cd backend
pytest                      # Run all tests
pytest tests/test_auth_middleware.py  # Test specific file
```

### 3. Linting & Formatting

```bash
# Frontend
cd frontend
npm run lint                # ESLint
npm run lint:fix            # Auto-fix issues
npm run format              # Prettier

# Backend
cd backend
black src/                  # Format Python code
pylint src/                 # Lint Python code
```

---

## Common Tasks

### Task: Run Frontend Build

```bash
cd frontend
npm run build
npm run start  # Production build
```

**Expected output:** No TypeScript errors, successful build

### Task: Create a Database Migration

```bash
# 1. Create migration file
touch database/migrations/03_new_feature.sql

# 2. Write migration
-- Example: Add new table
CREATE TABLE new_table (
    id UUID PRIMARY KEY,
    yacht_id UUID REFERENCES yachts(id),
    ...
);

-- Enable RLS
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;

# 3. Test migration
psql -U postgres -d celesteos < database/migrations/03_new_feature.sql

# 4. Add to setup script
# Update database/setup_complete.sql
```

### Task: Add a New Dashboard Widget

```bash
# 1. Create component
touch frontend/src/components/DashboardWidgets/NewWidget.tsx

# 2. Implement
import { Card } from '@/components/ui/card'

export function NewWidget() {
  return (
    <Card>
      <h3>New Widget</h3>
      {/* Widget content */}
    </Card>
  )
}

# 3. Add to dashboard
# Edit frontend/src/app/dashboard/page.tsx
import { NewWidget } from '@/components/DashboardWidgets/NewWidget'

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <WorkOrderStatus />
      <NewWidget />  {/* ← Add here */}
    </div>
  )
}
```

### Task: Debug Action Execution

```bash
# 1. Enable debug logging in backend
# Edit backend/src/action_router/logger.py
logger.setLevel(logging.DEBUG)

# 2. Trigger action from frontend
# Open browser DevTools → Network tab

# 3. Check backend logs
cd backend
tail -f logs/action_router.log

# 4. Check n8n execution logs
# Open n8n UI → Executions tab
```

---

## Troubleshooting

### Frontend won't start

**Error:** `Module not found`
**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend authentication fails

**Error:** `JWT validation failed`
**Solution:**
1. Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`
2. Verify JWT token in browser localStorage
3. Check token expiry (24-hour limit)

### Database connection issues

**Error:** `Connection refused`
**Solution:**
1. Verify Supabase project is active
2. Check firewall rules (allow port 5432)
3. Verify connection string in `.env`

### n8n webhook not responding

**Error:** `Webhook timeout`
**Solution:**
1. Check n8n server is running
2. Verify `N8N_WEBHOOK_BASE_URL` in `.env`
3. Check n8n workflow is activated
4. Review n8n execution logs

---

## Phase 1 Development Priorities

**Goal:** End-to-end flow for 10 critical actions

### Immediate Tasks

1. **Complete 5 n8n Workflows**
   - `create_work_order`
   - `mark_work_order_complete`
   - `add_to_handover`
   - `edit_work_order_details`
   - `edit_invoice_amount`

2. **Build Modal Components**
   - `CreateWorkOrderModal`
   - `ConfirmationDialog`
   - `EditInvoiceModal`

3. **Implement 5 Database Tables**
   - `work_orders`
   - `faults`
   - `parts_inventory`
   - `handovers` + `handover_items`
   - `audit_log`

4. **Test End-to-End**
   - Search → Fault card → Create WO → Database

### Success Criteria

- ✅ User can search for "E047 fault"
- ✅ System returns fault card with actions
- ✅ User can click "Create Work Order"
- ✅ Modal appears with pre-filled context
- ✅ Work order is created in database
- ✅ Audit log records mutation
- ✅ User sees success notification

---

## Resources

### Documentation
- **Architecture:** `docs/ARCHITECTURE_UNIFIED.md`
- **Micro-Actions:** `docs/micro-actions/MICRO_ACTION_REGISTRY.md`
- **API Spec:** `docs/specs/api-spec.md`
- **Security:** `docs/architecture/security.md`

### External Links
- [Next.js Documentation](https://nextjs.org/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [n8n Documentation](https://docs.n8n.io)
- [Tailwind CSS](https://tailwindcss.com/docs)

### Code Style Guides
- **TypeScript:** [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- **Python:** [PEP 8](https://pep8.org/)
- **React:** [Airbnb React Style Guide](https://github.com/airbnb/javascript/tree/master/react)

---

## Need Help?

1. **Check docs first:** `docs/ARCHITECTURE_UNIFIED.md`
2. **Search existing issues:** GitHub Issues
3. **Ask in Slack:** #celesteos-dev channel
4. **Create an issue:** Provide error logs + steps to reproduce

---

## Next Steps

1. ✅ Read `docs/ARCHITECTURE_UNIFIED.md` (30 min)
2. ✅ Set up development environment (1 hour)
3. ✅ Run frontend + backend locally (30 min)
4. ✅ Complete tutorial: Add a new micro-action (2 hours)
5. ✅ Pick a Phase 1 task and start coding!

**Welcome to the team! 🚀**

---

**Last Updated:** 2025-11-21
**Maintained By:** CelesteOS Core Team
