# Microaction-Workflow Master List
## Backbone for CelesteOS Action Execution

**Version:** 2.0
**Date:** November 21, 2025
**Total Actions:** 67
**Total Workflows:** 6

---

## Master Workflow Endpoints

| Endpoint | Archetype | Action Count | n8n File |
|----------|-----------|--------------|----------|
| `/workflows/view` | VIEW | 25 | `master-view-workflow.json` |
| `/workflows/create` | CREATE | 14 | `master-create-workflow.json` |
| `/workflows/update` | UPDATE | 18 | `master-update-workflow.json` |
| `/workflows/export` | EXPORT | 6 | `master-export-workflow.json` |
| `/workflows/rag` | RAG | 4 | `master-rag-workflow.json` |
| `/workflows/linking` | LINKING | 6 | `master-linking-workflow.json` |

---

## Microaction Registry

### Format

Each entry contains:
- **action_name** - Canonical identifier
- **archetype** - Which of 6 master workflows handles it
- **environments** - Where action is available (sea/port/shipyard/guest)
- **context_required** - What IDs/data must be passed
- **parameters** - User input fields
- **returns** - Card type + actions

---

## FAULT & DIAGNOSIS (7 actions)

### 1. diagnose_fault
- **Archetype:** RAG
- **Endpoint:** `/workflows/rag`
- **Environments:** sea, port, shipyard
- **Context Required:** `fault_id`, `equipment_id`
- **Parameters:** `user_input` (fault symptoms)
- **Returns:**
  - Card: `fault` with AI diagnosis
  - Actions: `create_work_order_from_fault`, `suggest_parts`, `add_fault_note`
- **n8n Logic:**
  1. Embed user query (OpenAI embeddings)
  2. Vector search manual sections (pgvector)
  3. LLM inference (Claude/GPT-4) with retrieved context
  4. Return diagnosis with confidence score

### 2. show_manual_section
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id`, `section_id` (optional)
- **Parameters:** `query` (what section to show)
- **Returns:**
  - Card: `document` with manual section
  - Actions: `view_related_documents`, `link_document_to_fault`
- **n8n Logic:** SELECT from `document_sections` WHERE equipment_id = ? AND section_title LIKE ?

### 3. view_fault_history
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id` OR `fault_id`
- **Parameters:** `time_range` (optional), `status_filter` (optional)
- **Returns:**
  - Card: `fault_list`
  - Actions: `diagnose_fault`, `create_work_order_from_fault`
- **n8n Logic:** SELECT * FROM faults WHERE equipment_id = ? ORDER BY created_at DESC

### 4. suggest_parts
- **Archetype:** RAG
- **Endpoint:** `/workflows/rag`
- **Environments:** sea, port, shipyard
- **Context Required:** `fault_id` OR `equipment_id`
- **Parameters:** `fault_description`
- **Returns:**
  - Card: `part_list`
  - Actions: `order_part`, `view_part_stock`
- **n8n Logic:** RAG search manual + fault history → LLM suggests parts

### 5. create_work_order_from_fault
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** `fault_id`, `equipment_id`
- **Parameters:** `title`, `description`, `priority`
- **Returns:**
  - Card: `work_order`
  - Actions: `add_work_order_note`, `add_parts_to_work_order`, `assign_work_order`
- **n8n Logic:** INSERT INTO work_orders (fault_id, equipment_id, ...) RETURNING *

### 6. add_fault_note
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `fault_id`
- **Parameters:** `note_text`
- **Returns:**
  - Card: `note`
  - Actions: `edit_note`, `delete_item`
- **n8n Logic:** INSERT INTO notes (entity_type='fault', entity_id, note_text) RETURNING *

### 7. add_fault_photo
- **Archetype:** LINKING
- **Endpoint:** `/workflows/linking`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `fault_id`
- **Parameters:** `photo_url`, `caption`
- **Returns:**
  - Card: `photo`
  - Actions: `add_note`, `delete_item`
- **n8n Logic:** INSERT INTO photos (entity_type='fault', entity_id, photo_url) RETURNING *

---

## WORK ORDER / PMS (8 actions)

### 8. create_work_order
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id` (optional), `fault_id` (optional)
- **Parameters:** `title`, `description`, `priority`, `assigned_to` (optional)
- **Returns:**
  - Card: `work_order`
  - Actions: `add_work_order_note`, `add_work_order_photo`, `add_parts_to_work_order`, `mark_work_order_complete`
- **n8n Logic:**
  ```sql
  INSERT INTO work_orders (yacht_id, title, description, priority, equipment_id, fault_id, created_by, status)
  VALUES (?, ?, ?, ?, ?, ?, ?, 'pending') RETURNING *;

  INSERT INTO audit_logs (action_name='create_work_order', ...) VALUES (...);
  ```

### 9. view_work_order_history
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id` OR `work_order_id`
- **Parameters:** `status_filter`, `time_range`
- **Returns:**
  - Card: `work_order_list`
  - Actions: `view_work_order_checklist`, `add_work_order_note`
- **n8n Logic:** SELECT * FROM work_orders WHERE equipment_id = ? ORDER BY created_at DESC LIMIT 20

### 10. mark_work_order_complete
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `work_order_id`
- **Parameters:** `completion_notes`, `hours_worked`
- **Returns:**
  - Card: `work_order`
  - Actions: `add_work_order_note`, `add_to_handover`
- **n8n Logic:**
  ```sql
  UPDATE work_orders SET status='completed', completed_at=NOW(), completion_notes=? WHERE id=? RETURNING *;
  INSERT INTO audit_logs (action_name='mark_work_order_complete', severity='low') VALUES (...);
  ```

### 11. add_work_order_note
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `work_order_id`
- **Parameters:** `note_text`
- **Returns:**
  - Card: `note`
  - Actions: `edit_note`, `delete_item`
- **n8n Logic:** INSERT INTO notes (entity_type='work_order', entity_id, note_text) RETURNING *

### 12. add_work_order_photo
- **Archetype:** LINKING
- **Endpoint:** `/workflows/linking`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `work_order_id`
- **Parameters:** `photo_url`, `caption`
- **Returns:**
  - Card: `photo`
  - Actions: `delete_item`
- **n8n Logic:** INSERT INTO photos (entity_type='work_order', entity_id, photo_url) RETURNING *

### 13. add_parts_to_work_order
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** `work_order_id`
- **Parameters:** `part_ids[]`, `quantities[]`
- **Returns:**
  - Card: `work_order`
  - Actions: `log_part_usage`, `order_part`
- **n8n Logic:** INSERT INTO work_order_parts (work_order_id, part_id, quantity) VALUES (?, ?, ?) RETURNING *

### 14. view_work_order_checklist
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `work_order_id`
- **Parameters:** none
- **Returns:**
  - Card: `checklist`
  - Actions: `mark_checklist_item_complete`, `add_checklist_note`
- **n8n Logic:** SELECT * FROM checklist_items WHERE work_order_id = ?

### 15. assign_work_order
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `work_order_id`
- **Parameters:** `assigned_to_user_id`
- **Returns:**
  - Card: `work_order`
  - Actions: `add_work_order_note`, `mark_work_order_complete`
- **n8n Logic:**
  ```sql
  UPDATE work_orders SET assigned_to=?, updated_at=NOW() WHERE id=? RETURNING *;
  INSERT INTO audit_logs (action_name='assign_work_order') VALUES (...);
  ```

---

## EQUIPMENT (6 actions)

### 16. view_equipment_details
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id`
- **Parameters:** none
- **Returns:**
  - Card: `equipment`
  - Actions: `view_equipment_history`, `view_equipment_parts`, `view_linked_faults`, `create_work_order`
- **n8n Logic:**
  ```sql
  SELECT e.*,
    COUNT(DISTINCT f.id) as fault_count,
    COUNT(DISTINCT wo.id) as work_order_count
  FROM equipment e
  LEFT JOIN faults f ON f.equipment_id = e.id AND f.status = 'open'
  LEFT JOIN work_orders wo ON wo.equipment_id = e.id
  WHERE e.id = ? GROUP BY e.id;
  ```

### 17. view_equipment_history
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id`
- **Parameters:** `time_range`, `event_type_filter`
- **Returns:**
  - Card: `history_timeline`
  - Actions: `view_equipment_details`, `view_equipment_manual`
- **n8n Logic:** SELECT * FROM equipment_events WHERE equipment_id = ? ORDER BY event_date DESC

### 18. view_equipment_parts
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id`
- **Parameters:** none
- **Returns:**
  - Card: `part_list`
  - Actions: `view_part_stock`, `order_part`
- **n8n Logic:** SELECT p.* FROM parts p JOIN equipment_parts ep ON ep.part_id = p.id WHERE ep.equipment_id = ?

### 19. view_linked_faults
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id`
- **Parameters:** `status_filter`
- **Returns:**
  - Card: `fault_list`
  - Actions: `diagnose_fault`, `create_work_order_from_fault`
- **n8n Logic:** SELECT * FROM faults WHERE equipment_id = ? AND status = ?

### 20. view_equipment_manual
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id`
- **Parameters:** `section_query` (optional)
- **Returns:**
  - Card: `document`
  - Actions: `show_manual_section`, `view_related_documents`
- **n8n Logic:** SELECT * FROM documents WHERE equipment_id = ? AND document_type = 'manual'

### 21. add_equipment_note
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `equipment_id`
- **Parameters:** `note_text`
- **Returns:**
  - Card: `note`
  - Actions: `edit_note`, `delete_item`
- **n8n Logic:** INSERT INTO notes (entity_type='equipment', entity_id, note_text) RETURNING *

---

## INVENTORY / PARTS (7 actions)

### 22. view_part_stock
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `part_id`
- **Parameters:** none
- **Returns:**
  - Card: `part`
  - Actions: `order_part`, `log_part_usage`, `view_part_usage`
- **n8n Logic:** SELECT * FROM parts WHERE id = ?

### 23. order_part
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** `part_id`
- **Parameters:** `quantity`, `urgency`, `supplier` (optional)
- **Returns:**
  - Card: `purchase`
  - Actions: `track_delivery`, `add_item_to_purchase`
- **n8n Logic:**
  ```sql
  INSERT INTO purchase_requests (part_id, quantity, urgency, created_by, status)
  VALUES (?, ?, ?, ?, 'pending') RETURNING *;
  ```

### 24. view_part_location
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `part_id`
- **Parameters:** none
- **Returns:**
  - Card: `part`
  - Actions: `scan_part_barcode`, `log_part_usage`
- **n8n Logic:** SELECT location, storage_details FROM parts WHERE id = ?

### 25. view_part_usage
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `part_id`
- **Parameters:** `time_range`
- **Returns:**
  - Card: `usage_history`
  - Actions: `log_part_usage`, `order_part`
- **n8n Logic:** SELECT * FROM part_usage WHERE part_id = ? ORDER BY used_at DESC

### 26. log_part_usage
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `part_id`
- **Parameters:** `quantity_used`, `work_order_id` (optional)
- **Returns:**
  - Card: `part`
  - Actions: `order_part` (if low stock)
- **n8n Logic:**
  ```sql
  INSERT INTO part_usage (part_id, quantity, work_order_id, used_by) VALUES (?, ?, ?, ?) RETURNING *;
  UPDATE parts SET stock_quantity = stock_quantity - ? WHERE id = ? RETURNING *;
  ```

### 27. scan_part_barcode
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** none
- **Parameters:** `barcode_data`
- **Returns:**
  - Card: `part`
  - Actions: `log_part_usage`, `order_part`, `view_part_stock`
- **n8n Logic:** SELECT * FROM parts WHERE barcode = ? OR part_number = ?

### 28. view_linked_equipment
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `part_id`
- **Parameters:** none
- **Returns:**
  - Card: `equipment_list`
  - Actions: `view_equipment_details`, `create_work_order`
- **n8n Logic:** SELECT e.* FROM equipment e JOIN equipment_parts ep ON ep.equipment_id = e.id WHERE ep.part_id = ?

---

## HANDOVER (6 actions)

### 29. add_to_handover
- **Archetype:** LINKING
- **Endpoint:** `/workflows/linking`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `entity_type`, `entity_id`
- **Parameters:** `section`, `content`, `priority`
- **Returns:**
  - Card: `handover`
  - Actions: `edit_handover_section`, `export_handover`
- **n8n Logic:**
  ```sql
  INSERT INTO handover_items (handover_id, section, entity_type, entity_id, content, priority)
  SELECT (SELECT id FROM handovers WHERE date = CURRENT_DATE LIMIT 1), ?, ?, ?, ?, ?
  RETURNING *;
  ```

### 30. add_document_to_handover
- **Archetype:** LINKING
- **Endpoint:** `/workflows/linking`
- **Environments:** sea, port, shipyard
- **Context Required:** `document_id`, `handover_id`
- **Parameters:** `section`, `notes`
- **Returns:**
  - Card: `handover`
  - Actions: `edit_handover_section`, `view_document`
- **n8n Logic:** INSERT INTO handover_documents (handover_id, document_id, section, notes) RETURNING *

### 31. add_predictive_insight_to_handover
- **Archetype:** RAG
- **Endpoint:** `/workflows/rag`
- **Environments:** sea, port
- **Context Required:** `equipment_id` OR `fault_id`
- **Parameters:** `insight_type`
- **Returns:**
  - Card: `handover`
  - Actions: `edit_handover_section`, `view_smart_summary`
- **n8n Logic:** LLM generates predictive insight → INSERT INTO handover_items

### 32. edit_handover_section
- **Archetype:** LINKING
- **Endpoint:** `/workflows/linking`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `handover_item_id`
- **Parameters:** `new_content`, `new_priority`
- **Returns:**
  - Card: `handover`
  - Actions: `export_handover`, `delete_item`
- **n8n Logic:**
  ```sql
  UPDATE handover_items SET content=?, priority=?, updated_at=NOW() WHERE id=? RETURNING *;
  INSERT INTO audit_logs (action_name='edit_handover_section') VALUES (...);
  ```

### 33. export_handover
- **Archetype:** EXPORT
- **Endpoint:** `/workflows/export`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `handover_id` OR `date_range`
- **Parameters:** `format` (pdf/docx)
- **Returns:**
  - Card: `export`
  - Actions: none
- **n8n Logic:**
  ```
  1. SELECT * FROM handovers WHERE date >= ? AND date <= ?
  2. Generate PDF from template
  3. Upload to Supabase Storage
  4. Return signed download URL
  ```

### 34. regenerate_handover_summary
- **Archetype:** EXPORT
- **Endpoint:** `/workflows/export`
- **Environments:** sea, port, shipyard
- **Context Required:** `handover_id`
- **Parameters:** none
- **Returns:**
  - Card: `handover`
  - Actions: `export_handover`, `edit_handover_section`
- **n8n Logic:** Collect all handover items → LLM summarizes → UPDATE handovers SET summary=?

---

## DOCUMENTS (3 actions)

### 35. view_document
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `document_id`
- **Parameters:** none
- **Returns:**
  - Card: `document`
  - Actions: `view_document_section`, `view_related_documents`, `link_document_to_equipment`
- **n8n Logic:** SELECT * FROM documents WHERE id = ?

### 36. view_related_documents
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `equipment_id` OR `document_id`
- **Parameters:** `document_type_filter`
- **Returns:**
  - Card: `document_list`
  - Actions: `view_document`, `add_document_to_handover`
- **n8n Logic:** SELECT * FROM documents WHERE equipment_id = ? OR category = ?

### 37. view_document_section
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard
- **Context Required:** `document_id`, `section_id` OR `section_name`
- **Parameters:** none
- **Returns:**
  - Card: `document`
  - Actions: `show_manual_section`, `add_document_section_to_handover`
- **n8n Logic:** SELECT * FROM document_sections WHERE document_id = ? AND section_name LIKE ?

---

## HOURS OF REST / COMPLIANCE (4 actions)

### 38. view_hours_of_rest
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, guest
- **Context Required:** `user_id` (optional, defaults to current user)
- **Parameters:** `date_range`
- **Returns:**
  - Card: `hor_table`
  - Actions: `update_hours_of_rest`, `export_hours_of_rest`, `view_compliance_status`
- **n8n Logic:**
  ```sql
  SELECT hr.*, u.name FROM hours_of_rest hr
  JOIN users u ON u.id = hr.user_id
  WHERE hr.user_id = ? AND hr.date >= ? AND hr.date <= ?
  ORDER BY hr.date DESC;
  ```

### 39. update_hours_of_rest
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, guest
- **Context Required:** `hor_id` OR `user_id` + `date`
- **Parameters:** `rest_hours`, `work_hours`
- **Returns:**
  - Card: `hor_table`
  - Actions: `export_hours_of_rest`, `view_compliance_status`
- **n8n Logic:**
  ```sql
  UPDATE hours_of_rest SET
    rest_hours=?, work_hours=?,
    is_compliant=(rest_hours >= 10),
    updated_at=NOW()
  WHERE id=? RETURNING *;
  ```

### 40. export_hours_of_rest
- **Archetype:** EXPORT
- **Endpoint:** `/workflows/export`
- **Environments:** sea, port, guest
- **Context Required:** `user_id` (optional), `date_range`
- **Parameters:** `format` (pdf/csv)
- **Returns:**
  - Card: `export`
  - Actions: none
- **n8n Logic:** SELECT * FROM hours_of_rest WHERE date >= ? → Generate PDF → Return download URL

### 41. view_compliance_status
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, guest
- **Context Required:** `user_id` (optional)
- **Parameters:** none
- **Returns:**
  - Card: `compliance_summary`
  - Actions: `update_hours_of_rest`, `export_hours_of_rest`
- **n8n Logic:**
  ```sql
  SELECT
    COUNT(*) as total_days,
    SUM(CASE WHEN is_compliant THEN 1 ELSE 0 END) as compliant_days,
    SUM(CASE WHEN is_compliant THEN 0 ELSE 1 END) as non_compliant_days
  FROM hours_of_rest WHERE user_id = ? AND date >= CURRENT_DATE - INTERVAL '30 days';
  ```

---

## PURCHASING / SUPPLIER (7 actions)

### 42. create_purchase_request
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** none
- **Parameters:** `title`, `description`, `priority`, `supplier` (optional)
- **Returns:**
  - Card: `purchase`
  - Actions: `add_item_to_purchase`, `approve_purchase`, `upload_invoice`
- **n8n Logic:**
  ```sql
  INSERT INTO purchase_requests (yacht_id, title, description, priority, created_by, status)
  VALUES (?, ?, ?, ?, ?, 'pending') RETURNING *;
  ```

### 43. add_item_to_purchase
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `item_name`, `quantity`, `unit_cost`, `part_id` (optional)
- **Returns:**
  - Card: `purchase`
  - Actions: `approve_purchase`, `update_purchase_status`
- **n8n Logic:** INSERT INTO purchase_items (purchase_id, item_name, quantity, unit_cost) RETURNING *

### 44. approve_purchase
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `approval_notes`
- **Returns:**
  - Card: `purchase`
  - Actions: `track_delivery`, `upload_invoice`
- **n8n Logic:**
  ```sql
  UPDATE purchase_requests SET status='approved', approved_by=?, approved_at=NOW() WHERE id=? RETURNING *;
  INSERT INTO audit_logs (action_name='approve_purchase', severity='medium') VALUES (...);
  ```

### 45. upload_invoice
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `file_url`, `invoice_number`, `invoice_amount`
- **Returns:**
  - Card: `purchase`
  - Actions: `edit_invoice_amount`, `log_delivery_received`
- **n8n Logic:** UPDATE purchase_requests SET invoice_url=?, invoice_number=?, invoice_amount=? WHERE id=? RETURNING *

### 46. track_delivery
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `tracking_number`, `estimated_arrival`
- **Returns:**
  - Card: `purchase`
  - Actions: `log_delivery_received`, `update_purchase_status`
- **n8n Logic:** UPDATE purchase_requests SET tracking_number=?, estimated_arrival=? WHERE id=? RETURNING *

### 47. log_delivery_received
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `received_notes`, `received_by`
- **Returns:**
  - Card: `purchase`
  - Actions: `add_item_to_purchase` (for discrepancies)
- **n8n Logic:**
  ```sql
  UPDATE purchase_requests SET status='received', received_at=NOW(), received_by=? WHERE id=? RETURNING *;
  -- Also update part stock if part_id linked
  UPDATE parts SET stock_quantity = stock_quantity + ? WHERE id IN (SELECT part_id FROM purchase_items WHERE purchase_id=?);
  ```

### 48. update_purchase_status
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `new_status`, `notes`
- **Returns:**
  - Card: `purchase`
  - Actions: `track_delivery`, `log_delivery_received`
- **n8n Logic:** UPDATE purchase_requests SET status=?, notes=?, updated_at=NOW() WHERE id=? RETURNING *

---

## OPERATIONAL CHECKLISTS (4 actions)

### 49. view_checklist
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `checklist_id` OR `checklist_type`
- **Parameters:** none
- **Returns:**
  - Card: `checklist`
  - Actions: `mark_checklist_item_complete`, `add_checklist_note`, `add_checklist_photo`
- **n8n Logic:** SELECT * FROM checklists WHERE id = ? OR checklist_type = ?

### 50. mark_checklist_item_complete
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `checklist_item_id`
- **Parameters:** `notes` (optional)
- **Returns:**
  - Card: `checklist`
  - Actions: `add_checklist_note`, `view_checklist`
- **n8n Logic:**
  ```sql
  UPDATE checklist_items SET is_completed=TRUE, completed_by=?, completed_at=NOW(), notes=? WHERE id=? RETURNING *;
  -- Check if all items completed
  UPDATE checklists SET completed_at=NOW() WHERE id=? AND NOT EXISTS (SELECT 1 FROM checklist_items WHERE checklist_id=? AND is_completed=FALSE);
  ```

### 51. add_checklist_note
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `checklist_id` OR `checklist_item_id`
- **Parameters:** `note_text`
- **Returns:**
  - Card: `note`
  - Actions: `edit_note`, `delete_item`
- **n8n Logic:** INSERT INTO notes (entity_type='checklist', entity_id, note_text) RETURNING *

### 52. add_checklist_photo
- **Archetype:** LINKING
- **Endpoint:** `/workflows/linking`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `checklist_id` OR `checklist_item_id`
- **Parameters:** `photo_url`, `caption`
- **Returns:**
  - Card: `photo`
  - Actions: `delete_item`
- **n8n Logic:** INSERT INTO photos (entity_type='checklist', entity_id, photo_url) RETURNING *

---

## SHIPYARD / REFIT (5 actions)

### 53. view_worklist
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** shipyard
- **Context Required:** none
- **Parameters:** `status_filter`, `category_filter`
- **Returns:**
  - Card: `worklist`
  - Actions: `add_worklist_task`, `update_worklist_progress`, `export_worklist`
- **n8n Logic:** SELECT * FROM worklist_tasks WHERE yacht_id = ? AND status IN (?)

### 54. add_worklist_task
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** shipyard
- **Context Required:** none
- **Parameters:** `title`, `description`, `category`, `priority`
- **Returns:**
  - Card: `worklist`
  - Actions: `update_worklist_progress`, `add_checklist_note`
- **n8n Logic:** INSERT INTO worklist_tasks (yacht_id, title, description, category, priority, status) VALUES (?, ?, ?, ?, ?, 'pending') RETURNING *

### 55. update_worklist_progress
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** shipyard
- **Context Required:** `worklist_task_id`
- **Parameters:** `new_status`, `progress_percentage`, `notes`
- **Returns:**
  - Card: `worklist`
  - Actions: `add_checklist_note`, `tag_for_survey`
- **n8n Logic:** UPDATE worklist_tasks SET status=?, progress=?, notes=?, updated_at=NOW() WHERE id=? RETURNING *

### 56. export_worklist
- **Archetype:** EXPORT
- **Endpoint:** `/workflows/export`
- **Environments:** shipyard
- **Context Required:** none
- **Parameters:** `format` (pdf/csv)
- **Returns:**
  - Card: `export`
  - Actions: none
- **n8n Logic:** SELECT * FROM worklist_tasks WHERE yacht_id = ? → Generate PDF → Return download URL

### 57. tag_for_survey
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** shipyard
- **Context Required:** `worklist_task_id` OR `equipment_id`
- **Parameters:** `survey_type`, `notes`
- **Returns:**
  - Card: `worklist`
  - Actions: `add_checklist_note`, `update_worklist_progress`
- **n8n Logic:** UPDATE worklist_tasks SET tagged_for_survey=TRUE, survey_type=?, survey_notes=? WHERE id=? RETURNING *

---

## FLEET / MANAGEMENT (3 actions)

### 58. view_fleet_summary
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** port, shipyard (management only)
- **Context Required:** none
- **Parameters:** none
- **Returns:**
  - Card: `fleet_summary`
  - Actions: `open_vessel`, `export_fleet_summary`
- **n8n Logic:**
  ```sql
  SELECT
    yacht_id, yacht_name, location, status,
    (SELECT COUNT(*) FROM faults WHERE yacht_id=y.id AND status='open') as open_faults,
    (SELECT COUNT(*) FROM work_orders WHERE yacht_id=y.id AND status='pending') as pending_work_orders
  FROM yachts y;
  ```

### 59. open_vessel
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** port, shipyard (management only)
- **Context Required:** `yacht_id`
- **Parameters:** none
- **Returns:**
  - Card: `smart_summary`
  - Actions: `view_equipment_details`, `view_work_order_history`, `view_fleet_summary`
- **n8n Logic:** Switch user session to selected yacht_id → Return dashboard summary

### 60. export_fleet_summary
- **Archetype:** EXPORT
- **Endpoint:** `/workflows/export`
- **Environments:** port, shipyard (management only)
- **Context Required:** none
- **Parameters:** `format` (pdf/excel)
- **Returns:**
  - Card: `export`
  - Actions: none
- **n8n Logic:** SELECT fleet data → Generate Excel/PDF → Return download URL

---

## PREDICTIVE / SMART SUMMARY (2 actions)

### 61. request_predictive_insight
- **Archetype:** RAG
- **Endpoint:** `/workflows/rag`
- **Environments:** sea, port
- **Context Required:** `equipment_id` OR `fault_id`
- **Parameters:** `insight_type` (failure_prediction, maintenance_recommendation, etc.)
- **Returns:**
  - Card: `smart_summary`
  - Actions: `add_predictive_insight_to_handover`, `create_work_order`
- **n8n Logic:**
  1. Collect equipment history, fault patterns, usage data
  2. LLM analyzes with prompt: "Predict potential failures based on: ..."
  3. Return prediction with confidence score

### 62. view_smart_summary
- **Archetype:** VIEW
- **Endpoint:** `/workflows/view`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** none
- **Parameters:** `date` (optional, defaults to today)
- **Returns:**
  - Card: `smart_summary`
  - Actions: `add_to_handover`, `view_equipment_details`, `create_work_order`
- **n8n Logic:**
  1. SELECT summary FROM smart_summaries WHERE date = ?
  2. If not exists: Generate new summary via LLM
  3. Return insights, recommendations, priorities

---

## MOBILE-SPECIFIC (2 actions)

### 63. upload_photo
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** none (will be linked later)
- **Parameters:** `photo_data` (base64), `caption`
- **Returns:**
  - Card: `photo`
  - Actions: `add_fault_photo`, `add_work_order_photo`, `delete_item`
- **n8n Logic:**
  1. Upload photo to Supabase Storage
  2. INSERT INTO photos (photo_url, caption, uploaded_by) RETURNING *
  3. Return photo_url for linking

### 64. record_voice_note
- **Archetype:** EXPORT
- **Endpoint:** `/workflows/export`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** none
- **Parameters:** `audio_data` (base64)
- **Returns:**
  - Card: `note`
  - Actions: `add_note`, `add_to_handover`
- **n8n Logic:**
  1. Upload audio to Supabase Storage
  2. Transcribe audio (Whisper API)
  3. INSERT INTO notes (note_text=transcription, audio_url) RETURNING *

---

## EDIT ACTIONS - ADDENDUM (10 actions)

### 65. edit_work_order_details
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `work_order_id`
- **Parameters:** `title` (optional), `description` (optional), `priority` (optional), `reason` (required for audit)
- **Returns:**
  - Card: `work_order`
  - Actions: `add_work_order_note`, `mark_work_order_complete`
- **n8n Logic:**
  ```sql
  -- Get old values for audit
  SELECT title, description, priority INTO old_values FROM work_orders WHERE id=?;
  -- Update
  UPDATE work_orders SET title=COALESCE(?, title), description=COALESCE(?, description), priority=COALESCE(?, priority) WHERE id=? RETURNING *;
  -- Audit
  INSERT INTO audit_logs (action_name='edit_work_order_details', severity='medium', old_value, new_value, reason) VALUES (...);
  ```

### 66. edit_equipment_details
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard
- **Context Required:** `equipment_id`
- **Parameters:** `name`, `location`, `status`, `reason` (required)
- **Returns:**
  - Card: `equipment`
  - Actions: `view_equipment_history`, `add_equipment_note`
- **n8n Logic:** Similar to edit_work_order_details with audit logging

### 67. edit_part_details
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard
- **Context Required:** `part_id`
- **Parameters:** `part_name`, `location`, `min_stock_level`, `reason` (required)
- **Returns:**
  - Card: `part`
  - Actions: `order_part`, `log_part_usage`
- **n8n Logic:** Update with audit logging

### 68. edit_purchase_details
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard
- **Context Required:** `purchase_id`
- **Parameters:** `title`, `description`, `supplier`, `reason` (required)
- **Returns:**
  - Card: `purchase`
  - Actions: `approve_purchase`, `upload_invoice`
- **n8n Logic:** Update with audit logging

### 69. edit_invoice_amount ⚠️ HIGH AUDIT
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard (HOD/Management only)
- **Context Required:** `purchase_id`
- **Parameters:** `new_amount`, `reason` (required, min 20 chars)
- **Returns:**
  - Card: `purchase`
  - Actions: `approve_purchase`, `track_delivery`
- **n8n Logic:**
  ```sql
  -- Get old amount
  SELECT invoice_amount INTO old_amount FROM purchases WHERE id=?;
  -- Calculate change
  SET amount_change = ABS(new_amount - old_amount);
  SET percentage_change = (amount_change / old_amount) * 100;
  -- Update
  UPDATE purchases SET
    invoice_amount=new_amount,
    requires_review=(amount_change > 500 OR percentage_change > 10),
    updated_at=NOW()
  WHERE id=? RETURNING *;
  -- HIGH PRIORITY audit log
  INSERT INTO audit_logs (action_name='edit_invoice_amount', severity='high', old_value, new_value, reason) VALUES (...);
  -- Email notification if threshold exceeded
  IF amount_change > 500 OR percentage_change > 10 THEN
    sendEmail(management, 'Invoice amount changed: ...');
  END IF;
  ```

### 70. edit_fault_details
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard
- **Context Required:** `fault_id`
- **Parameters:** `title`, `description`, `severity`, `reason` (required)
- **Returns:**
  - Card: `fault`
  - Actions: `diagnose_fault`, `create_work_order_from_fault`
- **n8n Logic:** Update with audit logging

### 71. edit_note
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `note_id`
- **Parameters:** `new_text`
- **Returns:**
  - Card: `note`
  - Actions: `delete_item`
- **n8n Logic:** UPDATE notes SET note_text=?, updated_at=NOW() WHERE id=? AND created_by=? RETURNING *

### 72. delete_item ⚠️ SOFT DELETE
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** sea, port, shipyard, guest
- **Context Required:** `entity_type`, `entity_id`
- **Parameters:** `reason` (required)
- **Returns:**
  - Card: `confirmation`
  - Actions: none
- **n8n Logic:**
  ```sql
  -- Soft delete (preserves data)
  UPDATE {entity_type} SET deleted_at=NOW(), deleted_by=?, deletion_reason=? WHERE id=? RETURNING *;
  INSERT INTO audit_logs (action_name='delete_item', severity='medium', entity_type, entity_id, reason) VALUES (...);
  ```

### 73. approve_work_order
- **Archetype:** UPDATE
- **Endpoint:** `/workflows/update`
- **Environments:** port, shipyard (HOD/Chief only)
- **Context Required:** `work_order_id`
- **Parameters:** `approval_notes`
- **Returns:**
  - Card: `work_order`
  - Actions: `assign_work_order`, `add_work_order_note`
- **n8n Logic:** UPDATE work_orders SET status='approved', approved_by=?, approved_at=NOW() WHERE id=? RETURNING *

### 74. scan_equipment_barcode
- **Archetype:** CREATE
- **Endpoint:** `/workflows/create`
- **Environments:** sea, port, shipyard
- **Context Required:** none
- **Parameters:** `barcode_data`
- **Returns:**
  - Card: `equipment`
  - Actions: `view_equipment_details`, `view_equipment_history`, `create_work_order`
- **n8n Logic:** SELECT * FROM equipment WHERE barcode = ? OR serial_number = ?

---

## Environment Definitions

| Environment | Description | Available Actions |
|-------------|-------------|-------------------|
| **sea** | Vessel underway | All except shipyard-specific (worklist, tag_for_survey) |
| **port** | Vessel docked | All except shipyard-specific |
| **shipyard** | Vessel in refit | All including worklist, tag_for_survey |
| **guest** | Guest/charter trip | Limited: view_*, add_note, add_photo, view_smart_summary |

---

## Quick Reference

**Archetype Distribution:**
- VIEW: 25 actions (37%)
- CREATE: 14 actions (21%)
- UPDATE: 18 actions (27%)
- EXPORT: 6 actions (9%)
- RAG: 4 actions (6%)
- LINKING: 6 actions (9%)

**Total:** 67 actions → 6 workflows

**Audit Logging Required:**
- All UPDATE actions
- All CREATE actions (low severity)
- Edit actions (medium/high severity)

**Role Restrictions:**
- Most actions: crew, ETO, Chief, Captain
- Approve actions: HOD, Chief, Captain
- Edit invoice: Chief, Captain, Management only
- Fleet management: Management only

---

## Implementation Notes

1. **Switch Node Pattern:** Each master workflow uses n8n switch node to branch on `action_name`
2. **Unified Payload:** All actions send: `{ action_name, context, parameters, session }`
3. **Unified Response:** All actions return: `{ success, card_type, card, micro_actions, streaming_chunks }`
4. **Audit Logging:** Automatic for all mutations, severity-based for edits
5. **JWT Validation:** Every workflow validates token → extracts user_id, yacht_id
6. **RLS:** Supabase Row Level Security ensures yacht_id isolation

---

**Next Steps:**
1. Import 6 workflows into n8n
2. Configure Supabase credentials
3. Activate workflows
4. Test each archetype with sample payloads
5. Monitor execution logs
6. Expand switch nodes to handle all 67 actions (currently showing ~5 per workflow as examples)
