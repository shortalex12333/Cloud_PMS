# P0 Actions Quickstart

**Last Updated:** 2026-01-09
**Status:** ✅ Server Running & Ready for Testing

---

## 🚀 Quick Start Guide

### 1. Server is Already Running

The FastAPI server is running at **http://localhost:8000**

**Check health:**
```bash
curl http://localhost:8000/v1/actions/health | jq .
```

**Expected response:**
```json
{
  "status": "healthy",
  "handlers_loaded": 4,
  "p0_actions_implemented": 8
}
```

### 2. Set Up Environment Variables

```bash
# Set your credentials
export JWT_TOKEN="your_jwt_token_here"
export YACHT_ID="your_yacht_uuid"
export USER_ID="your_user_uuid"

# Set test entity IDs (get these from database)
export EQUIPMENT_ID="valid_equipment_uuid"
export FAULT_ID="valid_fault_uuid"
export PART_ID="valid_part_uuid"
```

### 3. Run Automated Tests

```bash
cd /tmp/Cloud_PMS
./test_p0_actions.sh
```

### 4. Manual Testing

**Test a READ action (no side effects):**
```bash
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "action": "check_stock_level",
    "context": {
      "yacht_id": "'"$YACHT_ID"'",
      "user_id": "'"$USER_ID"'",
      "role": "engineer"
    },
    "payload": {
      "part_id": "'"$PART_ID"'"
    }
  }' | jq .
```

**Test a MUTATE action with prefill:**
```bash
# Step 1: Prefill form data
curl "http://localhost:8000/v1/actions/create_work_order_from_fault/prefill?fault_id=$FAULT_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .

# Step 2: Preview changes
curl -X POST http://localhost:8000/v1/actions/create_work_order_from_fault/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "context": {"yacht_id": "'"$YACHT_ID"'", "user_id": "'"$USER_ID"'"},
    "payload": {
      "fault_id": "'"$FAULT_ID"'",
      "title": "Test Work Order",
      "priority": "high"
    }
  }' | jq .

# Step 3: Execute with signature
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SIGNATURE=$(echo -n "$USER_ID:create_work_order_from_fault:$TIMESTAMP" | base64)

curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "action": "create_work_order_from_fault",
    "context": {"yacht_id": "'"$YACHT_ID"'", "user_id": "'"$USER_ID"'", "role": "chief_engineer"},
    "payload": {
      "fault_id": "'"$FAULT_ID"'",
      "title": "Test Work Order",
      "priority": "high",
      "description": "Testing P0 action execution",
      "signature": {
        "user_id": "'"$USER_ID"'",
        "action": "create_work_order_from_fault",
        "timestamp": "'"$TIMESTAMP"'",
        "signature": "'"$SIGNATURE"'"
      }
    }
  }' | jq .
```

---

## 📚 Documentation

- **Full Testing Guide:** `P0_ACTIONS_TEST_GUIDE.md`
- **Implementation Status:** `P0_IMPLEMENTATION_STATUS.md`
- **Test Script:** `test_p0_actions.sh`
- **Verification Report:** `IMPLEMENTATION_CHECK_REPORT.md`

---

## 🛠️ Server Management

**Check server status:**
```bash
ps aux | grep uvicorn | grep -v grep
```

**View logs:**
```bash
tail -f /tmp/uvicorn.log
```

**Restart server:**
```bash
# Kill existing server
lsof -ti:8000 | xargs kill -9

# Start new server
cd /tmp/Cloud_PMS/apps/api
nohup python3 -m uvicorn pipeline_service:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
```

---

## 🎯 All 8 P0 Actions Available

1. **show_manual_section** - Display equipment manual (READ)
2. **create_work_order_from_fault** - Create WO from fault (MUTATE, signature required)
3. **add_note_to_work_order** - Add note to WO (MUTATE)
4. **add_part_to_work_order** - Add part to shopping list (MUTATE)
5. **mark_work_order_complete** - Complete WO + deduct inventory (MUTATE, signature required)
6. **check_stock_level** - Check part inventory (READ)
7. **log_part_usage** - Deduct inventory directly (MUTATE)
8. **add_to_handover** - Add shift handover item (MUTATE)

---

## ⚠️ Current Limitation

Network connectivity to Supabase is unavailable in this environment. The API endpoints are ready but cannot connect to the database.

**To test with a different network:**
- Transfer the `/tmp/Cloud_PMS` directory to a machine with internet access
- Ensure `.env` file contains valid Supabase credentials
- Run the test script

---

## ✅ What's Complete

- ✅ All 8 P0 actions implemented
- ✅ Database migrations deployed
- ✅ FastAPI server running
- ✅ Health check passing
- ✅ All handlers initialized
- ✅ Routes registered
- ✅ Testing documentation complete

**Ready for end-to-end testing when network access is available.**

---

**For detailed instructions, see P0_ACTIONS_TEST_GUIDE.md**
