# CELESTE HOLISTIC SYSTEM VIEW
> Generated: 2026-02-27 | 6 Sub-Agents | Comprehensive Analysis

---

## EXECUTIVE SUMMARY

Celeste is an NLP-first yacht maintenance system with:
- **10 Entity Lenses** (work orders, faults, equipment, inventory, certificates, documents, receiving, shopping list, email, hours of rest)
- **12 Fragmented Routes** (feature-flagged)
- **27 Active Filters** across 8 domains
- **87+ Actions** (62 MUTATE, 16 SIGNED, 15 READ)
- **23,173 lines** of E2E test coverage (built, awaiting deployment)

---

## 1. ENTITY LENSES

| Lens | Status | Table | Actions | Key Fields |
|------|--------|-------|---------|------------|
| **Work Order** | PRODUCTION | `pms_work_orders` | 14 | title, status, priority, equipment_id, assigned_to |
| **Equipment** | PRODUCTION | `pms_equipment` | 16 | name, status, criticality, manufacturer, serial_number |
| **Fault** | PRODUCTION | `pms_faults` | 12 | title, severity, status, equipment_id, reported_by |
| **Certificate** | PRODUCTION | `pms_vessel_certificates`, `pms_crew_certificates` | 6 | certificate_type, expiry_date, issuing_authority |
| **Document** | PRODUCTION | `doc_metadata` | 6 | filename, doc_type, storage_path, tags, equipment_ids |
| **Part/Inventory** | PRODUCTION | `pms_parts`, `pms_inventory_stock` | 10 | name, part_number, quantity_on_hand, minimum_quantity |
| **Shopping List** | PRODUCTION | `pms_shopping_list_items` | 5 | part_name, quantity_requested, status, urgency |
| **Receiving** | PRODUCTION | `pms_receiving_events`, `pms_receiving_line_items` | 10 | receiving_number, quantity_received, disposition |
| **Hours of Rest** | PRODUCTION | `pms_crew_rest_logs` | 5 | crew_id, logged_hours, shift_start, shift_end |
| **Crew** | DEV (Phase 2) | `auth_users_profiles` | TBD | person_name, role, yacht_id, is_active |

### Cross-Lens Relationships

```
Work Order ──► Equipment (equipment_id)
    ├──────► Fault (fault_id)
    ├──────► Crew (assigned_to)
    └──────► Part (pms_work_order_parts)

Equipment ──► Work Orders, Faults, Parts BOM, Documents, Certificates, Notes

Certificate ──► Document (document_id), Crew (person_node_id)

Part ──► Equipment (BOM), Work Order (usage), Shopping List, Receiving

Receiving ──► Part, Shopping List, Equipment (immediate install)
```

---

## 2. FRAGMENTED ROUTES

**Feature Flag:** `NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true`

```
/                           # Single Surface (CelesteOS)
├── /app                    # Legacy fallback
├── /work-orders            # List + Detail overlay
│   └── /work-orders/[id]   # Full-page detail
├── /faults
│   └── /faults/[id]
├── /equipment
│   └── /equipment/[id]
├── /inventory
│   └── /inventory/[id]
├── /email
│   └── /email/[threadId]
├── /shopping-list
│   └── /shopping-list/[id]
├── /receiving
│   └── /receiving/[id]
├── /certificates
│   └── /certificates/[id]
├── /documents
│   └── /documents/[id]
├── /warranties
│   └── /warranties/[id]
├── /hours-of-rest
│   └── /hours-of-rest/[id]
└── /purchasing
    └── /purchasing/[id]
```

### Query Parameters
- `?id=<entityId>` - Select item for overlay/panel
- `?filter=<filterId>` - Apply quick filter
- `?thread=<threadId>` - Email thread selection

---

## 3. FILTER SYSTEM

**Total: 27 Active Filters** | 1 Blocked | 8 Domains

### Work Orders (5 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| wo_overdue | Overdue work orders | due_date < TODAY AND status NOT IN (completed, cancelled) |
| wo_due_7d | Due this week | due_date BETWEEN TODAY AND TODAY+7 |
| wo_open | Open work orders | status IN (planned, in_progress) |
| wo_priority_emergency | Emergency priority | priority = emergency |
| wo_priority_critical | Critical priority | priority = critical |

### Faults (4 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| fault_open | Open faults | status = open |
| fault_unresolved | Unresolved faults | status IN (open, investigating) |
| fault_critical | Critical faults | severity = high |
| fault_investigating | Under investigation | status = investigating |

### Equipment (4 active, 1 blocked)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| eq_attention | Needs attention | attention_flag = true |
| eq_failed | Failed equipment | status = failed |
| eq_maintenance | In maintenance | status = maintenance |
| eq_critical | Critical equipment | criticality = critical |
| ~~eq_due_service_30d~~ | ~~Service due (30d)~~ | **BLOCKED: next_service_date column missing** |

### Inventory (2 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| inv_low_stock | Low stock | quantity_on_hand <= minimum_quantity |
| inv_out_of_stock | Out of stock | quantity_on_hand = 0 |

### Certificates (2 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| cert_expiring_30d | Expiring soon | expiry_date BETWEEN TODAY AND TODAY+30 |
| cert_expired | Expired certificates | expiry_date < TODAY |

### Email (3 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| email_unlinked | Unlinked emails | No active email_links |
| email_linked | Linked emails | Has active email_links |
| email_with_attachments | With attachments | has_attachments = true |

### Shopping List (2 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| shop_pending | Pending approval | status IN (candidate, under_review) |
| shop_urgent | Urgent items | urgency IN (high, critical) |

### Receiving (2 filters)
| Filter ID | Label | Definition |
|-----------|-------|------------|
| recv_pending | Pending receiving | status IN (in_progress, partial) |
| recv_discrepancy | With discrepancies | status = discrepancy |

### NLP Inference Pipeline
1. **Phase 1: Explicit Patterns** (score 0.9-1.0) - 104 regex patterns
2. **Phase 2: Keyword Matching** (score 0.3-0.8) - Substring matching
3. **Phase 3: Domain Suggestions** (score 0.3) - Fallback by domain

---

## 4. DATA SOURCES

### Backend API (FastAPI on Render)

| Endpoint | Method | Data Source | Frontend Consumer |
|----------|--------|-------------|-------------------|
| `/v1/work-orders` | GET | pms_work_orders | fetchWorkOrders() |
| `/v1/faults` | GET/POST | pms_faults | fetchFaults() |
| `/v1/equipment` | GET | pms_equipment | fetchEquipment() |
| `/v1/inventory` | GET | pms_parts | fetchParts() |
| `/v1/certificates` | GET | pms_*_certificates | fetchCertificates() |
| `/v1/documents` | GET/POST | doc_metadata | fetchDocuments() |
| `/v1/receiving` | GET/POST | pms_receiving_* | fetchReceivingItems() |
| `/v1/actions/execute` | POST | Action registry | microactions/executor.ts |
| `/api/search/stream` | SSE | Multi-table | SpotlightSearch |

### Supabase Tables (Tenant DB)
- `pms_work_orders`, `pms_faults`, `pms_equipment`, `pms_parts`
- `pms_inventory_stock`, `pms_inventory_transactions`
- `pms_vessel_certificates`, `pms_crew_certificates`
- `doc_metadata`, `pms_receiving_events`, `pms_receiving_line_items`
- `pms_shopping_list_items`, `pms_crew_rest_logs`
- `ledger_events`, `pms_audit_log`

### Authentication
- **JWT Token**: Supabase Auth (Master DB)
- **Yacht Isolation**: `yacht_id` claim in JWT
- **Role-Based Access**: `role` field in JWT metadata
- **RLS Policies**: `yacht_id = get_user_yacht_id()`

---

## 5. ACTIONS BY DOMAIN

### Action Types
- **READ**: View-only (no DB writes)
- **MUTATE**: Standard mutations (INSERT/UPDATE)
- **SIGNED**: High-risk requiring PIN+TOTP signature

### Work Orders (14 actions)
| Action | Type | Roles |
|--------|------|-------|
| create_work_order_from_fault | SIGNED | chief_engineer, captain, manager |
| close_work_order | MUTATE | chief_engineer, chief_officer, captain |
| assign_work_order | MUTATE | chief_engineer, chief_officer, captain |
| add_wo_note | MUTATE | chief_engineer, chief_officer, captain |
| add_wo_part | MUTATE | chief_engineer, chief_officer, captain |
| start_work_order | MUTATE | chief_engineer, chief_officer, captain |
| cancel_work_order | MUTATE | chief_engineer, chief_officer, captain |
| view_work_order_detail | READ | all crew |

### Equipment (16 actions)
| Action | Type | Roles |
|--------|------|-------|
| update_equipment_status | MUTATE | engineer+ |
| add_equipment_note | MUTATE | all crew |
| attach_file_to_equipment | MUTATE | all crew |
| create_work_order_for_equipment | MUTATE | engineer+ |
| flag_equipment_attention | MUTATE | engineer+ |
| decommission_equipment | SIGNED | captain, manager |

### Faults (12 actions)
| Action | Type | Roles |
|--------|------|-------|
| report_fault | MUTATE | all crew |
| acknowledge_fault | MUTATE | chief_engineer+ |
| close_fault | MUTATE | chief_engineer+ |
| update_fault | MUTATE | chief_engineer+ |
| mark_fault_false_alarm | MUTATE | chief_engineer+ |
| add_fault_note | MUTATE | all crew |

### Receiving (10 actions)
| Action | Type | Roles |
|--------|------|-------|
| create_receiving | MUTATE | all crew |
| add_receiving_item | MUTATE | HOD+ |
| adjust_receiving_item | MUTATE | HOD+ |
| accept_receiving | SIGNED | HOD+ |
| reject_receiving | MUTATE | all crew |

### Inventory (10 actions)
| Action | Type | Roles |
|--------|------|-------|
| consume_part | MUTATE | all crew |
| adjust_stock_quantity | SIGNED | captain, manager |
| transfer_part | MUTATE | HOD+ |
| receive_part | MUTATE | HOD+ |
| write_off_part | SIGNED | captain, manager |
| add_to_shopping_list | MUTATE | all crew |

---

## 6. LIMITATIONS & GAPS

### CRITICAL (P0)
| Issue | Impact | Status |
|-------|--------|--------|
| RLS Policy Gaps | Cross-yacht data leakage | BLOCKED - needs migrations |
| Faults Lens | 2/10 actions implemented | INCOMPLETE |
| Equipment Lens | 0/7 spec actions | INCOMPLETE |
| Signature Capture | SIGNED actions use empty `{}` | NOT IMPLEMENTED |
| Action Name Mismatches | Backend rejects actions | WRONG NAMES |

### HIGH (P1)
| Issue | Impact | Status |
|-------|--------|--------|
| Role Visibility | Buttons shown regardless of role | UI ONLY |
| Handover Drafts | Edits lost on session interrupt | NOT IMPLEMENTED |
| OCR Integration | Receiving upload non-functional | MOCK ONLY |
| Agent Token | Agent auth will fail | NOT CONFIGURED |

### MEDIUM (P2)
| Issue | Impact | Status |
|-------|--------|--------|
| Email Features | May be disabled | CONFIG-DEPENDENT |
| Action Logging | No audit trail | TABLE MISSING |
| AI Features | Disabled without OpenAI key | CONFIG-DEPENDENT |

### BLOCKED FILTERS
| Filter | Reason |
|--------|--------|
| eq_due_service_30d | `next_service_date` column missing |

---

## 7. TEST COVERAGE

### Spotlight E2E Tests (Created)
| Category | Files | Lines |
|----------|-------|-------|
| SHOW Tests | 10 | ~10,100 |
| ACTION Tests | 9 | ~13,100 |
| **TOTAL** | **19** | **23,173** |

### Test Status
- **Created**: All 19 files
- **Blocked**: Backend routes not deployed to production
- **Routes Missing**: `/v1/work-orders`, `/v1/equipment`, `/v1/inventory`

---

## 8. ARCHITECTURE PATTERNS

### Single Surface Philosophy
- One URL: `app.celeste7.ai`
- Query → Focus → Act
- Full-screen lenses (no cards/sidebars)
- Backend authority (frontend renders what backend returns)

### RLS Pattern
```sql
yacht_id = public.get_user_yacht_id()
```

### Soft Delete
```sql
deleted_at, deleted_by, deletion_reason (NEVER hard DELETE)
```

### Append-Only Ledgers
- `pms_inventory_transactions`
- `pms_part_usage`
- `pms_shopping_list_state_history`

### Action Activation
- Actions appear only after entity is FOCUSED
- No ambient dashboards

---

## 9. DEPLOYMENT STATUS

| Component | Location | Status |
|-----------|----------|--------|
| Frontend | Vercel | ✅ DEPLOYED |
| API | Render | ⚠️ MISSING ROUTES |
| Database | Supabase | ✅ DEPLOYED |
| Storage | Supabase | ✅ DEPLOYED |
| E2E Tests | Local | ✅ CREATED |

### Routes Needing Deployment
```python
# apps/api/routes/
work_order_routes.py   # GET /v1/work-orders
equipment_routes.py    # GET /v1/equipment
inventory_routes.py    # GET /v1/inventory
```

---

## 10. NEXT STEPS

### P0 - Immediate
1. Deploy backend routes to Render
2. Fix RLS policies (migrations)
3. Complete Faults Lens actions
4. Complete Equipment Lens actions
5. Implement signature capture

### P1 - Short-term
1. Run E2E test suite twice consecutively
2. Configure agent token auth
3. Implement OCR integration
4. Add action execution logging

### P2 - Medium-term
1. Complete email integration
2. Implement crew lens (Phase 2)
3. Add AI-powered features

---

*Report compiled from 6 parallel sub-agents analyzing 100+ source files*
