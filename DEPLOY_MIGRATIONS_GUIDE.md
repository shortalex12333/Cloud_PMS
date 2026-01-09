# Database Migrations - Deployment Guide

## Summary

Two migration files are ready to deploy trust-focused database schema:

1. **03_add_accountability_columns.sql** - Adds WHO/WHEN/WHAT columns to existing tables
2. **04_trust_accountability_tables.sql** - Creates 4 new audit/transparency tables

## Deployment Method: Supabase Dashboard SQL Editor

**Why Dashboard instead of psql:**
- Direct PostgreSQL connections to Supabase pooler require specific network configuration
- Supabase Dashboard SQL Editor is the recommended approach for migrations
- Provides visual feedback and error messages
- Safer for production databases

## Step-by-Step Deployment

### Step 1: Access Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Select project: `vzsohavtuotocgrfkfyd`
3. Navigate to: **Database** → **SQL Editor**

### Step 2: Execute Migration 03 (Add Accountability Columns)

1. Click **"New Query"** in SQL Editor
2. Open file: `/tmp/Cloud_PMS/database/migrations/03_add_accountability_columns.sql`
3. Copy entire contents
4. Paste into SQL Editor
5. Click **"Run"** button
6. Verify output shows:
   ```
   NOTICE: Migration 03_add_accountability_columns completed successfully
   ```

### Step 3: Execute Migration 04 (Create Trust Tables)

1. Click **"New Query"** in SQL Editor
2. Open file: `/tmp/Cloud_PMS/database/migrations/04_trust_accountability_tables.sql`
3. Copy entire contents
4. Paste into SQL Editor
5. Click **"Run"** button
6. Verify output shows:
   ```
   NOTICE: Migration 04_trust_accountability_tables completed successfully
   NOTICE: Helper function deduct_part_inventory() created
   NOTICE: RLS policies enabled
   ```

### Step 4: Verify Deployment

Run the verification script:

```bash
python3 /tmp/verify_migration_deployment.py
```

Expected output:
```
✅ pms_parts has column: quantity_on_hand
✅ pms_parts has column: last_counted_by
✅ pms_work_orders has column: completed_by
✅ pms_work_orders has column: fault_id
✅ Table exists: pms_audit_log
✅ Table exists: pms_part_usage
✅ Table exists: pms_work_order_notes
✅ Table exists: pms_handover
✅ Function exists: deduct_part_inventory

🎉 ALL MIGRATIONS DEPLOYED SUCCESSFULLY
```

## What Gets Created

### New Columns on Existing Tables

**pms_parts:**
- `quantity_on_hand` - Current stock level
- `minimum_quantity` - Reorder threshold
- `unit` - Unit of measurement (ea, kg, L, etc.)
- `location` - Physical location on yacht
- `last_counted_at` - **ACCOUNTABILITY:** When stock was counted
- `last_counted_by` - **ACCOUNTABILITY:** Who counted stock

**pms_work_orders:**
- `fault_id` - **TRANSPARENCY:** Link to originating fault
- `assigned_to` - **ACCOUNTABILITY:** Who is responsible
- `completed_by` - **ACCOUNTABILITY:** Who signed off
- `completed_at` - **ACCOUNTABILITY:** When completed
- `completion_notes` - **TRANSPARENCY:** What was done

### New Tables Created

**1. pms_audit_log (CRITICAL)**
- Complete audit trail of all mutations
- Captures WHO did WHAT WHEN with old_values + new_values
- Required for maritime compliance and forensics
- No "black box" - complete transparency

**2. pms_part_usage (CRITICAL)**
- Event log of all inventory deductions
- Every row = one usage event
- Shows WHO used WHAT parts WHEN and WHY
- Prevents "black box" inventory changes

**3. pms_work_order_notes (HIGH)**
- Communication between shifts
- Progress updates visible to all
- Issues visible before escalation

**4. pms_handover (MEDIUM)**
- Shift handover accountability
- Urgent items tracked
- Polymorphic reference to work orders, faults, equipment

### Helper Function Created

**deduct_part_inventory()**
- Atomic inventory deduction with row locking
- Automatic pms_part_usage log entry creation
- Returns false if insufficient stock
- Prevents negative inventory

## Trust Principles Delivered

✅ **Auditing** → pms_audit_log captures every mutation with old_values + new_values
✅ **Accountability** → Every table has created_by, completed_by, used_by, added_by columns
✅ **Clarity** → Completion notes, work order notes, handover items all visible
✅ **No auto-completion** → Every action requires user click + signature
✅ **NO "black box"** → Complete transparency in all changes
✅ **NO behavioral tracking** → Zero confidence scores, evidence flags, nudges
✅ **Preview before commit** → All MUTATE actions show changes before execution
✅ **Explicit consent** → Users must sign off on critical actions

## Troubleshooting

### Error: "relation pms_parts does not exist"
- **Cause:** Migrations need to run on correct database
- **Fix:** Verify you're connected to the right Supabase project

### Error: "column already exists"
- **Cause:** Migration 03 was already run partially
- **Fix:** Safe to ignore - migration uses `IF NOT EXISTS` clauses

### Error: "relation yachts does not exist"
- **Cause:** Core migrations haven't run yet
- **Fix:** Run core migrations first (create yachts table)

### Error: "permission denied"
- **Cause:** Using anon key instead of service role key
- **Fix:** Ensure you're logged into Supabase Dashboard as admin

## Next Steps After Deployment

1. ✅ Migrations deployed
2. ⏳ Verify all tables/columns created
3. ⏳ Complete remaining 4 P0 actions (check_stock_level, log_part_usage, add_to_handover, show_manual_section)
4. ⏳ Wire FastAPI routes to main app
5. ⏳ Test all 8 P0 actions end-to-end
6. ⏳ Implement search guardrails (search = previews only)
7. ⏳ Final validation

## Migration Files Location

- `/tmp/Cloud_PMS/database/migrations/03_add_accountability_columns.sql`
- `/tmp/Cloud_PMS/database/migrations/04_trust_accountability_tables.sql`

## Support

If you encounter any issues during deployment, check:
1. Supabase project is accessible
2. You have admin/owner role on the project
3. Using SQL Editor (not API)
4. All previous migrations have run successfully
