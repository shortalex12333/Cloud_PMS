# E2E Testing Evidence - Sun  8 Feb 2026 16:56:12 EST

## Test Environment
- API URL: https://pipeline-core.int.celeste7.ai
- Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
- Date: Sun  8 Feb 2026 16:56:12 EST

---


## Test: v2_search_crew_parts_query

**Request:**
```
POST /v2/search
{"query_text":"parts low in stock"}
```

**HTTP Status:** 200

**Response Body:**
```json
{
  "success": true,
  "request_id": "ab177176-6cf",
  "results": [],
  "results_by_domain": {
    "graph_nodes": []
  },
  "total_count": 0,
  "context": {
    "domain": "parts",
    "domain_confidence": 0.9,
    "intent": "READ",
    "intent_confidence": 0.8,
    "mode": "hybrid",
    "filters": {
      "time_window_days": 90,
      "scopes": [
        "parts"
      ]
    }
  },
  "actions": [
    {
      "action_id": "check_stock_level",
      "label": "Check Stock Level",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "deckhand",
        "steward",
        "chef",
        "bosun",
        "engineer",
        "eto",
        "chief_engineer",
        "chief_officer",
        "chief_steward",
        "purser",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_part_details",
      "label": "View Part Details",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "deckhand",
        "bosun",
        "eto",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    }
  ],
  "trust": {
    "path": "hybrid",
    "scopes": [
      "parts"
    ],
    "time_window_days": 90,
    "used_vector": true,
    "explain": "Hybrid search: SQL filters + semantic on 'parts low in stock...'"
  },
  "timing_ms": {
    "orchestration": 1164.9,
    "execution": 291.8,
    "total": 1456.8
  },
  "debug": null,
  "error": null
}
```

**Result:** ✅ PASS

---

## Test: v2_search_hod_parts_query

**Request:**
```
POST /v2/search
{"query_text":"parts low in stock"}
```

**HTTP Status:** 200

**Response Body:**
```json
{
  "success": true,
  "request_id": "5fb5e892-5bd",
  "results": [],
  "results_by_domain": {
    "graph_nodes": []
  },
  "total_count": 0,
  "context": {
    "domain": "parts",
    "domain_confidence": 0.9,
    "intent": "READ",
    "intent_confidence": 0.8,
    "mode": "hybrid",
    "filters": {
      "time_window_days": 90,
      "scopes": [
        "parts"
      ]
    }
  },
  "actions": [
    {
      "action_id": "check_stock_level",
      "label": "Check Stock Level",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "deckhand",
        "steward",
        "chef",
        "bosun",
        "engineer",
        "eto",
        "chief_engineer",
        "chief_officer",
        "chief_steward",
        "purser",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "log_part_usage",
      "label": "Log Part Usage",
      "variant": "MUTATE",
      "allowed_roles": [
        "engineer",
        "eto",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id",
        "quantity",
        "usage_reason"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "consume_part",
      "label": "Consume Part",
      "variant": "MUTATE",
      "allowed_roles": [
        "deckhand",
        "bosun",
        "eto",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id",
        "quantity"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "receive_part",
      "label": "Receive Part",
      "variant": "MUTATE",
      "allowed_roles": [
        "deckhand",
        "bosun",
        "eto",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id",
        "quantity_received",
        "idempotency_key"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "transfer_part",
      "label": "Transfer Part",
      "variant": "MUTATE",
      "allowed_roles": [
        "bosun",
        "eto",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id",
        "quantity",
        "from_location_id",
        "to_location_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_part_details",
      "label": "View Part Details",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "deckhand",
        "bosun",
        "eto",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "generate_part_labels",
      "label": "Generate Part Labels",
      "variant": "MUTATE",
      "allowed_roles": [
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "part_ids"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "request_label_output",
      "label": "Output Labels",
      "variant": "MUTATE",
      "allowed_roles": [
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "document_id",
        "output"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    }
  ],
  "trust": {
    "path": "hybrid",
    "scopes": [
      "parts"
    ],
    "time_window_days": 90,
    "used_vector": true,
    "explain": "Hybrid search: SQL filters + semantic on 'parts low in stock...'"
  },
  "timing_ms": {
    "orchestration": 1326.2,
    "execution": 309.0,
    "total": 1635.4
  },
  "debug": null,
  "error": null
}
```

**Result:** ✅ PASS

---

## Test: crew_read_action_check_stock

**Request:**
```
POST /v1/actions/execute
{"action":"check_stock_level","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"part_id":"00000000-0000-0000-0000-000000000000"}}
```

**HTTP Status:** 404

**Response Body:**
```json
{
  "status": "error",
  "error_code": "PART_NOT_FOUND",
  "message": "Part not found: 00000000-0000-0000-0000-000000000000"
}
```

**Result:** ✅ PASS

---

## Test: crew_mutate_action_denied

**Request:**
```
POST /v1/actions/execute
{"action":"log_part_usage","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"part_id":"00000000-0000-0000-0000-000000000000","quantity":1,"usage_reason":"maintenance","notes":"test"}}
```

**HTTP Status:** 400

**Response Body:**
```json
{
  "status": "error",
  "error_code": "INSUFFICIENT_STOCK",
  "message": "Not enough stock to deduct requested quantity"
}
```

**Result:** ❌ FAIL (expected 403, got 400)

---

## Test: hod_mutate_action_allowed

**Request:**
```
POST /v1/actions/execute
{"action":"log_part_usage","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"part_id":"00000000-0000-0000-0000-000000000000","quantity":1,"usage_reason":"maintenance","notes":"test"}}
```

**HTTP Status:** 400

**Response Body:**
```json
{
  "status": "error",
  "error_code": "INSUFFICIENT_STOCK",
  "message": "Not enough stock to deduct requested quantity"
}
```

**Result:** ❌ FAIL (expected 404, got 400)

---

## Test: invalid_part_id_error_mapping

**Request:**
```
POST /v1/actions/execute
{"action":"check_stock_level","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"part_id":"invalid-uuid-format"}}
```

**HTTP Status:** 400

**Response Body:**
```json
{
  "status": "error",
  "error_code": "INTERNAL_ERROR",
  "message": "Failed to check stock level: {'code': '22P02', 'details': None, 'hint': None, 'message': 'invalid input syntax for type uuid: \"invalid-uuid-format\"'}"
}
```

**Result:** ✅ PASS

---

## Test: missing_field_error_mapping

**Request:**
```
POST /v1/actions/execute
{"action":"check_stock_level","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{}}
```

**HTTP Status:** 400

**Response Body:**
```json
{
  "status": "error",
  "error_code": "MISSING_REQUIRED_FIELD",
  "message": "Missing required field(s): part_id"
}
```

**Result:** ✅ PASS

---

## Test: parts_routing_verification

**Request:**
```
POST /v2/search
{"query_text":"oil filter"}
```

**HTTP Status:** 200

**Response Body:**
```json
{
  "success": true,
  "request_id": "2825f69c-bdb",
  "results": [],
  "results_by_domain": {
    "work_orders": [],
    "equipment": [],
    "document_chunks": [],
    "graph_nodes": []
  },
  "total_count": 0,
  "context": {
    "domain": "work_orders",
    "domain_confidence": 0.9,
    "intent": "READ",
    "intent_confidence": 0.8,
    "mode": "hybrid",
    "filters": {
      "time_window_days": 90,
      "scopes": [
        "work_orders",
        "equipment",
        "faults",
        "documents",
        "parts"
      ]
    }
  },
  "actions": [
    {
      "action_id": "view_work_order_checklist",
      "label": "View Work Order Checklist",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "work_order_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_work_order_detail",
      "label": "View Work Order Detail",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "work_order_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_my_work_orders",
      "label": "View My Work Orders",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_related_entities",
      "label": "View Related Entities",
      "variant": "READ",
      "allowed_roles": [
        "crew",
        "chief_engineer",
        "chief_officer",
        "captain",
        "manager"
      ],
      "required_fields": [
        "yacht_id",
        "entity_type",
        "entity_id"
      ],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    }
  ],
  "trust": {
    "path": "hybrid",
    "scopes": [
      "work_orders",
      "equipment",
      "faults",
      "documents",
      "parts"
    ],
    "time_window_days": 90,
    "used_vector": true,
    "explain": "Hybrid search: SQL filters + semantic on 'oil filter...'"
  },
  "timing_ms": {
    "orchestration": 794.6,
    "execution": 1126.0,
    "total": 1920.7
  },
  "debug": null,
  "error": null
}
```

**Result:** ✅ PASS

---
