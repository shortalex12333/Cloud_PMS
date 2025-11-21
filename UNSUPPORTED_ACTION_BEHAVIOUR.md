# UNSUPPORTED_ACTION_BEHAVIOUR.md

**Version:** 1.0
**Purpose:** Define graceful handling of unsupported or invalid user requests
**Philosophy:** Never say "I don't know" — always offer alternatives and guide users

---

## 🎯 Core Principles

### **1. Never Fail Silently**
- Always acknowledge the user's request
- Explain clearly what we can't do
- Offer related alternatives

### **2. Always Be Helpful**
- Suggest similar supported actions
- Guide users to what they probably meant
- Learn from unsupported requests (log as feature requests)

### **3. Maintain Trust**
- Be honest about limitations
- Don't overpromise future features
- Don't make users feel dumb

### **4. Continuous Improvement**
- Log all unsupported requests
- Review weekly for patterns
- Prioritize common requests for development

---

## 📋 Categories of Unsupported Requests

### **Category 1: Supported Action, Wrong Phrasing**

**Example:**
- User: "Can you email me the handover?"
- System knows: "export handover" exists
- Issue: User phrased it differently

**Response Pattern:**
```
✅ I can help with that!

It sounds like you want to export the handover.

[Button: Export Handover to PDF]
[Button: Send to Email (coming soon)]

Would you like me to export it now?
```

**Implementation:**
- Use fuzzy matching to find similar actions
- Levenshtein distance <3 = suggest it
- Show buttons for similar actions

---

### **Category 2: Supported Action, Missing Context**

**Example:**
- User: "Create a work order"
- System knows: Needs equipment ID or description
- Issue: Insufficient information

**Response Pattern:**
```
✅ I can create a work order for you.

I need a bit more info:
• Which equipment is this for?
• What's the issue or task?

Try: "Create work order for generator maintenance"
```

**Implementation:**
- Detect missing required params
- Prompt for specific information
- Give example queries

---

### **Category 3: Partially Supported (Needs Workaround)**

**Example:**
- User: "Export handover to Excel"
- System supports: PDF export only
- Issue: Wrong format requested

**Response Pattern:**
```
⚠️ I can export handovers to PDF, but not Excel yet.

Here's what I can do:
• Export to PDF (you can convert to Excel manually)
• Export to email

[Button: Export to PDF]

💡 Want Excel export? I'll log this as a feature request.
```

**Implementation:**
- Offer closest alternative
- Explain manual workaround if applicable
- Log as feature request automatically

---

### **Category 4: Genuinely Unsupported (Future Feature)**

**Example:**
- User: "Translate handover to Spanish"
- System: No translation feature exists
- Issue: Legitimate request, not yet built

**Response Pattern:**
```
❌ I can't translate documents yet.

What I can do:
• Export handover to PDF (you can use Google Translate)
• Show handover in English

This is a great idea! I've logged it as a feature request.

Want me to export the handover for now?
```

**Implementation:**
- Clear "not available yet"
- Suggest manual alternatives
- Auto-log as feature request
- Show "export" or related fallback

---

### **Category 5: Out of Scope (Will Never Support)**

**Example:**
- User: "Order pizza for the crew"
- System: Not engineering-related
- Issue: Completely out of scope

**Response Pattern:**
```
😊 That's not something I can help with!

I'm built for yacht engineering tasks like:
• Managing equipment and faults
• Creating work orders
• Searching manuals
• Tracking inventory

Try asking me: "Show overdue maintenance tasks"
```

**Implementation:**
- Polite but firm
- Redirect to valid use cases
- Give helpful examples

---

### **Category 6: Ambiguous Request**

**Example:**
- User: "Fix the generator"
- System: Unclear what "fix" means (create WO? diagnose? show history?)
- Issue: Multiple interpretations possible

**Response Pattern:**
```
🤔 I can help with the generator. What would you like to do?

• Create a work order for generator maintenance
• Diagnose a generator fault
• Show generator service history
• View generator manual

Or tell me more: "Generator 2 is overheating"
```

**Implementation:**
- List top 3-5 likely intents
- Prompt for clarification
- Show buttons for each option

---

### **Category 7: Invalid Input (Malformed)**

**Example:**
- User: "asdfjkl;qwer"
- System: Gibberish or typo
- Issue: Can't extract intent at all

**Response Pattern:**
```
❓ I didn't quite understand that.

I can help you with:
• Searching manuals and documents
• Managing work orders and maintenance
• Diagnosing faults and issues
• Tracking inventory and parts

Try: "Show me MTU manual" or "Create work order"
```

**Implementation:**
- Detect very low confidence (<0.3)
- Show help menu
- Log for analysis (might be new domain term)

---

## 🔧 Implementation Strategy

### **Detection Flow:**

```
User Query
    ↓
1. Intent Detection (Claude/GPT)
    ↓
    ├─ Confidence >0.7 → Execute action
    ├─ Confidence 0.4-0.7 → Ask for clarification
    ├─ Confidence <0.4 → Check fuzzy match
    │       ↓
    │   Fuzzy Match (Levenshtein)
    │       ↓
    │       ├─ Distance <3 → Suggest similar action
    │       └─ Distance ≥3 → Unsupported action flow
    │
    └─ No intent detected → Invalid input response
```

### **LLM Prompt for Intent Detection:**

```
You are an intent classifier for CelesteOS, a yacht engineering system.

User query: "{query}"

Determine:
1. primary_intent: The main action (or null if unsupported)
2. confidence: Float 0-1
3. missing_params: Array of required params not provided
4. suggested_actions: Array of 3 alternative actions if unsupported

Respond with JSON only.

Example:
{
  "primary_intent": "create_work_order",
  "confidence": 0.65,
  "missing_params": ["equipment_id"],
  "suggested_actions": []
}

Supported actions: [create_work_order, add_to_handover, export_handover, ...]
```

### **Fuzzy Matching Logic:**

```javascript
// In n8n Code node
const userIntent = extractedIntent; // e.g., "export hand over"
const supportedActions = [
  "export_handover",
  "add_to_handover",
  "create_work_order",
  // ... all 37 actions
];

function levenshteinDistance(a, b) {
  // Standard algorithm implementation
  // ...
}

const similarities = supportedActions.map(action => ({
  action,
  distance: levenshteinDistance(
    userIntent.toLowerCase().replace(/\s+/g, '_'),
    action
  )
}));

const closest = similarities.sort((a, b) => a.distance - b.distance)[0];

if (closest.distance <= 3) {
  // Suggest this action
  return {
    suggested_action: closest.action,
    message: `Did you mean "${formatActionName(closest.action)}"?`
  };
} else {
  // Truly unsupported
  return {
    suggested_action: null,
    message: "I can't do that yet, but here's what I can do..."
  };
}
```

---

## 📊 Standard Response Templates

### **Template 1: Supported with Typo**

```json
{
  "supported": true,
  "type": "typo_correction",
  "message": "I think you meant: \"{corrected_action}\"",
  "suggested_actions": [
    {
      "action": "export_handover",
      "label": "Export Handover to PDF",
      "confidence": 0.9
    }
  ],
  "user_query": "export hand over"
}
```

**Frontend Rendering:**
```
✅ I think you meant: "Export Handover"

[Button: Export Handover to PDF]
```

---

### **Template 2: Missing Context**

```json
{
  "supported": true,
  "type": "missing_params",
  "message": "I can {action}, but I need more info.",
  "missing_params": ["equipment_id", "description"],
  "prompt": "Try: 'Create work order for generator maintenance'",
  "user_query": "create work order"
}
```

**Frontend Rendering:**
```
✅ I can create a work order, but I need:
• Which equipment?
• What's the issue?

Try: "Create work order for generator maintenance"
```

---

### **Template 3: Unsupported Feature**

```json
{
  "supported": false,
  "type": "feature_request",
  "message": "I can't {action} yet.",
  "alternatives": [
    {
      "action": "export_handover",
      "label": "Export to PDF (you can convert manually)",
      "reason": "Closest alternative"
    },
    {
      "action": "view_handover",
      "label": "View handover online",
      "reason": "Related action"
    }
  ],
  "feature_request_logged": true,
  "user_query": "export to excel"
}
```

**Frontend Rendering:**
```
❌ I can't export to Excel yet.

Alternatives:
• Export to PDF (you can convert manually)
• View handover online

💡 Feature request logged. We'll consider adding this!
```

---

### **Template 4: Ambiguous Request**

```json
{
  "supported": "ambiguous",
  "type": "clarification_needed",
  "message": "I can help with {entity}, but what would you like to do?",
  "options": [
    {
      "action": "create_work_order",
      "label": "Create work order for generator",
      "confidence": 0.7
    },
    {
      "action": "diagnose_fault",
      "label": "Diagnose generator fault",
      "confidence": 0.6
    },
    {
      "action": "view_equipment",
      "label": "View generator details",
      "confidence": 0.5
    }
  ],
  "user_query": "fix the generator"
}
```

**Frontend Rendering:**
```
🤔 I can help with the generator. What would you like to do?

[Button: Create work order]
[Button: Diagnose fault]
[Button: View details]

Or tell me more: "Generator 2 is overheating"
```

---

### **Template 5: Invalid/Gibberish**

```json
{
  "supported": false,
  "type": "invalid_input",
  "message": "I didn't understand that.",
  "help": [
    "Search manuals and documents",
    "Manage work orders",
    "Diagnose faults",
    "Track inventory"
  ],
  "examples": [
    "Show me MTU manual",
    "Create work order for stabilizer",
    "What's fault E047?"
  ],
  "user_query": "asdfjkl"
}
```

**Frontend Rendering:**
```
❓ I didn't understand that.

I can help with:
• Searching manuals and documents
• Managing work orders
• Diagnosing faults

Try: "Show me MTU manual"
```

---

## 📝 Feature Request Logging

### **Database Table:**

```sql
CREATE TABLE feature_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  yacht_id UUID REFERENCES yachts(id),
  user_id UUID REFERENCES users(id),
  query TEXT NOT NULL,
  extracted_intent TEXT,
  suggested_actions JSONB,
  category TEXT,  -- 'unsupported_action', 'wrong_format', 'new_feature'
  frequency INT DEFAULT 1,
  first_requested_at TIMESTAMPTZ DEFAULT NOW(),
  last_requested_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT DEFAULT 'pending',  -- 'pending', 'reviewing', 'planned', 'wont_fix'
  notes TEXT
);

CREATE INDEX idx_feature_requests_status ON feature_requests(status, frequency DESC);
CREATE INDEX idx_feature_requests_yacht ON feature_requests(yacht_id);
```

### **Logging Logic:**

```javascript
// In n8n workflow
async function logFeatureRequest(query, yacht_id, user_id, extracted_intent) {
  // Check if this request already exists
  const existing = await db.query(
    `SELECT id, frequency FROM feature_requests
     WHERE query ILIKE $1 AND yacht_id = $2`,
    [query, yacht_id]
  );

  if (existing.rows.length > 0) {
    // Increment frequency
    await db.query(
      `UPDATE feature_requests
       SET frequency = frequency + 1,
           last_requested_at = NOW()
       WHERE id = $1`,
      [existing.rows[0].id]
    );
  } else {
    // Create new request
    await db.query(
      `INSERT INTO feature_requests
       (yacht_id, user_id, query, extracted_intent, category)
       VALUES ($1, $2, $3, $4, 'unsupported_action')`,
      [yacht_id, user_id, query, extracted_intent]
    );
  }
}
```

### **Weekly Review Query:**

```sql
-- Top 20 most requested features
SELECT
  query,
  COUNT(DISTINCT yacht_id) as yacht_count,
  SUM(frequency) as total_requests,
  MIN(first_requested_at) as first_seen,
  MAX(last_requested_at) as last_seen
FROM feature_requests
WHERE status = 'pending'
GROUP BY query
ORDER BY total_requests DESC
LIMIT 20;
```

---

## 🎨 Frontend UX Patterns

### **Pattern 1: Inline Suggestion**

```tsx
// When similar action found
<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <p className="text-sm text-blue-900">
    ✅ I think you meant: <strong>"Export Handover"</strong>
  </p>
  <button className="mt-2 btn-primary">
    Export Handover to PDF
  </button>
</div>
```

### **Pattern 2: Multiple Options**

```tsx
// When ambiguous
<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
  <p className="text-sm text-yellow-900 mb-3">
    🤔 I can help with the generator. What would you like to do?
  </p>
  <div className="flex flex-col gap-2">
    <button className="btn-secondary">Create work order</button>
    <button className="btn-secondary">Diagnose fault</button>
    <button className="btn-secondary">View details</button>
  </div>
  <p className="text-xs text-yellow-700 mt-3">
    Or tell me more: "Generator 2 is overheating"
  </p>
</div>
```

### **Pattern 3: Unsupported Feature**

```tsx
// When feature doesn't exist
<div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
  <p className="text-sm text-gray-900 mb-2">
    ❌ I can't export to Excel yet.
  </p>
  <p className="text-xs text-gray-600 mb-3">
    Alternatives:
  </p>
  <div className="flex flex-col gap-2">
    <button className="btn-secondary text-sm">
      Export to PDF (you can convert manually)
    </button>
    <button className="btn-secondary text-sm">
      View handover online
    </button>
  </div>
  <p className="text-xs text-gray-500 mt-3">
    💡 Feature request logged. We'll consider adding this!
  </p>
</div>
```

### **Pattern 4: Complete Fallback**

```tsx
// When no intent detected
<div className="bg-white border border-gray-300 rounded-lg p-4">
  <p className="text-sm text-gray-900 mb-3">
    ❓ I didn't understand that.
  </p>
  <p className="text-xs text-gray-600 mb-2">
    I can help you with:
  </p>
  <ul className="text-xs text-gray-600 list-disc list-inside mb-3">
    <li>Searching manuals and documents</li>
    <li>Managing work orders</li>
    <li>Diagnosing faults</li>
    <li>Tracking inventory</li>
  </ul>
  <p className="text-xs text-blue-600">
    Try: "Show me MTU manual" or "Create work order"
  </p>
</div>
```

---

## 🧪 Testing Unsupported Requests

### **Test Cases:**

| User Input | Expected Category | Expected Response |
|------------|-------------------|-------------------|
| "export hand over" | Typo correction | Suggest "export_handover" |
| "create wo" | Abbreviation | Suggest "create_work_order" |
| "export to excel" | Unsupported format | Offer PDF, log feature request |
| "translate to spanish" | Unsupported feature | Explain not available, log request |
| "order pizza" | Out of scope | Polite redirect to valid use cases |
| "fix generator" | Ambiguous | Show options (create WO, diagnose, view) |
| "asdfjkl" | Invalid input | Show help menu with examples |
| "create work order" | Missing context | Prompt for equipment + description |

### **Test Workflow:**

```bash
# Test each category
curl -X POST https://api.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "export hand over",
    "yacht_signature": "test-yacht-123"
  }'

# Expected response
{
  "supported": true,
  "type": "typo_correction",
  "message": "I think you meant: \"Export Handover\"",
  "suggested_actions": [...]
}
```

---

## 📊 Metrics to Track

### **Key Metrics:**

| Metric | Target | Why |
|--------|--------|-----|
| **Unsupported request rate** | <10% | Measure coverage |
| **Clarification request rate** | <20% | Measure clarity |
| **Successful suggestion rate** | >70% | Measure fuzzy matching quality |
| **Feature request frequency** | N/A | Prioritization signal |

### **Dashboard Query:**

```sql
-- Unsupported request breakdown
SELECT
  CASE
    WHEN confidence > 0.7 THEN 'supported'
    WHEN confidence > 0.4 THEN 'clarification_needed'
    WHEN levenshtein_distance <= 3 THEN 'typo_suggestion'
    ELSE 'unsupported'
  END as category,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM search_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY category;
```

---

## ✅ Implementation Checklist

**MVP-1:**
- [ ] LLM intent detection with confidence scores
- [ ] Fuzzy matching for typos (Levenshtein)
- [ ] Feature request logging (database table)
- [ ] Standard response templates (5 categories)
- [ ] Frontend UX components for each pattern
- [ ] Help menu with examples
- [ ] Logging for all unsupported requests

**MVP-2:**
- [ ] ML-based intent classification (faster, cheaper)
- [ ] Context-aware suggestions (based on user history)
- [ ] Auto-generate help based on user's yacht config
- [ ] Proactive suggestions ("Did you know you can...")
- [ ] Feature request voting system
- [ ] Admin dashboard for reviewing feature requests

---

## 🎯 Success Criteria

**Good unsupported action handling means:**

1. ✅ Users never hit a dead end
2. ✅ Users always know why something didn't work
3. ✅ Users are guided to valid alternatives
4. ✅ System learns from unsupported requests
5. ✅ Feature requests are prioritized by frequency
6. ✅ Users feel heard (requests are logged)
7. ✅ Typos and abbreviations are handled gracefully

**Bad unsupported action handling:**
- ❌ "Error: Invalid request"
- ❌ "I don't know what you mean"
- ❌ Silent failure (no response)
- ❌ Generic error message with no guidance
- ❌ No logging of unsupported requests

---

**END OF UNSUPPORTED ACTION BEHAVIOUR**
