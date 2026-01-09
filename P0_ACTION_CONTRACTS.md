# P0 Action Contracts (JSON Schemas)

**Date:** 2026-01-08
**Status:** Contract Definition Phase
**Purpose:** Canonical request/response schemas for all 8 P0 actions

---

## Contract Principles

1. **All actions use the same envelope:**
   ```json
   {
     "action": "action_name",
     "context": { "yacht_id": "uuid", "user_id": "uuid", "role": "chief_engineer" },
     "payload": { /* action-specific fields */ }
   }
   ```

2. **All responses use the same envelope:**
   ```json
   {
     "status": "success" | "error",
     "action": "action_name",
     "result": { /* action-specific result */ },
     "error_code": "ERROR_CODE" | null,
     "message": "Human-readable message" | null
   }
   ```

3. **MUTATE actions have 3 endpoints:**
   - `GET /v1/actions/{action_name}/prefill` - Get pre-filled form data
   - `POST /v1/actions/{action_name}/preview` - Preview changes before commit
   - `POST /v1/actions/execute` - Execute the action (with signature)

4. **READ actions have 1 endpoint:**
   - `POST /v1/actions/execute` - Execute immediately

---

## Cluster 01: FIX_SOMETHING

### 1. show_manual_section

**Type:** READ
**Purpose:** Display the relevant manual section for equipment/fault
**Entry Conditions:** Fault page, Equipment page, Direct query
**Signature Required:** No

#### Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": {
      "type": "string",
      "const": "show_manual_section"
    },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["equipment_id"],
      "properties": {
        "equipment_id": {
          "type": "string",
          "format": "uuid",
          "description": "Equipment to show manual for"
        },
        "fault_code": {
          "type": "string",
          "description": "Optional fault code to jump to specific section"
        },
        "section_id": {
          "type": "string",
          "description": "Optional direct section ID"
        }
      }
    }
  }
}
```

#### Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "show_manual_section" },
    "result": {
      "type": "object",
      "required": ["document", "section"],
      "properties": {
        "document": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "title": { "type": "string" },
            "manufacturer": { "type": "string" },
            "model": { "type": "string" },
            "version": { "type": "string" },
            "storage_path": { "type": "string" },
            "signed_url": {
              "type": "string",
              "format": "uri",
              "description": "30-minute signed URL to PDF"
            },
            "page_count": { "type": "integer" }
          }
        },
        "section": {
          "type": "object",
          "properties": {
            "id": { "type": "string" },
            "title": { "type": "string" },
            "page_number": { "type": "integer" },
            "text_preview": { "type": "string", "maxLength": 500 }
          }
        },
        "related_sections": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": { "type": "string" },
              "title": { "type": "string" },
              "page_number": { "type": "integer" }
            }
          }
        }
      }
    }
  }
}
```

#### Error Codes

- `EQUIPMENT_NOT_FOUND` - Equipment ID doesn't exist
- `MANUAL_NOT_FOUND` - No manual available for this equipment
- `SECTION_NOT_FOUND` - Requested section doesn't exist
- `STORAGE_ACCESS_ERROR` - Failed to generate signed URL

---

## Cluster 02: DO_MAINTENANCE

### 2. create_work_order_from_fault

**Type:** MUTATE
**Purpose:** Convert fault observation into accountable work order
**Entry Conditions:** Fault page, Equipment page, Direct query (gated by intent)
**Signature Required:** Yes

#### Prefill Endpoint

**GET** `/v1/actions/create_work_order_from_fault/prefill?fault_id={uuid}`

**Response:**
```json
{
  "status": "success",
  "prefill_data": {
    "title": "Engine Room Deck 3 - Generator 2 (MTU 16V4000) - MTU-OVHT-01",
    "equipment_id": "uuid",
    "equipment_name": "Generator 2 (MTU 16V4000)",
    "location": "Engine Room Deck 3",
    "description": "Coolant temperature exceeding normal operating range.\n\nOccurrences: 8 in last 30 days",
    "priority": "normal",
    "fault_id": "uuid",
    "fault_code": "MTU-OVHT-01"
  },
  "duplicate_check": {
    "has_duplicate": false,
    "existing_wo": null
  }
}
```

**If duplicate found:**
```json
{
  "status": "success",
  "prefill_data": { /* same as above */ },
  "duplicate_check": {
    "has_duplicate": true,
    "existing_wo": {
      "id": "uuid",
      "number": "WO-2024-067",
      "status": "in_progress",
      "assigned_to": "Sarah Chen",
      "created_at": "2026-01-06T10:30:00Z"
    }
  }
}
```

#### Preview Endpoint

**POST** `/v1/actions/create_work_order_from_fault/preview`

**Request:**
```json
{
  "context": { "yacht_id": "uuid", "user_id": "uuid", "role": "chief_engineer" },
  "payload": {
    "fault_id": "uuid",
    "title": "Generator 2 - MTU-OVHT-01",
    "equipment_id": "uuid",
    "location": "Engine Room Deck 3",
    "description": "Coolant temperature exceeding normal...",
    "priority": "normal"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "preview": {
    "action": "create_work_order_from_fault",
    "summary": "You are about to create:",
    "entity_type": "work_order",
    "changes": {
      "title": "Generator 2 - MTU-OVHT-01",
      "equipment": "Generator 2 (MTU 16V4000)",
      "location": "Engine Room Deck 3",
      "priority": "Normal",
      "status": "Candidate",
      "linked_to": "Fault F-2024-089"
    },
    "side_effects": [
      "Work order will be created with status CANDIDATE",
      "Work order will be linked to fault F-2024-089",
      "Audit log entry will be created",
      "Fault status will NOT change (remains active)"
    ],
    "requires_signature": true,
    "warning": null
  }
}
```

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "create_work_order_from_fault" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["fault_id", "title", "equipment_id", "priority", "signature"],
      "properties": {
        "fault_id": { "type": "string", "format": "uuid" },
        "title": { "type": "string", "minLength": 3, "maxLength": 200 },
        "equipment_id": { "type": "string", "format": "uuid" },
        "location": { "type": "string", "maxLength": 100 },
        "description": { "type": "string", "maxLength": 5000 },
        "priority": {
          "type": "string",
          "enum": ["low", "normal", "high", "urgent"]
        },
        "signature": {
          "type": "object",
          "required": ["user_id", "timestamp"],
          "properties": {
            "user_id": { "type": "string", "format": "uuid" },
            "timestamp": { "type": "string", "format": "date-time" }
          }
        },
        "override_duplicate": {
          "type": "boolean",
          "default": false,
          "description": "Set to true if user chose 'Create New Anyway' after duplicate warning"
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "create_work_order_from_fault" },
    "result": {
      "type": "object",
      "required": ["work_order"],
      "properties": {
        "work_order": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "number": { "type": "string", "pattern": "^WO-\\d{4}-\\d{3}$" },
            "title": { "type": "string" },
            "equipment_id": { "type": "string", "format": "uuid" },
            "equipment_name": { "type": "string" },
            "location": { "type": "string" },
            "description": { "type": "string" },
            "priority": { "type": "string" },
            "status": { "const": "candidate" },
            "fault_id": { "type": "string", "format": "uuid" },
            "created_at": { "type": "string", "format": "date-time" },
            "created_by": { "type": "string", "format": "uuid" }
          }
        },
        "audit_log_id": { "type": "string", "format": "uuid" },
        "next_actions": {
          "type": "array",
          "items": { "type": "string" },
          "examples": [["add_note_to_work_order", "add_part_to_work_order", "view_work_order"]]
        }
      }
    },
    "message": { "type": "string", "example": "✓ WO-2024-089 created" }
  }
}
```

#### Error Codes

- `FAULT_NOT_FOUND` - Fault ID doesn't exist
- `EQUIPMENT_NOT_FOUND` - Equipment ID doesn't exist
- `DUPLICATE_WO_EXISTS` - Work order already exists for this fault (and override_duplicate=false)
- `SIGNATURE_REQUIRED` - Missing signature
- `INVALID_SIGNATURE` - Signature doesn't match user
- `VALIDATION_ERROR` - Required fields missing or invalid

---

### 3. add_note_to_work_order

**Type:** MUTATE
**Purpose:** Add context breadcrumb for whoever picks up this work next
**Entry Conditions:** Work order detail page
**Signature Required:** No (low-risk WRITE-NOTE action)

#### Prefill Endpoint

**GET** `/v1/actions/add_note_to_work_order/prefill?work_order_id={uuid}`

**Response:**
```json
{
  "status": "success",
  "prefill_data": {
    "work_order_id": "uuid",
    "work_order_number": "WO-2024-089",
    "equipment_name": "Generator 2 (MTU 16V4000)",
    "current_status": "in_progress"
  }
}
```

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "add_note_to_work_order" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["work_order_id", "note_text"],
      "properties": {
        "work_order_id": { "type": "string", "format": "uuid" },
        "note_text": {
          "type": "string",
          "minLength": 1,
          "maxLength": 5000,
          "description": "Note content"
        },
        "note_type": {
          "type": "string",
          "enum": ["general", "progress", "issue", "parts", "completion"],
          "default": "general"
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "add_note_to_work_order" },
    "result": {
      "type": "object",
      "required": ["note"],
      "properties": {
        "note": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "work_order_id": { "type": "string", "format": "uuid" },
            "note_text": { "type": "string" },
            "note_type": { "type": "string" },
            "created_at": { "type": "string", "format": "date-time" },
            "created_by": { "type": "string", "format": "uuid" },
            "created_by_name": { "type": "string" }
          }
        }
      }
    },
    "message": { "type": "string", "example": "Note added to WO-2024-089" }
  }
}
```

#### Error Codes

- `WO_NOT_FOUND` - Work order doesn't exist
- `WO_CLOSED` - Cannot add note to closed work order
- `VALIDATION_ERROR` - Note text empty or too long

---

### 4. add_part_to_work_order

**Type:** MUTATE
**Purpose:** Add parts to work order (shopping list, not deduction from inventory)
**Entry Conditions:** Work order detail page
**Signature Required:** No

#### Prefill Endpoint

**GET** `/v1/actions/add_part_to_work_order/prefill?work_order_id={uuid}&part_id={uuid}`

**Response:**
```json
{
  "status": "success",
  "prefill_data": {
    "work_order_id": "uuid",
    "work_order_number": "WO-2024-089",
    "part": {
      "id": "uuid",
      "name": "MTU Coolant Thermostat",
      "part_number": "MTU-12345",
      "unit": "each",
      "stock_available": 2,
      "stock_status": "IN_STOCK",
      "location": "Storeroom A - Shelf 3"
    },
    "suggested_quantity": 1
  }
}
```

#### Preview Endpoint

**POST** `/v1/actions/add_part_to_work_order/preview`

**Request:**
```json
{
  "context": { "yacht_id": "uuid", "user_id": "uuid" },
  "payload": {
    "work_order_id": "uuid",
    "part_id": "uuid",
    "quantity": 1,
    "notes": "Replacement for faulty thermostat"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "preview": {
    "action": "add_part_to_work_order",
    "summary": "You are about to add part to work order:",
    "changes": {
      "work_order": "WO-2024-089",
      "part": "MTU Coolant Thermostat (MTU-12345)",
      "quantity": "1 each",
      "notes": "Replacement for faulty thermostat"
    },
    "side_effects": [
      "Part will be ADDED to work order parts list",
      "Inventory will NOT be deducted (use 'mark_work_order_complete' or 'log_part_usage' to deduct)",
      "Parts list on WO will be updated",
      "Audit log entry will be created"
    ],
    "warnings": [
      "ℹ️  Current stock: 2 available. Sufficient for this work order."
    ],
    "requires_signature": false
  }
}
```

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "add_part_to_work_order" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["work_order_id", "part_id", "quantity"],
      "properties": {
        "work_order_id": { "type": "string", "format": "uuid" },
        "part_id": { "type": "string", "format": "uuid" },
        "quantity": {
          "type": "number",
          "minimum": 0.01,
          "description": "Quantity needed (not deducted yet)"
        },
        "notes": {
          "type": "string",
          "maxLength": 500,
          "description": "Optional note about part usage"
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "add_part_to_work_order" },
    "result": {
      "type": "object",
      "required": ["work_order_part"],
      "properties": {
        "work_order_part": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "work_order_id": { "type": "string", "format": "uuid" },
            "part_id": { "type": "string", "format": "uuid" },
            "part_name": { "type": "string" },
            "part_number": { "type": "string" },
            "quantity": { "type": "number" },
            "notes": { "type": "string" },
            "added_at": { "type": "string", "format": "date-time" },
            "added_by": { "type": "string", "format": "uuid" }
          }
        },
        "stock_warning": {
          "type": "boolean",
          "description": "True if stock is below minimum or out of stock"
        }
      }
    },
    "message": { "type": "string", "example": "Part added to WO-2024-089" }
  }
}
```

#### Error Codes

- `WO_NOT_FOUND` - Work order doesn't exist
- `PART_NOT_FOUND` - Part doesn't exist
- `WO_CLOSED` - Cannot add parts to closed work order
- `INVALID_QUANTITY` - Quantity must be positive

---

### 5. mark_work_order_complete

**Type:** MUTATE
**Purpose:** Sign your name to say "I did this work"
**Entry Conditions:** Work order detail page (status = in_progress)
**Signature Required:** Yes

#### Prefill Endpoint

**GET** `/v1/actions/mark_work_order_complete/prefill?work_order_id={uuid}`

**Response:**
```json
{
  "status": "success",
  "prefill_data": {
    "work_order_id": "uuid",
    "work_order_number": "WO-2024-089",
    "title": "Generator 2 - MTU-OVHT-01",
    "equipment_name": "Generator 2 (MTU 16V4000)",
    "current_status": "in_progress",
    "parts_list": [
      {
        "id": "uuid",
        "part_name": "MTU Coolant Thermostat",
        "part_number": "MTU-12345",
        "quantity": 1,
        "stock_available": 2
      }
    ],
    "notes_count": 3,
    "days_open": 2,
    "completion_summary": "Replaced faulty thermostat. Coolant temperature now within normal range."
  },
  "validation": {
    "can_complete": true,
    "warnings": [],
    "blockers": []
  }
}
```

**If validation fails:**
```json
{
  "status": "success",
  "prefill_data": { /* same as above */ },
  "validation": {
    "can_complete": false,
    "warnings": [
      "⚠️  No notes added to work order"
    ],
    "blockers": [
      "❌ Work order status is 'pending_parts' - cannot complete until parts arrive"
    ]
  }
}
```

#### Preview Endpoint

**POST** `/v1/actions/mark_work_order_complete/preview`

**Request:**
```json
{
  "context": { "yacht_id": "uuid", "user_id": "uuid", "role": "chief_engineer" },
  "payload": {
    "work_order_id": "uuid",
    "completion_notes": "Replaced thermostat. Tested under load. Temperature stable.",
    "parts_used": [
      { "part_id": "uuid", "quantity_used": 1 }
    ],
    "signature": {
      "user_id": "uuid",
      "timestamp": "2026-01-08T14:30:00Z"
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "preview": {
    "action": "mark_work_order_complete",
    "summary": "You are about to mark work order as complete:",
    "entity_type": "work_order",
    "changes": {
      "work_order": "WO-2024-089",
      "status_change": "in_progress → completed",
      "completion_notes": "Replaced thermostat. Tested under load...",
      "parts_to_deduct": [
        "MTU Coolant Thermostat (MTU-12345): 1 each"
      ],
      "completed_by": "John Smith (Chief Engineer)",
      "completed_at": "2026-01-08 14:30 UTC"
    },
    "side_effects": [
      "Work order status will change to COMPLETED",
      "Parts will be DEDUCTED from inventory",
      "Part usage log entries will be created",
      "Completion timestamp and signature will be recorded",
      "Audit log entry will be created",
      "Work order will appear in 'Completed' list"
    ],
    "inventory_changes": [
      {
        "part": "MTU Coolant Thermostat (MTU-12345)",
        "current_stock": 2,
        "after_deduction": 1,
        "warning": null
      }
    ],
    "requires_signature": true,
    "warnings": []
  }
}
```

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "mark_work_order_complete" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["work_order_id", "completion_notes", "signature"],
      "properties": {
        "work_order_id": { "type": "string", "format": "uuid" },
        "completion_notes": {
          "type": "string",
          "minLength": 10,
          "maxLength": 5000,
          "description": "Summary of work performed"
        },
        "parts_used": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["part_id", "quantity_used"],
            "properties": {
              "part_id": { "type": "string", "format": "uuid" },
              "quantity_used": { "type": "number", "minimum": 0.01 }
            }
          },
          "description": "Parts actually used (will be deducted from inventory)"
        },
        "signature": {
          "type": "object",
          "required": ["user_id", "timestamp"],
          "properties": {
            "user_id": { "type": "string", "format": "uuid" },
            "timestamp": { "type": "string", "format": "date-time" }
          }
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "mark_work_order_complete" },
    "result": {
      "type": "object",
      "required": ["work_order", "inventory_updates"],
      "properties": {
        "work_order": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "number": { "type": "string" },
            "status": { "const": "completed" },
            "completed_at": { "type": "string", "format": "date-time" },
            "completed_by": { "type": "string", "format": "uuid" },
            "completion_notes": { "type": "string" }
          }
        },
        "inventory_updates": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "part_id": { "type": "string", "format": "uuid" },
              "part_name": { "type": "string" },
              "quantity_deducted": { "type": "number" },
              "new_stock_level": { "type": "number" },
              "usage_log_id": { "type": "string", "format": "uuid" }
            }
          }
        },
        "audit_log_id": { "type": "string", "format": "uuid" }
      }
    },
    "message": { "type": "string", "example": "✓ WO-2024-089 marked complete" }
  }
}
```

#### Error Codes

- `WO_NOT_FOUND` - Work order doesn't exist
- `WO_ALREADY_COMPLETE` - Work order already marked complete
- `WO_NOT_IN_PROGRESS` - Work order must be in_progress to complete
- `SIGNATURE_REQUIRED` - Missing signature
- `INVALID_SIGNATURE` - Signature doesn't match user
- `INSUFFICIENT_STOCK` - Not enough stock for parts deduction
- `VALIDATION_ERROR` - Completion notes too short or missing

---

## Cluster 04: INVENTORY_PARTS

### 6. check_stock_level

**Type:** READ
**Purpose:** Look in the storeroom, not ask computer to guess
**Entry Conditions:** Part/inventory detail page, Direct query
**Signature Required:** No

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "check_stock_level" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["part_id"],
      "properties": {
        "part_id": {
          "type": "string",
          "format": "uuid",
          "description": "Part to check stock for"
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "check_stock_level" },
    "result": {
      "type": "object",
      "required": ["part", "stock"],
      "properties": {
        "part": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "name": { "type": "string" },
            "part_number": { "type": "string" },
            "category": { "type": "string" },
            "description": { "type": "string" },
            "unit": { "type": "string", "examples": ["each", "kg", "L", "m"] }
          }
        },
        "stock": {
          "type": "object",
          "properties": {
            "quantity_on_hand": { "type": "number" },
            "minimum_quantity": { "type": "number" },
            "maximum_quantity": { "type": "number" },
            "stock_status": {
              "type": "string",
              "enum": ["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK", "OVERSTOCKED"]
            },
            "location": { "type": "string", "description": "Physical storage location" },
            "last_counted_at": { "type": "string", "format": "date-time" },
            "last_counted_by": { "type": "string" }
          }
        },
        "usage_stats": {
          "type": "object",
          "properties": {
            "last_30_days": { "type": "number", "description": "Quantity used in last 30 days" },
            "average_monthly": { "type": "number" },
            "estimated_runout_days": { "type": "integer", "description": "Days until stock runs out at current usage rate" }
          }
        },
        "pending_orders": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "order_id": { "type": "string", "format": "uuid" },
              "quantity": { "type": "number" },
              "expected_delivery": { "type": "string", "format": "date" },
              "status": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

#### Error Codes

- `PART_NOT_FOUND` - Part doesn't exist
- `STOCK_DATA_UNAVAILABLE` - Stock tracking not configured for this part

---

### 7. log_part_usage

**Type:** MUTATE
**Purpose:** State "I took this from stores and used it for this job"
**Entry Conditions:** Part detail page, Work order completion flow
**Signature Required:** No

#### Prefill Endpoint

**GET** `/v1/actions/log_part_usage/prefill?part_id={uuid}&work_order_id={uuid}`

**Response:**
```json
{
  "status": "success",
  "prefill_data": {
    "part_id": "uuid",
    "part_name": "MTU Coolant Thermostat",
    "part_number": "MTU-12345",
    "unit": "each",
    "stock_available": 2,
    "work_order_id": "uuid",
    "work_order_number": "WO-2024-089",
    "suggested_quantity": 1,
    "usage_reason": "work_order"
  }
}
```

#### Preview Endpoint

**POST** `/v1/actions/log_part_usage/preview`

**Request:**
```json
{
  "context": { "yacht_id": "uuid", "user_id": "uuid" },
  "payload": {
    "part_id": "uuid",
    "quantity": 1,
    "work_order_id": "uuid",
    "usage_reason": "work_order",
    "notes": "Replaced faulty thermostat"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "preview": {
    "action": "log_part_usage",
    "summary": "You are about to log part usage:",
    "changes": {
      "part": "MTU Coolant Thermostat (MTU-12345)",
      "quantity": "1 each",
      "work_order": "WO-2024-089",
      "used_by": "John Smith",
      "used_at": "2026-01-08 14:35 UTC"
    },
    "side_effects": [
      "Inventory will be DEDUCTED by 1 each",
      "Part usage log entry will be created",
      "Stock level will change from 2 → 1",
      "Audit log entry will be created",
      "Usage will be attributed to your user account"
    ],
    "inventory_changes": [
      {
        "part": "MTU Coolant Thermostat (MTU-12345)",
        "current_stock": 2,
        "after_usage": 1,
        "warning": null
      }
    ],
    "requires_signature": false,
    "warnings": []
  }
}
```

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "log_part_usage" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["part_id", "quantity", "usage_reason"],
      "properties": {
        "part_id": { "type": "string", "format": "uuid" },
        "quantity": {
          "type": "number",
          "minimum": 0.01,
          "description": "Quantity used (will be deducted from stock)"
        },
        "work_order_id": {
          "type": "string",
          "format": "uuid",
          "description": "Optional work order this usage is for"
        },
        "equipment_id": {
          "type": "string",
          "format": "uuid",
          "description": "Optional equipment this part was used on"
        },
        "usage_reason": {
          "type": "string",
          "enum": ["work_order", "preventive_maintenance", "emergency_repair", "testing", "other"]
        },
        "notes": {
          "type": "string",
          "maxLength": 500,
          "description": "Optional note about usage"
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "log_part_usage" },
    "result": {
      "type": "object",
      "required": ["usage_log", "new_stock_level"],
      "properties": {
        "usage_log": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "part_id": { "type": "string", "format": "uuid" },
            "part_name": { "type": "string" },
            "quantity": { "type": "number" },
            "work_order_id": { "type": "string", "format": "uuid" },
            "equipment_id": { "type": "string", "format": "uuid" },
            "usage_reason": { "type": "string" },
            "notes": { "type": "string" },
            "used_at": { "type": "string", "format": "date-time" },
            "used_by": { "type": "string", "format": "uuid" },
            "used_by_name": { "type": "string" }
          }
        },
        "new_stock_level": {
          "type": "number",
          "description": "Stock level after deduction"
        },
        "stock_warning": {
          "type": "boolean",
          "description": "True if stock is now below minimum or out of stock"
        },
        "audit_log_id": { "type": "string", "format": "uuid" }
      }
    },
    "message": { "type": "string", "example": "Part usage logged" }
  }
}
```

#### Error Codes

- `PART_NOT_FOUND` - Part doesn't exist
- `INSUFFICIENT_STOCK` - Not enough stock to deduct requested quantity
- `INVALID_QUANTITY` - Quantity must be positive
- `WO_NOT_FOUND` - Work order doesn't exist (if work_order_id provided)

---

## Cluster 05: HANDOVER_COMMUNICATION

### 8. add_to_handover

**Type:** MUTATE
**Purpose:** Note to your future self (or person replacing you)
**Entry Conditions:** Fault page, Work order page, Equipment page, Document page (operational docs only)
**Signature Required:** No

#### Prefill Endpoint

**GET** `/v1/actions/add_to_handover/prefill?entity_type={type}&entity_id={uuid}`

**Response:**
```json
{
  "status": "success",
  "prefill_data": {
    "entity_type": "fault",
    "entity_id": "uuid",
    "title": "Generator 2 - MTU-OVHT-01",
    "summary_text": "Recurring overheating fault on Generator 2. Coolant temperature exceeding normal range. Occurred 8 times in last 30 days. Thermostat replaced on WO-2024-089.",
    "category": "ongoing_fault",
    "equipment_name": "Generator 2 (MTU 16V4000)",
    "location": "Engine Room Deck 3"
  }
}
```

**Pre-fill logic (from spec):**
```python
# Entity type determines category
if entity_type == "fault":
    category = "ongoing_fault"
elif entity_type == "work_order":
    category = "work_in_progress"
elif entity_type == "document":
    category = "important_info"
elif entity_type == "equipment":
    category = "equipment_status"
else:
    category = "general"

# Summary auto-generated from entity data
summary_text = f"{equipment_name} - {title}\n\n{description}"
```

#### Execute Request Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "context", "payload"],
  "properties": {
    "action": { "const": "add_to_handover" },
    "context": {
      "type": "object",
      "required": ["yacht_id", "user_id", "role"],
      "properties": {
        "yacht_id": { "type": "string", "format": "uuid" },
        "user_id": { "type": "string", "format": "uuid" },
        "role": { "type": "string" }
      }
    },
    "payload": {
      "type": "object",
      "required": ["entity_type", "entity_id", "summary_text", "category"],
      "properties": {
        "entity_type": {
          "type": "string",
          "enum": ["fault", "work_order", "equipment", "document_chunk", "part"]
        },
        "entity_id": { "type": "string", "format": "uuid" },
        "summary_text": {
          "type": "string",
          "minLength": 10,
          "maxLength": 2000,
          "description": "Summary of what needs to be handed over"
        },
        "category": {
          "type": "string",
          "enum": ["ongoing_fault", "work_in_progress", "important_info", "equipment_status", "general"]
        },
        "priority": {
          "type": "string",
          "enum": ["low", "normal", "high", "urgent"],
          "default": "normal"
        }
      }
    }
  }
}
```

#### Execute Response Schema (Success)

```json
{
  "type": "object",
  "required": ["status", "action", "result"],
  "properties": {
    "status": { "const": "success" },
    "action": { "const": "add_to_handover" },
    "result": {
      "type": "object",
      "required": ["handover_entry"],
      "properties": {
        "handover_entry": {
          "type": "object",
          "properties": {
            "id": { "type": "string", "format": "uuid" },
            "yacht_id": { "type": "string", "format": "uuid" },
            "entity_type": { "type": "string" },
            "entity_id": { "type": "string", "format": "uuid" },
            "summary_text": { "type": "string" },
            "category": { "type": "string" },
            "priority": { "type": "string" },
            "added_at": { "type": "string", "format": "date-time" },
            "added_by": { "type": "string", "format": "uuid" },
            "added_by_name": { "type": "string" }
          }
        }
      }
    },
    "message": { "type": "string", "example": "Added to handover" }
  }
}
```

#### Error Codes

- `ENTITY_NOT_FOUND` - Referenced entity doesn't exist
- `INVALID_ENTITY_TYPE` - Entity type not supported for handover
- `VALIDATION_ERROR` - Summary text too short or missing
- `DUPLICATE_ENTRY` - Entity already added to handover (allow override)

---

## Common Error Response Schema

All errors follow this format:

```json
{
  "status": "error",
  "action": "action_name",
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "Optional field that caused error",
    "expected": "Optional expected value",
    "received": "Optional received value"
  },
  "timestamp": "2026-01-08T14:30:00Z"
}
```

### Global Error Codes

- `UNAUTHORIZED` - Missing or invalid JWT
- `FORBIDDEN` - User doesn't have permission (role check failed)
- `YACHT_ISOLATION_VIOLATION` - Yacht ID mismatch
- `VALIDATION_ERROR` - Request schema validation failed
- `INTERNAL_ERROR` - Unexpected server error
- `RATE_LIMIT_EXCEEDED` - Too many requests

---

## Implementation Checklist

### Backend

- [ ] Create Pydantic models for all request/response schemas
- [ ] Add JSON Schema validation to action router
- [ ] Implement prefill endpoints for MUTATE actions
- [ ] Implement preview endpoints for MUTATE actions
- [ ] Add signature validation for signature-required actions
- [ ] Implement duplicate detection (create_work_order_from_fault)
- [ ] Add inventory deduction logic (mark_work_order_complete, log_part_usage)
- [ ] Create audit log entries for all MUTATE actions

### Frontend

- [ ] Create TypeScript types from JSON schemas
- [ ] Implement form components for each action
- [ ] Implement preview modals with side-effects display
- [ ] Add signature capture component
- [ ] Wire up prefill API calls
- [ ] Add validation error display
- [ ] Implement success/error toasts

### Database

- [ ] Create tables: work_orders, work_order_notes, work_order_parts
- [ ] Create tables: faults, parts, part_usage, handover
- [ ] Create table: audit_log
- [ ] Add RLS policies for all tables
- [ ] Create indices for performance

### Testing

- [ ] Test all happy paths
- [ ] Test all error cases
- [ ] Test signature validation
- [ ] Test inventory deduction edge cases
- [ ] Test duplicate detection
- [ ] Test RLS enforcement

---

**END OF P0 ACTION CONTRACTS**
