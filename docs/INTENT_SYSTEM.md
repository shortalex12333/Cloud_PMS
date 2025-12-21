# Intent Classification System

## Overview

The intent parser classifies user queries into 67 intents across 9 categories, determines query type, and routes to appropriate processing lanes.

```
Query → IntentParser → route_to_lane() → Lane Assignment
                ↓
    {intent, category, query_type, requires_mutation}
```

---

## Query Types

| Type | Description | Handler | Example |
|------|-------------|---------|---------|
| `search` | Find documents, equipment, faults | Render | "MTU 16V4000 manual" |
| `aggregation` | Stats, counts, "most/least" queries | Render | "what machines failing most" |
| `mutation` | Create, update, delete operations | n8n | "create work order for engine" |
| `compliance` | HOR, certificates, audits | Render | "who hasn't completed HOR" |
| `lookup` | Inventory location, stock check | Render | "show me box 3d contents" |

---

## Processing Lanes

| Lane | Skip GPT | When Used |
|------|----------|-----------|
| `NO_LLM` | Yes | Simple lookups, direct patterns (WO-1234, CAT manual) |
| `RULES_ONLY` | Yes | Command patterns (create/open/close work order) |
| `GPT` | No | Problem diagnosis, aggregations, compliance, complex queries |
| `BLOCKED` | Yes | Paste dumps (>50 words), too vague (≤2 words), non-domain |

---

## Lane Trigger Reasons

| Reason | Triggers Lane | Condition |
|--------|---------------|-----------|
| `paste_dump` | BLOCKED | >50 words or >300 chars |
| `too_vague` | BLOCKED | ≤2 words + generic intent |
| `non_domain` | BLOCKED | Non-maritime queries (bitcoin, weather, jokes) |
| `direct_lookup_pattern` | NO_LLM | Matches WO-1234, E047, CAT 3512 manual |
| `simple_lookup` | NO_LLM | ≤4 words + find_document/find_part intent |
| `command_pattern` | RULES_ONLY | Starts with create/open/close/log/add/schedule |
| `problem_words` | GPT | Contains overheating, leak, fault, alarm, etc. |
| `temporal_context` | GPT | Contains "before charter", "since yesterday", etc. |
| `diagnosis_intent` | GPT | Intent is diagnose_fault or report_fault |
| `aggregation_query` | GPT | query_type == aggregation |
| `compliance_query` | GPT | query_type == compliance |
| `complex_query` | GPT | Generic intent + ≥5 words |
| `default_fallback` | NO_LLM | No other conditions matched |

---

## Intent Categories (9)

### 1. fix_something
| Intent | Description |
|--------|-------------|
| `diagnose_fault` | Identify cause of problem |
| `report_fault` | Log a new fault |
| `show_manual_section` | Find relevant manual section |
| `view_fault_history` | See past faults for equipment |
| `suggest_parts` | Recommend parts for repair |
| `create_work_order_from_fault` | Create WO from fault report |
| `add_fault_note` | Add note to existing fault |
| `add_fault_photo` | Attach photo to fault |
| `link_equipment_to_fault` | Associate equipment with fault |

### 2. do_maintenance
| Intent | Description |
|--------|-------------|
| `create_work_order` | Create new work order |
| `view_work_order_history` | See WO history |
| `mark_work_order_complete` | Complete a WO |
| `complete_work_order` | Same as above |
| `add_work_order_note` | Add note to WO |
| `add_work_order_photo` | Attach photo to WO |
| `add_parts_to_work_order` | Add parts to WO |
| `link_parts_to_work_order` | Link parts to WO |
| `view_work_order_checklist` | See WO checklist |
| `assign_work_order` | Assign WO to crew |
| `edit_work_order_details` | Modify WO details |
| `view_checklist` | View maintenance checklist |
| `mark_checklist_item_complete` | Complete checklist item |

### 3. manage_equipment
| Intent | Description |
|--------|-------------|
| `view_equipment_details` | See equipment info |
| `view_equipment_history` | See equipment history |
| `view_equipment_parts` | See parts for equipment |
| `view_linked_faults` | See faults for equipment |
| `view_equipment_manual` | Find equipment manual |
| `add_equipment_note` | Add note to equipment |
| `request_predictive_insight` | Get AI prediction |
| `view_smart_summary` | Get AI summary |

### 4. control_inventory
| Intent | Description |
|--------|-------------|
| `view_part_stock` | Check stock levels |
| `add_part` | Add new part to inventory |
| `order_part` | Order parts from supplier |
| `view_part_location` | Find part location (box 3d) |
| `view_part_usage` | See part usage history |
| `log_part_usage` | Log part consumption |
| `edit_part_quantity` | Update stock quantity |
| `scan_part_barcode` | Scan part barcode |
| `view_linked_equipment` | See equipment using part |

### 5. communicate_status
| Intent | Description |
|--------|-------------|
| `add_to_handover` | Add item to handover |
| `add_document_to_handover` | Attach doc to handover |
| `add_predictive_insight_to_handover` | Add AI insight |
| `edit_handover_section` | Edit handover section |
| `export_handover` | Export handover PDF |
| `regenerate_handover_summary` | Regenerate AI summary |
| `upload_photo` | Upload photo |
| `record_voice_note` | Record voice memo |

### 6. comply_audit
| Intent | Description |
|--------|-------------|
| `view_hours_of_rest` | Check HOR status |
| `update_hours_of_rest` | Log HOR entry |
| `export_hours_of_rest` | Export HOR report |
| `view_compliance_status` | Check compliance status |
| `tag_for_survey` | Tag item for survey |

### 7. procure_suppliers
| Intent | Description |
|--------|-------------|
| `create_purchase_request` | Create purchase request |
| `add_item_to_purchase` | Add item to PR |
| `approve_purchase` | Approve purchase |
| `upload_invoice` | Upload invoice |
| `track_delivery` | Track shipment |
| `log_delivery_received` | Log received delivery |
| `update_purchase_status` | Update PR status |

### 8. search_documents
| Intent | Description |
|--------|-------------|
| `find_document` | Search for document |
| `view_document` | Open document |
| `view_related_documents` | See related docs |
| `view_document_section` | Jump to section |

### 9. analytics
| Intent | Description |
|--------|-------------|
| `view_failure_stats` | Failure statistics |
| `view_maintenance_stats` | Maintenance statistics |
| `view_inventory_stats` | Inventory statistics |
| `view_compliance_stats` | Compliance statistics |

---

## Mutation Intents (Route to n8n)

These intents require `requires_mutation: true` and route to n8n webhooks:

```
create_work_order, create_work_order_from_fault,
mark_work_order_complete, complete_work_order,
add_work_order_note, add_work_order_photo,
add_fault_note, add_fault_photo, report_fault,
order_part, add_part, log_part_usage, edit_part_quantity,
add_to_handover, edit_handover_section,
update_hours_of_rest,
create_purchase_request, approve_purchase, log_delivery_received,
assign_work_order, edit_work_order_details
```

---

## Output Structure

```json
{
  "query": "create work order for stabilizer fault",
  "intent": {
    "action": "create_work_order",
    "category": "do_maintenance",
    "query_type": "mutation",
    "confidence": 0.5,
    "requires_mutation": true
  },
  "entities": [
    {"type": "equipment", "value": "stabilizer", "canonical": "STABILIZER"}
  ],
  "unknowns": ["create", "work", "order"],
  "routing": {
    "handler": "n8n",
    "webhook": "/webhook/create_work_order",
    "method": "POST"
  },
  "processing_time_ms": 19.15
}
```

---

## Frontend Button Logic

Use these fields for UI:

| Field | Use |
|-------|-----|
| `requires_mutation` | Show action button (n8n) vs info display |
| `routing.handler` | "n8n" = action, "render" = read |
| `intent.action` | Specific action for button label |
| `intent.category` | Group buttons by category |
| `query_type` | Icon/color coding |
