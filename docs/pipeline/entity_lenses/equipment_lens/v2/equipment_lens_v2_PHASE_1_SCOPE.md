# Equipment Lens v2 - PHASE 1: SCOPE

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 1 defines the complete scope of the Equipment Lens:
- Who are the users?
- What actions exist?
- What roles can do what?
- What scenarios must we support?

---

## USER PERSONAS

### Who Uses Equipment?

| Persona | Role(s) | Location | Device | Primary Use Cases |
|---------|---------|----------|--------|-------------------|
| **Deckhand** | `deckhand` | Deck, tender bay | Phone (wet) | Report issues, take photos |
| **Interior Crew** | `steward`, `chef` | Interior spaces | Phone | Report galley/laundry equipment issues |
| **Engineer** | `engineer` | Engine room | Tablet (oily) | Status updates, fault logging, WO creation |
| **ETO** | `eto` | Bridge, AV rooms | Laptop/Tablet | Systems status, troubleshooting |
| **Chief Engineer** | `chief_engineer` | ECR, office | Laptop | Oversight, approvals, planning |
| **Chief Officer** | `chief_officer` | Bridge, deck | Tablet | Safety equipment, deck machinery |
| **Captain** | `captain` | Bridge, everywhere | Any | Authority, decommission approval |
| **Manager** | `manager` | Shore office | Desktop | Fleet oversight, compliance, decommission |

### User Mental States

| Context | State | System Implications |
|---------|-------|---------------------|
| Breakdown/Alarm | High stress | Fast photo capture, minimal fields, one-tap status |
| Routine inspection | Methodical | Checklist view, bulk status review |
| Pre-departure | Time pressure | Quick attention scan, critical items |
| Post-maintenance | Documentation | Completion notes, status restoration |
| Handover | Transition | History view, pending items summary |
| Planning | Analytical | Parts BOM, maintenance history, scheduling |

---

## ACTION INVENTORY

### Mutation Actions (7)

| # | Action ID | Label | Variant | Signed |
|---|-----------|-------|---------|--------|
| 1 | `update_equipment_status` | Update Status | MUTATE | NO |
| 2 | `add_equipment_note` | Add Note | MUTATE | NO |
| 3 | `attach_file_to_equipment` | Attach Photo/Document | MUTATE | NO |
| 4 | `create_work_order_for_equipment` | Create Work Order | MUTATE | NO |
| 5 | `link_part_to_equipment` | Link Part to BOM | MUTATE | NO |
| 6 | `flag_equipment_attention` | Flag/Clear Attention | MUTATE | NO |
| 7 | `decommission_equipment` | Decommission Equipment | SIGNED | **YES** |

### Read Actions (3)

| # | Action ID | Label | Notes |
|---|-----------|-------|-------|
| 8 | `view_equipment_faults` | View Faults | Escape hatch to Fault Lens |
| 9 | `view_equipment_work_orders` | View Work Orders | Escape hatch to WO Lens |
| 10 | `view_equipment_parts` | View Parts BOM | Escape hatch to Part Lens |

---

## ROLE PERMISSION MATRIX

### Legend
- ✅ = Allowed
- ❌ = Denied (RLS blocks)
- 🔐 = Requires signature

### Matrix

| Role | View | Note | Attach | Status | WO | Parts | Attn | Decomm |
|------|------|------|--------|--------|----|----|------|--------|
| `deckhand` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `steward` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `chef` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `engineer` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `eto` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `chief_engineer` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `chief_officer` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `chief_steward` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `purser` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `captain` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔐 |
| `manager` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔐 |

### Role Groups (for RLS)

```sql
-- CREW (view + note + attach only)
'deckhand', 'steward', 'chef', 'chief_steward', 'purser'

-- ENGINEERS (status + WO + parts)
'engineer', 'eto', 'chief_engineer'

-- OFFICERS (status + WO, no parts)
'chief_officer'

-- AUTHORITY (all including signed decommission)
'captain', 'manager'
```

---

## SCENARIO CATEGORIES

### Category 1: Status Management
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 1.1 | Engineer marks equipment failed | engineer | Status=failed, attention_flag=true |
| 1.2 | Crew attempts status change | deckhand | 403 Denied |
| 1.3 | Restore equipment to operational | engineer | Status=operational, flag optionally cleared |
| 1.4 | Set equipment to maintenance | chief_engineer | Status=maintenance |
| 1.5 | Invalid status transition (decomm → operational) | manager | 400 Invalid |

### Category 2: Notes and Attachments
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 2.1 | Deckhand adds observation note | deckhand | Note created |
| 2.2 | Engineer attaches breakdown photo | engineer | Photo uploaded, linked |
| 2.3 | Note with requires_ack flag | engineer | Note created, notification triggered |
| 2.4 | Attach video from inspection | eto | Video uploaded (within size limit) |
| 2.5 | Attach file exceeding size limit | any | 400 File too large |

### Category 3: Work Order Integration
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 3.1 | Create corrective WO for failed equipment | engineer | WO created, fault auto-created |
| 3.2 | Create preventive WO for equipment | chief_engineer | WO created, no fault |
| 3.3 | Crew attempts WO creation | deckhand | 403 Denied |
| 3.4 | View equipment work order history | any | List returned |

### Category 4: Decommission (Signed)
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 4.1 | Manager decommissions with signature | manager | Equipment decommissioned, audit signed |
| 4.2 | Captain decommissions with signature | captain | Equipment decommissioned, audit signed |
| 4.3 | Engineer attempts decommission | chief_engineer | 403 Denied |
| 4.4 | Decommission without signature | manager | 400 Signature required |
| 4.5 | Attempt to un-decommission | manager | 400 Terminal state |

### Category 5: Isolation and Security
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 5.1 | Cross-yacht equipment access | any | 404 Not found |
| 5.2 | Anon access to equipment | anon | 401 Unauthorized |
| 5.3 | Service role bypass | service_role | Full access |

### Category 6: Hierarchy and Search
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 6.1 | Query by equipment code | any | Equipment found |
| 6.2 | Query by location | any | Filtered list |
| 6.3 | Query by system type | any | Filtered list |
| 6.4 | View child equipment | any | Hierarchy displayed |
| 6.5 | Attention flag filter | any | Flagged items listed |

### Category 7: Ledger and History
| # | Scenario | Primary Role | Expected Outcome |
|---|----------|--------------|------------------|
| 7.1 | View equipment audit history | any | Audit entries returned |
| 7.2 | Verify non-signed audit has {} signature | any | signature = '{}' |
| 7.3 | Verify signed audit has JSON signature | any | signature = {full payload} |

---

## ACCEPTANCE CRITERIA OUTLINE

### Must Pass (Blocking)

1. **Role Gating**: All role restrictions enforced per matrix
2. **RLS Isolation**: Cross-yacht access returns 404
3. **Status Lifecycle**: Valid transitions allowed, invalid blocked
4. **Signature Enforcement**: Decommission requires signature or 400
5. **Audit Invariant**: All mutations create audit entry with signature (empty or full)
6. **Error Mapping**: All client errors return 4xx, never 500

### Should Pass (Important)

1. **Notification Triggers**: Critical failures generate notifications
2. **Ledger Completeness**: All events recorded with full context
3. **Storage Path Validation**: Files stored at correct yacht-scoped path
4. **Performance**: Queries return within 500ms

### Nice to Have (Polish)

1. **Hierarchy Queries**: Recursive CTE performs well
2. **Bulk Operations**: Attention scan handles 100+ items
3. **File Type Validation**: MIME types enforced

---

## NEXT PHASE

Proceed to **PHASE 2: DB TRUTH** to:
- Document exact production schema
- Verify column types and constraints
- Identify any schema gaps
- Confirm RLS policy deployment

---

**END OF PHASE 1**
