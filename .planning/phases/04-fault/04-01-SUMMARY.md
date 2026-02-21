# Summary: 04-01 Database Schema Verification

**Status:** Complete
**Executed:** 2026-02-19

## One-liner

pms_faults RLS verified: 6 policies, 3 FK constraints, no DELETE policy.

## Verification Results

### RLS Status
```sql
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_faults';
-- Result: true
```

### Policies (6 total)
| Policy | Command |
|--------|---------|
| crew_select_own_yacht_faults | SELECT |
| crew_insert_faults | INSERT |
| fault_writer_update_faults | UPDATE |
| Users can view faults | SELECT |
| Engineers can manage faults | ALL |
| Service role full access faults | ALL |

**No DELETE policy exists** (per doctrine: faults never deleted)

### FK Constraints (3 total)
| Constraint | References |
|------------|------------|
| faults_equipment_id_fkey | pms_equipment |
| faults_work_order_id_fkey | pms_work_orders |
| faults_yacht_id_fkey | yacht_registry |

### Related Tables
- pms_attachments: 9 RLS policies (yacht_isolation + users CRUD + service_role_bypass)
- pms_fault_notes: Table does not exist (notes stored via pms_attachments)

## must_haves Checklist

- [x] pms_faults has RLS enabled
- [x] SELECT policy: crew_select_own_yacht_faults exists
- [x] INSERT policy: crew_insert_faults exists
- [x] UPDATE policy: fault_writer_update_faults exists
- [x] No DELETE policy (confirmed absent)
- [x] FK constraint to pms_equipment verified
- [x] pms_attachments has RLS
