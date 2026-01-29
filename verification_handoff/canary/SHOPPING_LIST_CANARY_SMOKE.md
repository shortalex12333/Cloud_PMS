# Shopping List Lens v1 - Canary Smoke Test Results

**Date**: 2026-01-29T03:26:42.397355+00:00
**API Base**: https://celeste-pipeline-v1.onrender.com
**Yacht ID**: 85fe1119-b04c-41ac-80f1-829d23322598

## Test Summary

- Total: 8
- Passed: 0
- Failed: 8
- 5xx Errors: 0

## Test Results

- ❌ FAIL **Health endpoint**: Expected 200 + healthy, got 404: {'raw': 'Not Found\n'}
- ❌ FAIL **CREW create item**: Expected 200, got 404: {'raw': 'Not Found\n'}
- ❌ FAIL **CREW approve denied**: Skipped (no item created)
- ❌ FAIL **CREW reject denied**: Skipped (no item created)
- ❌ FAIL **CREW promote denied**: Skipped (no item created)
- ❌ FAIL **HOD approve item**: Skipped (no item created)
- ❌ FAIL **HOD reject item**: Skipped (no item created)
- ❌ FAIL **ENGINEER promote part**: Skipped (no candidate created)

## HTTP Transcripts

```

================================================================================
GET /health
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

(no body)

HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "raw": "Not Found\n"
}
================================================================================

```

```

================================================================================
POST /v1/actions/execute
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "action": "create_shopping_list_item",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_name": "Smoke Test Item 3f818af3",
    "quantity": 5,
    "source_type": "manual",
    "is_candidate_part": false,
    "urgency": "routine"
  }
}

HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "raw": "Not Found\n"
}
================================================================================

```

```

================================================================================
POST /v1/actions/execute
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "action": "create_shopping_list_item",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_name": "Smoke Test Item 2 5f855ed2",
    "quantity": 3,
    "source_type": "manual",
    "is_candidate_part": false
  }
}

HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "raw": "Not Found\n"
}
================================================================================

```

```

================================================================================
POST /v1/actions/execute
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "action": "create_shopping_list_item",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "item_name": "Candidate Part 3349f574",
    "quantity": 2,
    "source_type": "manual",
    "is_candidate_part": true,
    "manufacturer": "Test Mfg",
    "model_number": "TEST-123"
  }
}

HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "raw": "Not Found\n"
}
================================================================================

```

