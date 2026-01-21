# E012: CANONICAL USER JOURNEYS

**Date:** 2026-01-21
**Phase:** 9 - Journey, Trigger, and Threshold Validation
**Status:** COMPLETE

---

## Purpose

Define real user journeys (not actions) to validate that the system surfaces the right actions at the right time.

---

## Journey Format

Each journey defines:
- **Starting Context**: What the user sees/knows before starting
- **User Intent**: What they're trying to accomplish
- **Expected System Response**: What the system should do
- **Expected Actions Surfaced**: Which actions should appear and in what order

---

## Journey Set (12 Canonical Journeys)

---

### J01: Engineer Reports Fault from Memory

**Persona**: Chief Engineer, at sea

**Starting Context:**
- User on dashboard, no cards open
- Recalls issue from walk-around inspection
- Knows equipment name: "starboard generator"

**User Intent:**
Report a problem discovered during physical inspection

**Expected System Response:**
1. Search resolves "starboard generator" to equipment entity
2. Equipment card opens
3. Fault reporting flow initiates

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | report_fault | Strong equipment context + no existing fault |
| Secondary | view_equipment_details | Auto-run on card mount |
| Available | create_work_order | Equipment context exists |
| Available | add_to_handover | Entity context exists |

**Success Criteria:**
- report_fault is PRIMARY (most prominent)
- No work order actions until fault exists
- No fault detail actions (no fault yet)

---

### J02: Engineer Reports Fault While Viewing Equipment

**Persona**: ETO, in port

**Starting Context:**
- Equipment card already open (e.g., from drill-down)
- User notices problem or was asked to log one

**User Intent:**
Log a fault against the equipment they're currently viewing

**Expected System Response:**
1. report_fault already visible
2. Single click creates fault
3. System links fault to current equipment automatically

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | report_fault | Equipment context + no active fault |
| Secondary | create_work_order | Skip fault, go direct to WO |
| Available | view_equipment_manual | If has_manual=true |
| Available | view_linked_faults | See existing issues |

**Success Criteria:**
- equipment_id auto-populated in fault creation
- No manual entry of equipment reference
- Fault-to-equipment link created automatically

---

### J03: Captain Reviews Status, Drills Into History

**Persona**: Captain, at sea during passage

**Starting Context:**
- Dashboard showing status overview
- Sees "3 open faults" indicator
- Wants details

**User Intent:**
Understand current technical status, drill into specifics if concerning

**Expected System Response:**
1. Fault list surfaces on dashboard
2. Clicking fault shows fault detail
3. History context builds as user drills down

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | view_fault_detail | READ action, safe default |
| Available | acknowledge_fault | If not yet acknowledged |
| Suppressed | close_fault | Captain not primary resolver |
| Suppressed | diagnose_fault | Auto-runs, no button needed |

**Success Criteria:**
- Read actions primary for Captain role
- Mutation actions available but not primary
- No engineer-specific actions prominent

---

### J04: Manager Reviews Overdue Items

**Persona**: Fleet Manager, shore-side

**Starting Context:**
- Multi-yacht dashboard
- Filters to "overdue work orders"
- Sees list

**User Intent:**
Identify blockers, escalate or reassign as needed

**Expected System Response:**
1. Overdue items highlighted
2. Drill into specific work order
3. Reassignment options available

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | view_work_order_detail | Start with understanding |
| Primary | assign_work_order | HOD role, reassignment power |
| Available | add_wo_note | Log escalation context |
| Available | close_work_order | HOD can force-close |

**Success Criteria:**
- assign_work_order visible (Manager is HOD)
- No engineer-level detail actions prominent
- Escalation path clear

---

### J05: Engineer Hands Over Incomplete Work

**Persona**: Chief Engineer, end of watch

**Starting Context:**
- Has open work order in progress
- Watch ending, task not complete
- Needs to brief relief engineer

**User Intent:**
Document current status for handover, ensure continuity

**Expected System Response:**
1. Work order context preserved
2. Handover action prominent
3. Notes capture current state

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | add_to_handover | Strong WO context + handover intent |
| Secondary | add_wo_note | Document current state |
| Available | update_work_order | Update status/priority |
| Suppressed | close_work_order | Work incomplete |

**Success Criteria:**
- add_to_handover pulls work order context automatically
- Note added to WO history
- Handover item created with link to WO

---

### J06: Engineer Links Email to Work

**Persona**: ETO, in port

**Starting Context:**
- Email received from supplier about part delivery
- Needs to attach to existing work order

**User Intent:**
Connect external communication to internal work tracking

**Expected System Response:**
1. Email entity recognized
2. Work order selection offered
3. Link established

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | add_note_to_work_order | Email content as note |
| Available | add_to_handover | Capture for shift briefing |
| Available | update_work_order | Status change if relevant |

**Success Criteria:**
- Email content extractable
- Work order searchable/selectable
- Link created with audit trail

---

### J07: Engineer Views Manual, Performs Action

**Persona**: Engineer, at sea

**Starting Context:**
- Troubleshooting equipment
- Opens equipment manual section
- Follows procedure, completes task

**User Intent:**
Reference documentation, then record completion

**Expected System Response:**
1. Manual section displays
2. Task completion actions appear
3. Documentation flow natural

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | show_manual_section | User's explicit intent |
| Secondary | report_fault | If procedure reveals issue |
| Available | add_wo_note | Log procedure execution |
| Available | create_work_order | If maintenance identified |

**Success Criteria:**
- Manual content displays (data-dependent)
- Return to work context seamless
- Action recording optional but accessible

---

### J08: Engineer Searches Generic Term

**Persona**: Engineer, at sea

**Starting Context:**
- Dashboard or search interface
- Types "pump" or "filter"
- Many matches possible

**User Intent:**
Find specific equipment or issue among many similar items

**Expected System Response:**
1. Results grouped by type (equipment, faults, work orders)
2. Disambiguation clear
3. Recent/relevant items prioritized

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| None Primary | - | Ambiguous context, no single action fits |
| Per-Result | view_equipment_details | On equipment results |
| Per-Result | view_fault_detail | On fault results |
| Per-Result | view_work_order_detail | On WO results |

**Success Criteria:**
- No premature action commitment
- Read-only actions on results
- User must select before mutations available

---

### J09: User Pastes Ambiguous Input

**Persona**: Any role

**Starting Context:**
- Copies text from message/email
- Pastes "broken" or "not working" or "check generator"
- Intent unclear

**User Intent:**
Get system help interpreting vague input

**Expected System Response:**
1. Intent classified as ambiguous
2. Clarification offered
3. No destructive actions surfaced

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | (search/clarify) | System asks for more context |
| Suppressed | All mutations | Insufficient signal |

**Success Criteria:**
- System does NOT guess and create
- Clarification flow activates
- User guided to specificity

---

### J10: User Performs Follow-Up Query

**Persona**: Any role

**Starting Context:**
- Just completed an action (created fault, closed WO)
- Types "do that again" or "same thing for bilge pump"

**User Intent:**
Repeat previous action with variation

**Expected System Response:**
1. Previous context available
2. Variation extracted
3. Confirmation before repeat

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | (repeat of last action) | If context clear |
| Available | (similar actions) | If "same thing" is ambiguous |

**Success Criteria:**
- Previous action context retained (session)
- Variation entity resolved
- Confirmation required for mutations

---

### J11: Fault Escalates to Work Order

**Persona**: Engineer, at sea

**Starting Context:**
- Fault card open
- Diagnosis complete
- Repair needed

**User Intent:**
Convert diagnosed fault into scheduled work

**Expected System Response:**
1. create_work_order_from_fault prominent
2. Fault context transfers to WO
3. Fault marked as having WO

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | create_work_order_from_fault | Fault context + no existing WO |
| Secondary | add_to_handover | Escalate visibility |
| Suppressed | close_fault | Work not done yet |
| Available | acknowledge_fault | If not yet acked |

**Success Criteria:**
- create_work_order_from_fault visible ONLY when !fault.has_work_order
- After WO created, action disappears
- Fault-WO link established

---

### J12: Work Order Lifecycle Completion

**Persona**: Engineer, at sea

**Starting Context:**
- Work order in progress
- Task physically complete
- Documentation needed

**User Intent:**
Close out work order with proper documentation

**Expected System Response:**
1. close_work_order prominent
2. Documentation prompts
3. Status update and audit log

**Expected Actions Surfaced:**
| Priority | Action | Reason |
|----------|--------|--------|
| Primary | close_work_order | WO status = in_progress, work done |
| Secondary | add_wo_note | Final documentation |
| Available | add_wo_hours | Time tracking |
| Available | add_fault_photo | Evidence capture |
| Suppressed | start_work_order | Already started |

**Success Criteria:**
- close_work_order only when status allows
- Documentation actions grouped before close
- Audit trail complete

---

## Journey Coverage Matrix

| Journey | Roles | Clusters Touched | Critical Actions |
|---------|-------|------------------|------------------|
| J01 | Engineer | FIX_SOMETHING | report_fault |
| J02 | ETO | FIX_SOMETHING, MANAGE_EQUIPMENT | report_fault |
| J03 | Captain | FIX_SOMETHING | view_fault_detail |
| J04 | Manager | DO_MAINTENANCE | assign_work_order |
| J05 | Engineer | DO_MAINTENANCE, COMMUNICATE_STATUS | add_to_handover |
| J06 | ETO | DO_MAINTENANCE | add_note_to_work_order |
| J07 | Engineer | MANAGE_EQUIPMENT | show_manual_section |
| J08 | Any | (Search) | (disambiguation) |
| J09 | Any | (Clarification) | (none until clear) |
| J10 | Any | (Repeat) | (previous action) |
| J11 | Engineer | FIX_SOMETHING, DO_MAINTENANCE | create_work_order_from_fault |
| J12 | Engineer | DO_MAINTENANCE | close_work_order |

---

## Known Gaps

1. **J03/J04**: Captain and Manager roles need explicit role-based filtering in triggers
2. **J08/J09**: Clarification flow not fully implemented
3. **J10**: Session context for "repeat" not implemented
4. **Photo actions**: Storage integration incomplete (5 SKIPs in Phase 8)

---

**Document:** E012_JOURNEY_SET.md
**Completed:** 2026-01-21
