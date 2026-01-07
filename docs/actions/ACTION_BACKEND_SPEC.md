# Complete Backend Specification: All 67 Micro-Actions

**Version:** 1.0
**Date:** 2025-11-21
**Purpose:** Definitive backend implementation guide for each micro-action

---

## Document Structure

Each action specification includes:
- **Purpose:** What the action does
- **Operation Type:** VIEW | CREATE | UPDATE | LINKING | EXPORT | RAG
- **Tables:** Primary and secondary tables involved
- **Required Input:** Expected context and parameters
- **n8n Steps:** Pseudo-code workflow
- **Audit:** Logging requirements
- **Permissions:** Role-based access rules
- **Test Cases:** Success and failure scenarios

---

# Cluster 1: FIX_SOMETHING (8 Actions)

---

## Action 1: diagnose_fault

**Cluster:** fix_something
**Workflow archetype:** RAG
**Card type:** fault
**Frontend Status:** ✅ DiagnoseFaultModal implemented

**Purpose:** Use AI/RAG to analyze fault, find similar past faults, suggest solutions and parts.

**Operation Type:** RAG (Vector search + AI streaming)

**Tables:**
- `faults` (read)
- `fault_embeddings` (vector search)
- `equipment` (read)
- `documents` (read)
- `parts` (read for suggestions)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (required)",
    "additional_context": "string (optional) - extra user input"
  },
  "session": {
    "yacht_id": "uuid",
    "user_id": "uuid"
  }
}
```

**n8n Steps (pseudo):**
1. Validate `fault_id` exists and belongs to `session.yacht_id`.
2. Fetch fault details: title, description, severity, equipment_id.
3. If equipment_id exists, fetch equipment details (name, model, serial_number).
4. Generate embedding for fault description + additional_context.
5. Vector search `fault_embeddings` for top 5 similar resolved faults.
6. Retrieve relevant document sections from `documents` based on equipment_id.
7. Build prompt with fault context + similar faults + document excerpts.
8. Stream response from AI model (OpenAI/Claude).
9. Parse AI response for suggested parts, extract part_numbers.
10. Return streamed diagnosis + similar_faults array + suggested_parts array + manual_references.

**Response Shape:**
```json
{
  "success": true,
  "card_type": "diagnosis",
  "streaming": true,
  "card": {
    "fault_id": "uuid",
    "diagnosis_text": "Streamed AI response...",
    "similar_faults": [
      {"id": "uuid", "title": "...", "resolution": "...", "similarity_score": 0.94}
    ],
    "suggested_parts": [
      {"part_name": "...", "part_number": "...", "confidence": 0.89}
    ],
    "manual_references": ["Section 4.2: Cooling System"]
  }
}
```

**Audit:**
- Required: No (read-only, AI generation)
- Severity: N/A
- Optional: Log diagnosis requests for analytics

**Permissions:**
- Allowed: All authenticated users
- No restrictions

**Test Cases:**
- ✅ Valid fault_id with equipment → returns diagnosis with similar faults
- ✅ Fault with no similar history → returns diagnosis, empty similar_faults
- ✅ Additional_context provided → enhances diagnosis quality
- ❌ Invalid fault_id → error "Fault not found"
- ❌ Fault from different yacht → error "Forbidden"
- ❌ AI service unavailable → error "Diagnosis service temporarily unavailable"

---

## Action 2: show_manual_section

**Cluster:** fix_something
**Workflow archetype:** VIEW
**Card type:** document

**Purpose:** Retrieve and display a specific section from equipment manual or document.

**Operation Type:** VIEW

**Tables:**
- `documents` (read)
- `document_sections` (read)

**Required Input:**
```json
{
  "context": {
    "document_id": "uuid (required)",
    "section_id": "string (optional) - specific section",
    "equipment_id": "uuid (optional) - for context"
  }
}
```

**n8n Steps (pseudo):**
1. Validate document_id exists and yacht_id matches.
2. If section_id provided, fetch specific section from `document_sections`.
3. If no section_id, fetch document metadata and first section.
4. Return document content with navigation info.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid document_id → returns document content
- ✅ With section_id → jumps to specific section
- ❌ Invalid document_id → error "Document not found"

---

## Action 3: view_fault_history

**Cluster:** fix_something
**Workflow archetype:** VIEW
**Card type:** fault

**Purpose:** Display historical occurrences of similar faults for equipment or fault code.

**Operation Type:** VIEW

**Tables:**
- `faults` (read)
- `equipment` (join)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (optional) - view similar to this fault",
    "equipment_id": "uuid (optional) - view all faults for equipment",
    "fault_code": "string (optional) - view by fault code"
  },
  "parameters": {
    "limit": "number (default: 50)",
    "offset": "number (default: 0)"
  }
}
```

**n8n Steps (pseudo):**
1. Build filter based on provided context (fault_id, equipment_id, or fault_code).
2. Query faults table with filters, ORDER BY created_at DESC.
3. Include pagination metadata.
4. Return array of fault summary cards.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ By equipment_id → returns fault history for that equipment
- ✅ By fault_code → returns all faults with same code
- ✅ Empty history → returns empty array
- ❌ Invalid equipment_id → error "Equipment not found"

---

## Action 4: suggest_parts

**Cluster:** fix_something
**Workflow archetype:** VIEW
**Card type:** part_suggestion

**Purpose:** Recommend parts likely needed to resolve a fault based on fault type and history.

**Operation Type:** VIEW

**Tables:**
- `faults` (read)
- `fault_parts_suggestions` (read)
- `parts` (read)
- `equipment_parts` (read)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate fault_id exists.
2. Get fault details including equipment_id.
3. Query `fault_parts_suggestions` for this fault_id (if AI already generated).
4. If no suggestions, query `equipment_parts` for compatible parts.
5. Add stock availability from `parts` table.
6. Return ordered list by relevance/confidence.

**Response Shape:**
```json
{
  "success": true,
  "card_type": "part_suggestions",
  "cards": [
    {
      "part_id": "uuid",
      "part_name": "Oil Filter",
      "part_number": "OF-123",
      "confidence": 0.92,
      "reason": "Most common fix for this fault type",
      "stock_available": 12,
      "location": "Engine Room - Storage A"
    }
  ]
}
```

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Fault with suggestions → returns ranked parts list
- ✅ No suggestions → returns compatible parts from equipment
- ❌ Invalid fault_id → error "Fault not found"

---

## Action 5: create_work_order_from_fault

**Cluster:** fix_something
**Workflow archetype:** CREATE
**Card type:** work_order

**Purpose:** Generate a work order pre-filled with fault context (equipment, description, priority).

**Operation Type:** CREATE

**Tables:**
- `faults` (read)
- `work_orders` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (required)"
  },
  "parameters": {
    "title": "string (optional - defaults to fault title)",
    "priority": "string (optional - defaults to fault severity mapping)",
    "assigned_to": "uuid (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate fault_id exists and belongs to yacht.
2. Fetch fault details: title, description, equipment_id, severity.
3. Map severity to priority: critical → urgent, high → high, medium → medium, low → low.
4. INSERT into work_orders with pre-filled data.
5. UPDATE faults SET status = 'in_progress', linked_work_order_id = new_wo_id.
6. INSERT audit_log entry.
7. Return new work_order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: user_id, fault_id, work_order_id, timestamp

**Permissions:**
- Allowed: All engineering roles
- Denied: DECKHAND, STEWARDESS (unless cross-trained)

**Test Cases:**
- ✅ Valid fault → creates WO with pre-filled data
- ✅ With custom title/priority → overrides defaults
- ❌ Invalid fault_id → error "Fault not found"
- ❌ Fault already has linked WO → warning but allow (can have multiple WOs)

---

## Action 6: add_fault_note

**Cluster:** fix_something
**Workflow archetype:** CREATE
**Card type:** note

**Purpose:** Attach an observation or comment to a fault record.

**Operation Type:** CREATE

**Tables:**
- `faults` (validate)
- `fault_notes` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (required)"
  },
  "parameters": {
    "note_text": "string (required, min 1 char)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate fault_id exists and belongs to yacht.
2. Validate note_text is not empty.
3. INSERT into fault_notes (fault_id, text, created_by, created_at).
4. INSERT audit_log with LOW severity.
5. Return note card with id.

**Audit:**
- Required: Yes
- Severity: LOW
- Fields: user_id, fault_id, note_id

**Permissions:**
- Allowed: All authenticated users
- Own yacht only

**Test Cases:**
- ✅ Valid fault + note → creates note, returns note card
- ❌ Empty note_text → error "Note text required"
- ❌ Invalid fault_id → error "Fault not found"

---

## Action 7: add_fault_photo

**Cluster:** fix_something
**Workflow archetype:** CREATE
**Card type:** attachment

**Purpose:** Upload photo evidence of fault condition.

**Operation Type:** CREATE

**Tables:**
- `faults` (validate)
- `fault_attachments` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (required)"
  },
  "parameters": {
    "file_data": "base64 string or upload URL (required)",
    "filename": "string (required)",
    "caption": "string (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate fault_id exists.
2. Validate file_data is valid image (JPEG, PNG, max 10MB).
3. Upload to storage (Supabase Storage or S3).
4. INSERT into fault_attachments (fault_id, url, filename, caption, created_by).
5. INSERT audit_log.
6. Return attachment card with URL.

**Audit:**
- Required: Yes
- Severity: LOW

**Permissions:**
- Allowed: All authenticated users

**Test Cases:**
- ✅ Valid image upload → stores and returns URL
- ❌ File too large → error "File exceeds 10MB limit"
- ❌ Invalid file type → error "Only JPEG and PNG allowed"

---

## Action 8: edit_fault_details

**Cluster:** fix_something
**Workflow archetype:** UPDATE
**Card type:** fault
**Frontend Status:** ✅ EditFaultDetailsModal implemented

**Purpose:** Update fault description, severity, or status with audit logging.

**Operation Type:** UPDATE

**Tables:**
- `faults` (update)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "fault_id": "uuid (required)"
  },
  "parameters": {
    "title": "string (optional)",
    "description": "string (optional)",
    "severity": "enum: low|medium|high|critical (optional)",
    "status": "enum: open|in_progress|resolved|closed (optional)",
    "reopening_reason": "string (required if reopening closed fault)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate fault_id exists and belongs to yacht.
2. Fetch current fault state (for diff).
3. If current status = 'closed' AND new status != 'closed':
   - Require `reopening_reason` (min 15 chars).
   - Set audit severity to HIGH.
4. Build UPDATE with only provided fields.
5. Execute UPDATE in transaction.
6. INSERT audit_log with before/after state.
7. If reopening: send notification to HOD.
8. Return updated fault card.

**Audit:**
- Required: Yes
- Severity: MEDIUM (HIGH if reopening closed fault)
- Fields: before_state, after_state, reopening_reason (if applicable)

**Permissions:**
- Allowed: All engineering roles
- Reopening closed fault: HOD+ only

**Test Cases:**
- ✅ Edit title/description → updates, logs diff
- ✅ Change severity (low → high) → updates, warns in response
- ✅ Reopen with reason → updates, creates HIGH audit log
- ❌ Reopen without reason → error "Reason required to reopen closed fault"
- ❌ Invalid status transition → error "Invalid status change"

---

# Cluster 2: DO_MAINTENANCE (10 Actions)

---

## Action 9: create_work_order

**Cluster:** do_maintenance
**Workflow archetype:** CREATE
**Card type:** work_order
**Frontend Status:** ✅ CreateWorkOrderModal exists (Phase 1)

**Purpose:** Create a new work order with equipment selection.

**Operation Type:** CREATE

**Tables:**
- `work_orders` (insert)
- `equipment` (validate)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "parameters": {
    "title": "string (required, min 5 chars)",
    "description": "string (optional)",
    "equipment_id": "uuid (optional)",
    "priority": "enum: low|medium|high|urgent (default: medium)",
    "due_date": "date (optional)",
    "assigned_to": "uuid (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate title length.
2. If equipment_id provided, validate it exists and belongs to yacht.
3. If assigned_to provided, validate user exists and is on yacht.
4. INSERT into work_orders with status = 'draft'.
5. INSERT audit_log.
6. Return new work_order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM

**Permissions:**
- Allowed: All authenticated users (create own)
- Draft status by default

**Test Cases:**
- ✅ Valid input → creates WO in draft status
- ✅ With equipment_id → links to equipment
- ❌ Title too short → error "Title must be at least 5 characters"
- ❌ Invalid equipment_id → error "Equipment not found"

---

## Action 10: view_work_order_history

**Cluster:** do_maintenance
**Workflow archetype:** VIEW
**Card type:** work_order

**Purpose:** Show completion history for work orders (by equipment or type).

**Operation Type:** VIEW

**Tables:**
- `work_orders` (read)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (optional)",
    "work_order_type": "string (optional)"
  },
  "parameters": {
    "status_filter": "array of statuses (optional)",
    "limit": "number (default: 50)",
    "offset": "number (default: 0)"
  }
}
```

**n8n Steps (pseudo):**
1. Build query with filters.
2. Execute SELECT with pagination.
3. Return array of work_order summary cards.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ By equipment_id → returns WO history for equipment
- ✅ With status_filter → filters by status
- ✅ Empty history → returns empty array

---

## Action 11: mark_work_order_complete

**Cluster:** do_maintenance
**Workflow archetype:** UPDATE
**Card type:** work_order
**Frontend Status:** ✅ CompleteWorkOrderModal implemented

**Purpose:** Close work order with completion data, quality checks, and time tracking.

**Operation Type:** UPDATE

**Tables:**
- `work_orders` (update)
- `parts` (update stock if parts logged)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "completion_notes": "string (required, min 20 chars)",
    "actual_hours": "number (required, >= 0)",
    "outcome": "enum: completed|partially_completed|deferred (required)",
    "quality_check_passed": "boolean (required if outcome=completed)",
    "parts_used_documented": "boolean (required if outcome=completed)",
    "follow_up_required": "boolean (optional)",
    "follow_up_notes": "string (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists and belongs to yacht.
2. Validate current status allows completion (in_progress or approved).
3. If outcome = 'completed':
   - Require quality_check_passed = true.
   - Require parts_used_documented = true.
4. Calculate hours variance vs estimated.
5. UPDATE work_orders SET status, completion_notes, actual_hours, completed_at, completed_by.
6. If follow_up_required, create new draft work order.
7. If outcome = 'partially_completed', create follow-up WO for remaining work.
8. INSERT audit_log.
9. Return updated work_order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: before_state, after_state, hours_variance

**Permissions:**
- Allowed: Assigned user, HOD+, or creator
- Cannot complete if not in valid state

**Test Cases:**
- ✅ Complete with all checks passed → closes WO
- ✅ Partially complete → closes WO, creates follow-up
- ✅ Deferred → closes WO with deferral status
- ❌ Complete without quality check → error "Quality check required"
- ❌ WO already completed → error "Work order already closed"
- ❌ Completion notes too short → error "Notes must be at least 20 characters"

---

## Action 12: add_work_order_note

**Cluster:** do_maintenance
**Workflow archetype:** CREATE
**Card type:** note

**Purpose:** Add progress note to work order.

**Operation Type:** CREATE

**Tables:**
- `work_orders` (validate)
- `work_order_notes` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "note_text": "string (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists.
2. INSERT into work_order_notes.
3. INSERT audit_log (LOW severity).
4. Return note card.

**Audit:**
- Required: Yes
- Severity: LOW

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid note → creates and returns note
- ❌ Empty text → error "Note text required"

---

## Action 13: add_work_order_photo

**Cluster:** do_maintenance
**Workflow archetype:** CREATE
**Card type:** attachment

**Purpose:** Attach photo to work order (before/after, evidence).

**Operation Type:** CREATE

**Tables:**
- `work_orders` (validate)
- `work_order_attachments` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "file_data": "base64 or URL (required)",
    "filename": "string (required)",
    "photo_type": "enum: before|after|evidence|other (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists.
2. Validate and upload file.
3. INSERT into work_order_attachments.
4. INSERT audit_log.
5. Return attachment card.

**Audit:**
- Required: Yes
- Severity: LOW

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid image → uploads and links to WO
- ❌ Invalid file type → error
- ❌ File too large → error

---

## Action 14: add_parts_to_work_order

**Cluster:** do_maintenance
**Workflow archetype:** LINKING
**Card type:** work_order_parts
**Frontend Status:** ✅ LinkPartsToWorkOrderModal implemented

**Purpose:** Link parts to work order with quantities and optional reservation.

**Operation Type:** LINKING

**Tables:**
- `work_orders` (validate)
- `parts` (read/update if reserving)
- `work_order_parts` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "parts": [
      {
        "part_id": "uuid (required)",
        "quantity_required": "number (required, >= 1)",
        "notes": "string (optional)"
      }
    ],
    "reserve_parts": "boolean (optional, default: false)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists.
2. For each part in parts array:
   a. Validate part_id exists.
   b. Check stock >= quantity_required.
   c. If reserve_parts = true, reduce available stock.
3. INSERT into work_order_parts (batch).
4. If reserve_parts, UPDATE parts SET reserved_quantity += quantity.
5. INSERT audit_log.
6. Return updated work_order card with parts.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: parts_linked, quantities, reserved

**Permissions:**
- Allowed: Assigned user, engineering roles

**Test Cases:**
- ✅ Link parts with sufficient stock → success
- ✅ Reserve parts → reduces available quantity
- ❌ Quantity exceeds stock → error "Insufficient stock for part X"
- ❌ Invalid part_id → error "Part not found"

---

## Action 15: view_work_order_checklist

**Cluster:** do_maintenance
**Workflow archetype:** VIEW
**Card type:** checklist

**Purpose:** Display procedural checklist for work order task.

**Operation Type:** VIEW

**Tables:**
- `work_orders` (read)
- `work_order_checklists` (read)
- `checklist_items` (read)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists.
2. Fetch linked checklist from work_order_checklists.
3. Fetch checklist_items ordered by position.
4. Return checklist card with items.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ WO with checklist → returns items
- ✅ WO without checklist → returns empty checklist
- ❌ Invalid work_order_id → error

---

## Action 16: assign_work_order

**Cluster:** do_maintenance
**Workflow archetype:** UPDATE
**Card type:** work_order

**Purpose:** Assign work order to crew member.

**Operation Type:** UPDATE

**Tables:**
- `work_orders` (update)
- `users` (validate)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "assigned_to": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists.
2. Validate assigned_to user exists and is on same yacht.
3. UPDATE work_orders SET assigned_to.
4. INSERT audit_log.
5. Optionally send notification to assignee.
6. Return updated work_order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM

**Permissions:**
- Allowed: HOD+, or current assignee can reassign

**Test Cases:**
- ✅ Valid assignment → updates assigned_to
- ❌ User not on yacht → error "User not found"
- ❌ Self-assign by crew → depends on permissions

---

## Action 17: edit_work_order_details

**Cluster:** do_maintenance
**Workflow archetype:** UPDATE
**Card type:** work_order
**Frontend Status:** ✅ EditWorkOrderDetailsModal implemented

**Purpose:** Modify work order title, description, priority, due date, assignee.

**Operation Type:** UPDATE

**Tables:**
- `work_orders` (update)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "title": "string (optional)",
    "description": "string (optional)",
    "priority": "enum: low|medium|high|urgent (optional)",
    "due_date": "date (optional)",
    "assigned_to": "uuid (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists and belongs to yacht.
2. Fetch current work_order state.
3. If status IN ('completed', 'cancelled'):
   - Return error "Cannot edit closed work order".
4. Build UPDATE with only provided fields.
5. Execute UPDATE.
6. INSERT audit_log with before/after diff.
7. Return updated work_order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: before_state, after_state

**Permissions:**
- Allowed: CHIEF_ENGINEER, ETO, ENGINEER
- Crew can edit own WOs only

**Test Cases:**
- ✅ Edit title and priority on open WO → succeeds
- ✅ Edit description only → succeeds, minimal diff
- ❌ Edit completed WO → error "Cannot edit closed work order"
- ❌ Invalid work_order_id → error "Work order not found"
- ❌ Edit unauthorized field → ignore field silently

---

## Action 18: approve_work_order

**Cluster:** do_maintenance
**Workflow archetype:** UPDATE
**Card type:** work_order

**Purpose:** HOD approval before work order execution.

**Operation Type:** UPDATE

**Tables:**
- `work_orders` (update)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "approved": "boolean (required)",
    "approver_notes": "string (optional)",
    "rejection_reason": "string (required if approved=false)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate work_order_id exists.
2. Validate current status = 'pending_approval'.
3. Validate session.role is HOD+.
4. If approved = true:
   - UPDATE status = 'approved', approved_by, approved_at.
5. If approved = false:
   - UPDATE status = 'draft'.
   - Record rejection_reason.
6. INSERT audit_log.
7. Send notification to creator.
8. Return updated work_order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: approved, approver_notes, rejection_reason

**Permissions:**
- Allowed: HOD, CHIEF_ENGINEER, CAPTAIN, OWNER
- Cannot approve own WO

**Test Cases:**
- ✅ Approve pending WO → status becomes 'approved'
- ✅ Reject with reason → status becomes 'draft'
- ❌ Approve own WO → error "Cannot approve own work order"
- ❌ Approve non-pending WO → error "Work order not pending approval"
- ❌ Insufficient role → error "Insufficient permissions"

---

# Cluster 3: MANAGE_EQUIPMENT (8 Actions)

---

## Action 19: view_equipment_details

**Cluster:** manage_equipment
**Workflow archetype:** VIEW
**Card type:** equipment

**Purpose:** Display full equipment profile.

**Operation Type:** VIEW

**Tables:**
- `equipment` (read)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists and belongs to yacht.
2. Fetch equipment record.
3. Return equipment card.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid equipment_id → returns equipment card
- ❌ Invalid equipment_id → error "Equipment not found"

---

## Action 20: view_equipment_history

**Cluster:** manage_equipment
**Workflow archetype:** VIEW
**Card type:** equipment_history

**Purpose:** Show maintenance timeline for equipment.

**Operation Type:** VIEW

**Tables:**
- `equipment` (validate)
- `equipment_history` (read)
- `work_orders` (join)
- `faults` (join)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  },
  "parameters": {
    "limit": "number (default: 50)",
    "offset": "number (default: 0)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists.
2. Query equipment_history + related WOs + faults.
3. Order by date DESC.
4. Return timeline array.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Equipment with history → returns timeline
- ✅ No history → returns empty array

---

## Action 21: view_equipment_parts

**Cluster:** manage_equipment
**Workflow archetype:** VIEW
**Card type:** parts_list

**Purpose:** List compatible parts for equipment.

**Operation Type:** VIEW

**Tables:**
- `equipment` (validate)
- `equipment_parts` (read)
- `parts` (join)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists.
2. Query equipment_parts JOIN parts.
3. Include stock levels.
4. Return parts list.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Equipment with parts → returns list with stock
- ✅ No parts → returns empty array

---

## Action 22: view_linked_faults

**Cluster:** manage_equipment
**Workflow archetype:** VIEW
**Card type:** fault_list

**Purpose:** Show fault history for equipment.

**Operation Type:** VIEW

**Tables:**
- `equipment` (validate)
- `faults` (read)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  },
  "parameters": {
    "status_filter": "array (optional)",
    "limit": "number (default: 50)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists.
2. Query faults WHERE equipment_id = X.
3. Apply status filter if provided.
4. Return fault list.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Equipment with faults → returns fault list
- ✅ Filter by status → returns filtered list

---

## Action 23: view_equipment_manual

**Cluster:** manage_equipment
**Workflow archetype:** VIEW
**Card type:** document

**Purpose:** Access equipment-specific manual.

**Operation Type:** VIEW

**Tables:**
- `equipment` (validate)
- `documents` (read)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists.
2. Query documents WHERE linked_equipment_id = X.
3. Return document card or list.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Equipment with manual → returns document
- ✅ No manual → returns null or empty

---

## Action 24: add_equipment_note

**Cluster:** manage_equipment
**Workflow archetype:** CREATE
**Card type:** note

**Purpose:** Add observation about equipment condition.

**Operation Type:** CREATE

**Tables:**
- `equipment` (validate)
- `equipment_notes` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  },
  "parameters": {
    "note_text": "string (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists.
2. INSERT into equipment_notes.
3. INSERT audit_log (LOW severity).
4. Return note card.

**Audit:**
- Required: Yes
- Severity: LOW

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid note → creates and returns
- ❌ Empty text → error

---

## Action 25: edit_equipment_details

**Cluster:** manage_equipment
**Workflow archetype:** UPDATE
**Card type:** equipment
**Frontend Status:** ✅ EditEquipmentDetailsModal implemented

**Purpose:** Update equipment info with critical field tracking.

**Operation Type:** UPDATE

**Tables:**
- `equipment` (update)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "equipment_id": "uuid (required)"
  },
  "parameters": {
    "name": "string (optional)",
    "model": "string (optional)",
    "serial_number": "string (optional) - CRITICAL FIELD",
    "location": "string (optional)",
    "manufacturer": "string (optional)",
    "install_date": "date (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate equipment_id exists and belongs to yacht.
2. Fetch current equipment state.
3. Determine if serial_number is being changed → HIGH severity.
4. Build UPDATE with provided fields.
5. Execute UPDATE.
6. INSERT audit_log (MEDIUM or HIGH based on fields).
7. If serial_number changed → send notification to management.
8. Return updated equipment card.

**Audit:**
- Required: Yes
- Severity: MEDIUM (HIGH if serial_number changed)
- Fields: before_state, after_state, critical_field_changed

**Permissions:**
- Allowed: HOD+, CHIEF_ENGINEER
- Serial number changes: Management notification required

**Test Cases:**
- ✅ Edit location → updates, MEDIUM audit
- ✅ Edit serial_number → updates, HIGH audit, notification sent
- ❌ Invalid equipment_id → error
- ❌ Insufficient permissions → error

---

## Action 26: scan_equipment_barcode

**Cluster:** manage_equipment
**Workflow archetype:** VIEW
**Card type:** equipment

**Purpose:** Lookup equipment via QR/barcode scan.

**Operation Type:** VIEW

**Tables:**
- `equipment` (read)

**Required Input:**
```json
{
  "context": {
    "barcode_value": "string (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Query equipment WHERE barcode = X OR qr_code = X.
2. Filter by yacht_id.
3. If found, return equipment card.
4. If not found, return error.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid barcode → returns equipment
- ❌ Unknown barcode → error "Equipment not found"

---

# Cluster 4: CONTROL_INVENTORY (8 Actions)

---

## Action 27: view_part_stock

**Cluster:** control_inventory
**Workflow archetype:** VIEW
**Card type:** part
**Frontend Status:** ✅ Phase 3 list view implemented

**Purpose:** Display current stock level and location.

**Operation Type:** VIEW

**Tables:**
- `parts` (read)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (optional - single part)",
    "search_query": "string (optional - search)"
  },
  "parameters": {
    "limit": "number (default: 50)",
    "offset": "number (default: 0)",
    "filters": {
      "location": "object (optional)",
      "status": "array (optional)",
      "low_stock_only": "boolean (optional)"
    }
  }
}
```

**n8n Steps (pseudo):**
1. Build query based on filters.
2. If low_stock_only = true, add WHERE stock_quantity < min_stock_level.
3. Execute SELECT with pagination.
4. Return parts list with stock info.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ No filters → returns all parts
- ✅ Low stock filter → returns only low stock parts
- ✅ Single part_id → returns that part

---

## Action 28: order_part

**Cluster:** control_inventory
**Workflow archetype:** CREATE
**Card type:** part_order
**Frontend Status:** ✅ OrderPartModal implemented

**Purpose:** Create purchase request for part.

**Operation Type:** CREATE

**Tables:**
- `parts` (validate)
- `part_orders` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (required)"
  },
  "parameters": {
    "quantity": "number (required, >= 1)",
    "supplier": "string (optional)",
    "urgency": "enum: normal|urgent|critical (default: normal)",
    "expected_delivery": "date (optional)",
    "notes": "string (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate part_id exists.
2. Fetch part details for supplier default.
3. INSERT into part_orders.
4. INSERT audit_log (MEDIUM severity).
5. Return order card.

**Audit:**
- Required: Yes
- Severity: MEDIUM

**Permissions:** All authenticated users (creates request, needs approval)

**Test Cases:**
- ✅ Valid order → creates part_order
- ✅ With supplier override → uses provided supplier
- ❌ Invalid part_id → error
- ❌ Quantity <= 0 → error

---

## Action 29: view_part_location

**Cluster:** control_inventory
**Workflow archetype:** VIEW
**Card type:** part

**Purpose:** Show physical storage location.

**Operation Type:** VIEW

**Tables:**
- `parts` (read)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate part_id exists.
2. Return part with location fields (deck, room, storage, bin).

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid part → returns location details
- ❌ Invalid part_id → error

---

## Action 30: view_part_usage

**Cluster:** control_inventory
**Workflow archetype:** VIEW
**Card type:** usage_history

**Purpose:** Show when/where part was consumed.

**Operation Type:** VIEW

**Tables:**
- `parts` (validate)
- `part_usage_log` (read)
- `work_orders` (join)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (required)"
  },
  "parameters": {
    "limit": "number (default: 50)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate part_id exists.
2. Query part_usage_log JOIN work_orders.
3. Order by date DESC.
4. Return usage history array.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Part with usage → returns history
- ✅ No usage → returns empty array

---

## Action 31: log_part_usage

**Cluster:** control_inventory
**Workflow archetype:** UPDATE
**Card type:** part
**Frontend Status:** ✅ LogPartUsageModal implemented

**Purpose:** Record part consumption against work order.

**Operation Type:** UPDATE

**Tables:**
- `parts` (update stock)
- `work_orders` (validate)
- `part_usage_log` (insert)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (required)",
    "work_order_id": "uuid (required)"
  },
  "parameters": {
    "quantity_used": "number (required, >= 1)",
    "usage_notes": "string (optional)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate part_id exists.
2. Validate work_order_id exists.
3. Check stock_quantity >= quantity_used.
4. BEGIN TRANSACTION:
   a. UPDATE parts SET stock_quantity = stock_quantity - quantity_used.
   b. INSERT into part_usage_log.
   c. INSERT audit_log.
5. COMMIT.
6. If new stock < min_stock_level → add low_stock_warning to response.
7. Return updated part card with warning.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: part_id, quantity_used, remaining_stock

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid usage → reduces stock, creates log
- ✅ Stock goes low → returns with warning
- ❌ Exceeds stock → error "Insufficient stock"
- ❌ Invalid part_id → error

---

## Action 32: scan_part_barcode

**Cluster:** control_inventory
**Workflow archetype:** VIEW
**Card type:** part

**Purpose:** Identify part via barcode scan.

**Operation Type:** VIEW

**Tables:**
- `parts` (read)

**Required Input:**
```json
{
  "context": {
    "barcode_value": "string (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Query parts WHERE barcode = X OR part_number = X.
2. Filter by yacht_id.
3. Return part card if found.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Valid barcode → returns part
- ❌ Unknown → error "Part not found"

---

## Action 33: view_linked_equipment

**Cluster:** control_inventory
**Workflow archetype:** VIEW
**Card type:** equipment_list

**Purpose:** Show which equipment uses this part.

**Operation Type:** VIEW

**Tables:**
- `parts` (validate)
- `equipment_parts` (read)
- `equipment` (join)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (required)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate part_id exists.
2. Query equipment_parts JOIN equipment.
3. Return equipment list.

**Audit:** None (read-only)

**Permissions:** All authenticated users

**Test Cases:**
- ✅ Part with equipment → returns list
- ✅ No equipment → returns empty array

---

## Action 34: edit_part_quantity

**Cluster:** control_inventory
**Workflow archetype:** UPDATE
**Card type:** part
**Frontend Status:** ✅ EditPartQuantityModal implemented

**Purpose:** Adjust stock quantity with reason tracking.

**Operation Type:** UPDATE

**Tables:**
- `parts` (update)
- `audit_logs` (insert)

**Required Input:**
```json
{
  "context": {
    "part_id": "uuid (required)"
  },
  "parameters": {
    "new_quantity": "number (required, >= 0)",
    "adjustment_type": "enum: addition|correction|write_off|return (required)",
    "reason": "string (required, min 10 chars)"
  }
}
```

**n8n Steps (pseudo):**
1. Validate part_id exists.
2. Fetch current quantity for diff.
3. Validate reason length.
4. UPDATE parts SET stock_quantity = new_quantity.
5. INSERT audit_log with before/after, adjustment_type, reason.
6. Return updated part card.

**Audit:**
- Required: Yes
- Severity: MEDIUM
- Fields: old_quantity, new_quantity, adjustment_type, reason

**Permissions:**
- Allowed: HOD+, inventory managers

**Test Cases:**
- ✅ Correction with reason → updates stock
- ✅ Write-off with reason → reduces stock
- ❌ No reason → error "Reason required"
- ❌ Reason too short → error "Reason must be at least 10 characters"

---

# Remaining Clusters (Abbreviated Format)

Due to document length, remaining clusters follow abbreviated format. Full details available on request.

---

# Cluster 5: COMMUNICATE_STATUS (11 Actions)

## Action 35: add_to_handover
**Frontend Status:** ✅ AddToHandoverModal implemented
**Tables:** handover_items, handovers
**Operation:** LINKING
**Audit:** LOW

## Action 36: add_document_to_handover
**Tables:** handover_documents
**Operation:** LINKING
**Audit:** LOW

## Action 37: add_predictive_insight_to_handover
**Tables:** handover_insights
**Operation:** LINKING
**Audit:** LOW

## Action 38: edit_handover_section
**Tables:** handover_sections
**Operation:** UPDATE
**Audit:** LOW

## Action 39: export_handover
**Tables:** handovers
**Operation:** EXPORT (PDF generation)
**Audit:** LOW

## Action 40: regenerate_handover_summary
**Tables:** handovers, ai_summaries
**Operation:** UPDATE (AI call)
**Audit:** None

## Action 41: view_document
**Tables:** documents
**Operation:** VIEW
**Audit:** None

## Action 42: view_related_documents
**Tables:** documents
**Operation:** VIEW
**Audit:** None

## Action 43: view_document_section
**Tables:** documents
**Operation:** VIEW
**Audit:** None

## Action 44: edit_note
**Tables:** notes (generic), audit_logs
**Operation:** UPDATE
**Audit:** LOW
**Special:** Track edit history, show "Edited" badge

## Action 45: delete_item
**Tables:** multiple (notes, photos, attachments), audit_logs
**Operation:** UPDATE (soft delete)
**Audit:** MEDIUM
**Special:** 5-minute undo window, soft delete only

---

# Cluster 6: COMPLY_AUDIT (5 Actions)

## Action 46: view_hours_of_rest
**Tables:** hours_of_rest, users
**Operation:** VIEW
**Audit:** None

## Action 47: update_hours_of_rest
**Tables:** hours_of_rest, audit_logs
**Operation:** UPDATE
**Audit:** MEDIUM

## Action 48: export_hours_of_rest
**Tables:** hours_of_rest
**Operation:** EXPORT (PDF/Excel)
**Audit:** LOW

## Action 49: view_compliance_status
**Tables:** compliance_records
**Operation:** VIEW
**Audit:** None

## Action 50: tag_for_survey
**Tables:** work_items, audit_logs
**Operation:** UPDATE
**Audit:** LOW

---

# Cluster 7: PROCURE_SUPPLIERS (9 Actions)

## Action 51: create_purchase_request
**Frontend Status:** ✅ CreatePurchaseRequestModal implemented
**Tables:** purchase_requests, purchase_request_items, audit_logs
**Operation:** CREATE
**Audit:** MEDIUM

## Action 52: add_item_to_purchase
**Tables:** purchase_request_items
**Operation:** UPDATE
**Audit:** LOW

## Action 53: approve_purchase
**Tables:** purchase_requests, audit_logs, notifications
**Operation:** UPDATE
**Audit:** MEDIUM
**Special:** Notification if >$5,000

## Action 54: upload_invoice
**Tables:** invoices, purchase_requests
**Operation:** CREATE
**Audit:** MEDIUM

## Action 55: track_delivery
**Tables:** deliveries
**Operation:** VIEW
**Audit:** None

## Action 56: log_delivery_received
**Tables:** deliveries, parts (update stock), audit_logs
**Operation:** UPDATE
**Audit:** MEDIUM

## Action 57: update_purchase_status
**Tables:** purchase_requests
**Operation:** UPDATE
**Audit:** LOW

## Action 58: edit_purchase_details
**Tables:** purchase_requests, purchase_request_items
**Operation:** UPDATE
**Audit:** MEDIUM

## Action 59: edit_invoice_amount
**Frontend Status:** ✅ EditInvoiceAmountModal implemented
**Tables:** invoices, audit_logs, notifications
**Operation:** UPDATE
**Audit:** HIGH
**Special:** Required reason (15+ chars), notification if >$500 or >10% change

---

# Cluster 8: CHECKLIST (4 Actions)

## Action 60: view_checklist
**Tables:** checklists, checklist_items
**Operation:** VIEW
**Audit:** None

## Action 61: mark_checklist_item_complete
**Tables:** checklist_items, audit_logs
**Operation:** UPDATE
**Audit:** LOW

## Action 62: add_checklist_note
**Tables:** checklist_notes
**Operation:** CREATE
**Audit:** LOW

## Action 63: add_checklist_photo
**Tables:** checklist_attachments
**Operation:** CREATE
**Audit:** LOW

---

# Cluster 9: SHIPYARD/REFIT (4 Actions)

## Action 64: view_worklist
**Tables:** worklists, work_items
**Operation:** VIEW
**Audit:** None

## Action 65: add_worklist_task
**Tables:** work_items, audit_logs
**Operation:** CREATE
**Audit:** MEDIUM

## Action 66: update_worklist_progress
**Tables:** work_items
**Operation:** UPDATE
**Audit:** LOW

## Action 67: export_worklist
**Tables:** worklists
**Operation:** EXPORT (PDF/Excel)
**Audit:** LOW

---

# Appendix: Standard Test Case Template

For each action, backend engineer should verify:

**Success Cases:**
1. Happy path with valid, complete data
2. Happy path with minimal required data
3. Edge case: empty optional fields
4. Edge case: maximum allowed values
5. Idempotency: retry same request

**Failure Cases:**
1. Missing required field
2. Invalid field type (string instead of UUID)
3. Entity not found (invalid ID)
4. Entity from different yacht (RLS violation)
5. Insufficient permissions (wrong role)
6. Business rule violation (invalid state transition)
7. Constraint violation (stock insufficient, duplicate key)

---

**Last Updated:** 2025-11-21
**Author:** Frontend Team
**For:** Backend Implementation Team
