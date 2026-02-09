# E2E Testing Evidence - Sun  8 Feb 2026 16:50:44 EST

## Test Environment
- API URL: https://pipeline-core.int.celeste7.ai
- Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
- Date: Sun  8 Feb 2026 16:50:44 EST

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
  "request_id": "cf878f77-d83",
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
    "orchestration": 2094.6,
    "execution": 414.8,
    "total": 3285.3
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
  "request_id": "79fb2938-59a",
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
    "orchestration": 1015.1,
    "execution": 309.3,
    "total": 1324.5
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
{"action_id":"check_stock_level","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","part_id":"00000000-0000-0000-0000-000000000000"}
```

**HTTP Status:** 422

**Response Body:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "action"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "00000000-0000-0000-0000-000000000000"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "context"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "00000000-0000-0000-0000-000000000000"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "payload"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "00000000-0000-0000-0000-000000000000"
      }
    }
  ]
}
```

**Result:** ❌ FAIL (expected 404, got 422)

---

## Test: crew_mutate_action_denied

**Request:**
```
POST /v1/actions/execute
{"action_id":"log_part_usage","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","part_id":"test","quantity_used":1,"work_order_id":"test","notes":"test"}
```

**HTTP Status:** 422

**Response Body:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "action"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "log_part_usage",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "test",
        "quantity_used": 1,
        "work_order_id": "test",
        "notes": "test"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "context"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "log_part_usage",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "test",
        "quantity_used": 1,
        "work_order_id": "test",
        "notes": "test"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "payload"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "log_part_usage",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "test",
        "quantity_used": 1,
        "work_order_id": "test",
        "notes": "test"
      }
    }
  ]
}
```

**Result:** ❌ FAIL (expected 403, got 422)

---

## Test: hod_mutate_action_allowed

**Request:**
```
POST /v1/actions/execute
{"action_id":"log_part_usage","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","part_id":"test","quantity_used":1,"work_order_id":"test","notes":"test"}
```

**HTTP Status:** 422

**Response Body:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "action"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "log_part_usage",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "test",
        "quantity_used": 1,
        "work_order_id": "test",
        "notes": "test"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "context"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "log_part_usage",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "test",
        "quantity_used": 1,
        "work_order_id": "test",
        "notes": "test"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "payload"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "log_part_usage",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "test",
        "quantity_used": 1,
        "work_order_id": "test",
        "notes": "test"
      }
    }
  ]
}
```

**Result:** ❌ FAIL (expected 404, got 422)

---

## Test: invalid_part_id_error_mapping

**Request:**
```
POST /v1/actions/execute
{"action_id":"check_stock_level","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","part_id":"invalid-uuid-format"}
```

**HTTP Status:** 422

**Response Body:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "action"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "invalid-uuid-format"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "context"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "invalid-uuid-format"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "payload"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "part_id": "invalid-uuid-format"
      }
    }
  ]
}
```

**Result:** ❌ FAIL (expected 400, got 422)

---

## Test: missing_field_error_mapping

**Request:**
```
POST /v1/actions/execute
{"action_id":"check_stock_level","yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"}
```

**HTTP Status:** 422

**Response Body:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "action"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "context"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
      }
    },
    {
      "type": "missing",
      "loc": [
        "body",
        "payload"
      ],
      "msg": "Field required",
      "input": {
        "action_id": "check_stock_level",
        "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
      }
    }
  ]
}
```

**Result:** ❌ FAIL (expected 400, got 422)

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
  "request_id": "b985ddf4-c42",
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
    "orchestration": 1020.0,
    "execution": 1558.8,
    "total": 2578.9
  },
  "debug": null,
  "error": null
}
```

**Result:** ❌ FAIL (validation failed: )

---
