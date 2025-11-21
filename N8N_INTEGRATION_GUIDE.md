# 🔗 n8n Integration Guide - Micro-Action Extraction Service

**Complete guide for integrating the micro-action extraction service with n8n workflows**

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [n8n Node Configuration](#n8n-node-configuration)
3. [Common Workflows](#common-workflows)
4. [Error Handling](#error-handling)
5. [Potential Issues & Solutions](#potential-issues--solutions)
6. [Performance Optimization](#performance-optimization)
7. [Testing & Validation](#testing--validation)

---

## ⚡ Quick Start

### Prerequisites

- ✅ Micro-action service deployed on Render (see `RENDER_DEPLOYMENT_GUIDE.md`)
- ✅ Service URL: `https://celeste-microactions.onrender.com`
- ✅ n8n Cloud account OR self-hosted n8n instance

### 30-Second Setup

1. **Add HTTP Request Node** in n8n
2. **Configure:**
   ```
   Method: POST
   URL: https://celeste-microactions.onrender.com/extract_microactions
   ```
3. **Add Body:**
   ```json
   {
     "query": "{{$json.user_query}}"
   }
   ```
4. **Test** with sample query: "create work order and add to handover"

---

## 🔧 n8n Node Configuration

### Method 1: HTTP Request Node (Recommended)

**Node:** `HTTP Request`

**Configuration:**
```
┌─────────────────────────────────────────────┐
│ HTTP Request Node Settings                  │
├─────────────────────────────────────────────┤
│ Method:                POST                 │
│ URL:                   https://celeste-     │
│                        microactions.        │
│                        onrender.com/        │
│                        extract_microactions │
│                                             │
│ Authentication:        None                 │
│                                             │
│ Send Body:             ✓ Yes                │
│ Body Content Type:     JSON                 │
│                                             │
│ JSON Body:                                  │
│ {                                           │
│   "query": "{{$json.user_query}}",          │
│   "validate_combination": true              │
│ }                                           │
│                                             │
│ Headers:                                    │
│ Content-Type: application/json              │
└─────────────────────────────────────────────┘
```

**Response Mapping:**
```javascript
// Access extracted actions in next node:
{{$json.micro_actions}}          // Array: ["create_work_order", "add_to_handover"]
{{$json.count}}                  // Number: 2
{{$json.latency_ms}}             // Number: 102
{{$json.has_unsupported}}        // Boolean: false
{{$json.validation}}             // Object: {valid: true, warnings: [], ...}
```

### Method 2: Code Node (Advanced)

**Node:** `Code`

```javascript
// For complex logic or local testing
const response = await $http.request({
  method: 'POST',
  url: 'https://celeste-microactions.onrender.com/extract_microactions',
  headers: {
    'Content-Type': 'application/json'
  },
  body: {
    query: $input.item.json.user_query,
    validate_combination: true
  }
});

return {
  json: {
    user_query: $input.item.json.user_query,
    actions: response.micro_actions,
    count: response.count,
    latency: response.latency_ms
  }
};
```

---

## 🔄 Common Workflows

### Workflow 1: Main Entry Point

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Webhook   │────▶│   Extract    │────▶│   Route by       │
│  (receives  │     │  Micro-Actions│    │   Action Type    │
│   query)    │     │               │    │                  │
└─────────────┘     └──────────────┘     └──────────────────┘
                            │                      │
                            │                      ▼
                            │            ┌──────────────────┐
                            │            │ create_work_order│
                            │            │ → Call WO API    │
                            │            └──────────────────┘
                            │                      │
                            │                      ▼
                            │            ┌──────────────────┐
                            └───────────▶│ add_to_handover  │
                                         │ → Call Handover  │
                                         │   API            │
                                         └──────────────────┘
```

**n8n Implementation:**

**Node 1: Webhook Trigger**
```json
{
  "path": "search",
  "method": "POST",
  "responseMode": "lastNode"
}
```

**Node 2: HTTP Request - Extract Actions**
```json
{
  "method": "POST",
  "url": "https://celeste-microactions.onrender.com/extract_microactions",
  "body": {
    "query": "={{$json.query}}"
  }
}
```

**Node 3: Switch Node - Route by Action**
```javascript
// Mode: Rules
// Route based on actions array

// Rule 1: Contains 'create_work_order'
{{$json.micro_actions.includes('create_work_order')}}

// Rule 2: Contains 'add_to_handover'
{{$json.micro_actions.includes('add_to_handover')}}

// Rule 3: Contains 'report_fault'
{{$json.micro_actions.includes('report_fault')}}

// Default: Unsupported
```

### Workflow 2: Multi-Action Handler

```javascript
// Code Node: Process Multiple Actions
const actions = $input.item.json.micro_actions;
const results = [];

for (const action of actions) {
  switch(action) {
    case 'create_work_order':
      // Call work order API
      const woResult = await $http.request({
        method: 'POST',
        url: 'https://api.celeste7.ai/work-orders',
        body: {
          query: $input.item.json.query,
          action: action
        }
      });
      results.push({action, status: 'success', data: woResult});
      break;

    case 'add_to_handover':
      // Call handover API
      const horResult = await $http.request({
        method: 'POST',
        url: 'https://api.celeste7.ai/handover',
        body: {
          query: $input.item.json.query
        }
      });
      results.push({action, status: 'success', data: horResult});
      break;

    default:
      results.push({action, status: 'unsupported'});
  }
}

return {json: {results}};
```

### Workflow 3: Fallback to Claude/OpenAI

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Extract   │────▶│   IF Node    │────▶│  No actions?     │
│  Micro-      │     │  Check if    │    │  → Call Claude   │
│  Actions    │     │  empty       │    │    for fallback  │
└─────────────┘     └──────────────┘     └──────────────────┘
                            │
                            │ Has actions
                            ▼
                    ┌──────────────────┐
                    │  Process Actions │
                    │  normally        │
                    └──────────────────┘
```

**IF Node Configuration:**
```javascript
// Condition: Check if actions array is empty
{{$json.micro_actions.length === 0}}

// True → Route to Claude/OpenAI
// False → Process actions normally
```

---

## 🚨 Error Handling

### Error Scenario 1: Service Unavailable (503)

**Cause:** Cold start delay (Starter tier sleeps after 15min inactivity)

**n8n Detection:**
```javascript
// In Error Catcher Node
{{$json.statusCode === 503}}
```

**Solution:**
```javascript
// Add Wait node + Retry
{
  "wait": 3000,  // Wait 3 seconds
  "retries": 2,  // Retry up to 2 times
  "retryInterval": 2000  // 2 seconds between retries
}
```

**n8n Configuration:**
```
┌─────────────────────────────────────────────┐
│ HTTP Request Node - Error Handling          │
├─────────────────────────────────────────────┤
│ Retry On Fail:         ✓ Enabled            │
│ Max Tries:             3                    │
│ Wait Between Tries:    2000 ms              │
│                                             │
│ Retry On Status Codes: 503, 502, 504       │
└─────────────────────────────────────────────┘
```

### Error Scenario 2: Timeout

**Cause:** AI fallback taking too long (>30s)

**Solution:**
```
┌─────────────────────────────────────────────┐
│ HTTP Request Node - Timeout                 │
├─────────────────────────────────────────────┤
│ Timeout:               10000 ms (10s)       │
│                                             │
│ On Timeout:            Continue workflow    │
│                        with empty actions   │
└─────────────────────────────────────────────┘
```

**Error Handler:**
```javascript
// Code Node: Handle Timeout
if ($input.item.json.error && $input.item.json.error.code === 'ETIMEDOUT') {
  return {
    json: {
      micro_actions: [],
      count: 0,
      latency_ms: 10000,
      error: 'Extraction timeout - falling back to Claude'
    }
  };
}
```

### Error Scenario 3: Invalid Response

**Cause:** Service returned non-JSON or malformed data

**Detection:**
```javascript
// IF Node: Validate Response
{{typeof $json.micro_actions !== 'undefined' && Array.isArray($json.micro_actions)}}

// False → Route to error handler
```

**Solution:**
```javascript
// Code Node: Sanitize Response
try {
  const actions = $input.item.json.micro_actions || [];
  return {
    json: {
      micro_actions: Array.isArray(actions) ? actions : [],
      count: Array.isArray(actions) ? actions.length : 0,
      safe: true
    }
  };
} catch (error) {
  return {
    json: {
      micro_actions: [],
      count: 0,
      error: error.message,
      safe: false
    }
  };
}
```

---

## ⚠️ Potential Issues & Solutions

### Issue 1: CORS Errors (Frontend Integration)

**Symptom:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Cause:** Frontend trying to call service directly (not via n8n)

**Solution:**
```python
# In microaction_service.py, update CORS middleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "https://your-n8n-instance.com"
    ],  # Specific origins only
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

### Issue 2: Rate Limiting

**Symptom:** 429 Too Many Requests

**Cause:** Too many queries from same IP (if rate limiting added)

**Solution:**
```javascript
// n8n: Add exponential backoff
const delay = Math.min(1000 * Math.pow(2, $execution.retryNumber), 30000);
await new Promise(resolve => setTimeout(resolve, delay));
```

### Issue 3: Large Queries

**Symptom:** Query truncated or 413 Payload Too Large

**Cause:** Query exceeds 500 char limit (configured in microaction_config.py)

**Solution:**
```javascript
// n8n: Truncate before sending
const query = $input.item.json.user_query;
const truncated = query.length > 500 ? query.substring(0, 500) : query;

// Send truncated query
{
  "query": truncated
}
```

### Issue 4: Ambiguous Actions

**Symptom:** Wrong action detected or multiple unwanted actions

**Example:**
```
Query: "show work orders"
Got: ["create_work_order", "list_work_orders"]
Want: ["list_work_orders"]
```

**Solution:**
```javascript
// n8n: Filter actions by confidence threshold
// Use /extract_detailed endpoint instead

const response = await $http.request({
  method: 'POST',
  url: 'https://celeste-microactions.onrender.com/extract_detailed',
  body: { query: $input.item.json.user_query }
});

// Filter by confidence
const highConfidenceActions = response.matches
  .filter(m => m.confidence > 0.85)
  .map(m => m.action_name);

return { json: { micro_actions: highConfidenceActions } };
```

### Issue 5: No Actions Detected

**Symptom:** Empty micro_actions array for valid query

**Debug:**
```javascript
// n8n Code Node: Debug extraction
const response = await $http.request({
  method: 'POST',
  url: 'https://celeste-microactions.onrender.com/extract_detailed',
  body: { query: $input.item.json.user_query }
});

// Log detailed information
console.log('Query:', $input.item.json.user_query);
console.log('Matches:', response.matches);
console.log('Total matches:', response.total_matches);
console.log('Unsupported:', response.has_unsupported);

return { json: response };
```

**Solutions:**
1. **Add pattern to microaction_patterns.json**
2. **Use Claude/OpenAI fallback**
3. **Provide autocomplete suggestions to user**

### Issue 6: False Positives

**Symptom:** Actions detected when they shouldn't be

**Example:**
```
Query: "reporter on duty"
Got: ["report_fault"]  # ❌ Wrong!
Want: []
```

**Root Cause:** Pattern too broad

**Solution:**
```json
// Edit microaction_patterns.json
// Change:
"report\\s+fault"  // Too broad, matches "report" in "reporter"

// To:
"report\\s+(a\\s+)?fault"  // Requires "fault" after "report"
```

**n8n Workaround (temporary):**
```javascript
// Code Node: Filter out suspicious matches
const actions = $input.item.json.micro_actions;
const query = $input.item.json.user_query;

const filtered = actions.filter(action => {
  // Remove "report_fault" if query doesn't contain "fault"
  if (action === 'report_fault' && !query.toLowerCase().includes('fault')) {
    return false;
  }
  return true;
});

return { json: { micro_actions: filtered } };
```

---

## 🚀 Performance Optimization

### Optimization 1: Caching

**Problem:** Same query processed multiple times

**Solution:**
```javascript
// n8n: Add Redis/Memory cache
const cache = $input.item.json.cache || {};
const query = $input.item.json.user_query;
const cacheKey = query.toLowerCase().trim();

if (cache[cacheKey]) {
  // Return cached result
  return { json: cache[cacheKey] };
}

// Call extraction service
const response = await $http.request({...});

// Cache result
cache[cacheKey] = response;
cache[cacheKey].cached = true;

return { json: response };
```

### Optimization 2: Parallel Processing

**Problem:** Multiple sequential API calls slow down workflow

**Solution:**
```javascript
// n8n: Process actions in parallel
const actions = $input.item.json.micro_actions;

// Use Promise.all for parallel execution
const results = await Promise.all(
  actions.map(action =>
    $http.request({
      method: 'POST',
      url: `https://api.celeste7.ai/${action}`,
      body: { query: $input.item.json.user_query }
    })
  )
);

return { json: { results } };
```

### Optimization 3: Debouncing User Input

**Problem:** User typing triggers too many requests

**Solution:**
```javascript
// n8n: Add Wait node with debounce
{
  "wait": 500,  // Wait 500ms after last input
  "mode": "debounce"
}
```

---

## 🧪 Testing & Validation

### Test Suite for n8n

Create a test workflow with these queries:

```javascript
const testCases = [
  // Basic tests
  {query: "create work order", expected: ["create_work_order"]},
  {query: "add to handover", expected: ["add_to_handover"]},
  {query: "report fault", expected: ["report_fault"]},

  // Multi-action tests
  {query: "create wo and add to hor", expected: ["create_work_order", "add_to_handover"]},

  // Abbreviations
  {query: "create wo", expected: ["create_work_order"]},

  // Edge cases
  {query: "", expected: []},
  {query: "translate to spanish", expected: []},

  // False positive checks
  {query: "reporter on duty", expected: []},
  {query: "support team", expected: []},
];

// Run tests
for (const test of testCases) {
  const response = await $http.request({
    method: 'POST',
    url: 'https://celeste-microactions.onrender.com/extract_microactions',
    body: { query: test.query }
  });

  const passed = JSON.stringify(response.micro_actions.sort()) ===
                 JSON.stringify(test.expected.sort());

  console.log(`${passed ? '✅' : '❌'} "${test.query}"`);
  if (!passed) {
    console.log(`  Expected: ${test.expected}`);
    console.log(`  Got: ${response.micro_actions}`);
  }
}
```

### Monitor Service Health

**n8n Cron Trigger:**
```
Schedule: */5 * * * *  (every 5 minutes)

HTTP Request:
  GET https://celeste-microactions.onrender.com/health

IF Node:
  {{$json.status !== 'healthy'}}

  True → Send alert to Slack/Email
```

---

## 📊 Logging & Debugging

### Enable Detailed Logging

```javascript
// n8n Code Node: Log all extraction details
const response = await $http.request({
  method: 'POST',
  url: 'https://celeste-microactions.onrender.com/extract_detailed',
  body: {
    query: $input.item.json.user_query,
    include_metadata: true
  }
});

console.log('=== EXTRACTION DEBUG ===');
console.log('Query:', $input.item.json.user_query);
console.log('Actions:', response.micro_actions);
console.log('Matches:', response.matches);
console.log('Confidence scores:', response.matches.map(m => ({
  action: m.action_name,
  conf: m.confidence,
  source: m.source
})));
console.log('Latency:', response.latency_ms + 'ms');

return { json: response };
```

---

## ✅ Integration Checklist

Before going live:

- [ ] Service URL configured in n8n
- [ ] Health check passing
- [ ] Test queries return correct actions
- [ ] Error handling configured (503, timeout, invalid response)
- [ ] Retries configured (3 attempts, exponential backoff)
- [ ] Timeout set (10s max)
- [ ] Multi-action routing implemented
- [ ] Fallback to Claude/OpenAI configured
- [ ] Logging enabled
- [ ] Monitoring/alerts set up
- [ ] Cache implemented (if needed)
- [ ] CORS configured for frontend
- [ ] Test suite passing (>90% accuracy)

---

## 📞 Support & Resources

- **n8n Documentation:** https://docs.n8n.io
- **Service API Docs:** https://celeste-microactions.onrender.com/docs
- **Health Endpoint:** https://celeste-microactions.onrender.com/health
- **Patterns List:** https://celeste-microactions.onrender.com/patterns

---

**🎉 You're ready to integrate micro-action extraction with n8n!**

**Performance target:** <200ms P95 latency, >90% accuracy, 99.9% uptime
