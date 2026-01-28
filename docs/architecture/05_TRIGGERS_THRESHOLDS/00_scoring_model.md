# 00_SCORING_MODEL.md

**Date:** 2026-01-22
**Purpose:** Tunable confidence thresholds and scoring rules
**Status:** V0 Defaults - Subject to Production Tuning

---

## OVERVIEW

Confidence scoring determines when the router:
- Executes actions automatically (high confidence)
- Asks user to clarify (low confidence)
- Requires explicit confirmation (MUTATE actions)

**These are V0 defaults.** Production tuning will adjust based on:
- User feedback (false positive / false negative rates)
- Action success rates
- Disambiguation frequency

---

## ENTITY EXTRACTION CONFIDENCE THRESHOLDS

### Threshold Table (V0 Defaults)

| Confidence Range | Interpretation | Router Behavior |
|------------------|----------------|----------------|
| **0.9 - 1.0** | Exact match | Proceed to action matching |
| **0.7 - 0.89** | Fuzzy match (typo, alias) | Show disambiguation UI if multiple candidates |
| **0.5 - 0.69** | Multiple candidates | ASK USER to choose from list |
| **< 0.5** | No match / too ambiguous | ASK USER for more info or show "no results" |

### Examples

| Query | Entity Extracted | Confidence | Router Decision |
|-------|------------------|------------|-----------------|
| "Gen 2 alarm" | equipment: uuid-gen2 | 0.95 | ✅ Proceed (exact match) |
| "Generater 2 alarm" | equipment: uuid-gen2 | 0.82 | ⚠️ Fuzzy match, proceed but flag typo |
| "generator alarm" | equipment: [gen1, gen2, gen3] | 0.60 | ❌ Ask user: "Which generator?" |
| "xyz alarm" | equipment: null | 0.20 | ❌ Show "No results for 'xyz'" |

---

## ACTION EXECUTION CONFIDENCE THRESHOLDS

Confidence requirements vary by **risk class**:

### READ Actions (Low Risk)

**Threshold:** >= 0.7

**Rationale:** READ actions don't change state. Lower confidence is acceptable because:
- User can see results and correct if wrong
- No database mutations
- No audit logging required

**Example:**
- Query: "show gen 2 history"
- Entity: equipment (confidence 0.75)
- Action: `view_maintenance_history` (READ)
- **Decision:** Execute immediately, show results

---

### MUTATE Actions - Low Risk (No Signature Required)

**Threshold:** >= 0.8

**Rationale:** These actions change state but are low-impact (add notes, photos, tags). Require higher confidence than READ, but not as high as signature-required.

**Examples:**
- `add_fault_note`
- `add_work_order_photo`
- `tag_for_survey`

**Decision:** Require user confirmation + diff preview, but no signature.

---

### MUTATE Actions - High Risk (Signature Required)

**Threshold:** >= 0.9 OR explicit user confirmation

**Rationale:** These actions create/delete entities or change critical state. Require highest confidence OR force user to explicitly confirm even at lower confidence.

**Examples:**
- `create_work_order_from_fault`
- `mark_work_order_complete`
- `approve_purchase`
- `log_delivery_received`

**Decision:** If confidence < 0.9, show disambiguation UI. After disambiguation, require signature + full diff preview.

---

## CONFIDENCE SCORING ALGORITHM (Proposed)

### Entity Resolution Confidence Factors

Entity confidence = weighted average of:

| Factor | Weight | Examples |
|--------|--------|----------|
| **Exact ID match** | 1.0 | UUID, equipment_id, fault_id |
| **Unique name match** | 0.95 | "Generator 2", "CAT 3512B" |
| **Fuzzy name match** | 0.7 - 0.9 | "Gen 2" → "Generator 2" (typo tolerance) |
| **Alias match** | 0.85 | "Gen 2" → equipment with alias "Gen 2" |
| **Location + name match** | 0.9 | "Engine room chiller" (location + equipment type) |
| **Date/time match** | 0.8 - 0.95 | "yesterday" (0.9), "last week" (0.8) |
| **Multiple candidates** | 0.5 - 0.7 | 2-5 matches with similar scores |
| **No match** | < 0.5 | No database match |

**Current Implementation:** Unknown. Likely keyword matching + database lookup.

**Proposed Enhancement:** Train ML model on historical queries → entity resolutions to improve fuzzy matching.

---

## ACTION MATCHING CONFIDENCE THRESHOLDS

**How confident are we that this action matches the user's intent?**

### Threshold Table (V0 Defaults)

| Confidence Range | Interpretation | Router Behavior |
|------------------|----------------|----------------|
| **0.8 - 1.0** | Strong intent match | Primary suggestion |
| **0.6 - 0.79** | Contextual match | Secondary suggestion (dropdown) |
| **0.4 - 0.59** | Weak match | Show in "Other actions" list |
| **< 0.4** | No match | Do not show |

### Intent Matching Factors

Action matching confidence = weighted average of:

| Factor | Weight | Examples |
|--------|--------|----------|
| **Exact keyword match** | 1.0 | "create work order" → `create_work_order` |
| **Synonym match** | 0.9 | "make a task" → `create_work_order` |
| **Entity-compatible** | 0.7 | User selected fault → suggest `view_fault` |
| **Situational relevance** | 0.6 | User in shipyard → boost `add_worklist_task` |
| **User history** | 0.5 | User frequently does `diagnose_fault` → `create_work_order` → boost WO creation after diagnosis |

**Current Implementation:** Unknown. Likely keyword matching.

**Proposed Enhancement:** Learn from user action sequences to predict next likely action.

---

## CONFLICT RESOLUTION RULES

When multiple actions match with similar confidence:

### Rule 1: Multiple READs

**Scenario:** 2+ READ actions with confidence > 0.7

**Decision:** Show all results in tabs/sections. No conflict.

**Example:**
- Query: "Gen 2"
- Matches: `view_equipment` (0.9), `view_maintenance_history` (0.75), `view_linked_faults` (0.7)
- **Router:** Show equipment card with tabs for history, faults, parts

---

### Rule 2: Multiple MUTATEs

**Scenario:** 2+ MUTATE actions with confidence > 0.7

**Decision:** **NEVER auto-execute.** ASK USER to choose ONE.

**Example:**
- Query: "handle the gen 2 alarm"
- Matches: `create_work_order_from_fault` (0.8), `add_to_handover` (0.75), `acknowledge_fault` (0.7)
- **Router:** Show options list, user must select one

**Why:** These are commitments, not suggestions. Auto-executing the wrong one creates incorrect state.

---

### Rule 3: READ + MUTATE

**Scenario:** 1 READ action (high confidence) + 1+ MUTATE actions (lower confidence)

**Decision:** Execute READ, show MUTATE as dropdown option.

**Example:**
- Query: "show gen 2 alarm"
- Matches: `view_fault` (0.95, READ), `create_work_order_from_fault` (0.65, MUTATE)
- **Router:** Execute `view_fault`, show "Create work order" button in UI

---

## DISAMBIGUATION UI PATTERNS

When confidence triggers disambiguation:

### Pattern 1: Entity Disambiguation (confidence 0.5 - 0.69)

**UI:**
```
Which equipment did you mean?
○ Generator 1 (CAT 3512B) - Engine Room
○ Generator 2 (CAT 3512C) - Engine Room
○ Generator 3 (CAT 3508) - Emergency Power
```

---

### Pattern 2: Action Disambiguation (multiple MUTATEs)

**UI:**
```
What would you like to do with Fault #123?
○ Create work order (fix now)
○ Add to handover (defer to next shift)
○ Acknowledge fault (silence alarm)
[Cancel]
```

---

### Pattern 3: Confidence Too Low (< 0.5)

**UI:**
```
No results found for "xyz generator"

Did you mean:
- Generator 2 (CAT 3512B)
- Emergency Generator (CAT 3508)

Or try refining your search:
- Use equipment name or ID
- Include location (e.g., "engine room")
```

---

## TUNING STRATEGY

### Metrics to Track

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Entity resolution accuracy** | > 90% | User accepts suggested entity without clarification |
| **Action suggestion accuracy** | > 85% | User selects primary suggested action |
| **Disambiguation rate** | < 15% | % of queries requiring disambiguation UI |
| **False positive rate** | < 5% | User executes action then undoes it |
| **False negative rate** | < 10% | User searches again because first result was wrong |

---

### Threshold Adjustment Process

1. **Collect production data** (entity resolutions, action selections, user corrections)
2. **Analyze false positives/negatives** (where did the router fail?)
3. **Adjust thresholds** (e.g., lower MUTATE threshold from 0.8 → 0.75 if too many disambiguation prompts)
4. **A/B test** (split traffic, measure accuracy improvement)
5. **Deploy winning variant**

---

## FUTURE ENHANCEMENTS

### Phase 1: ML-Based Entity Resolution

Replace keyword matching with trained model:
- Input: Query string + user context (role, recent entities, session history)
- Output: Resolved entities + confidence scores

**Benefits:**
- Better typo tolerance
- Context-aware disambiguation (if user just viewed Gen 2, "generator" → Gen 2)
- Learn user-specific aliases

---

### Phase 2: Intent Classification Model

Replace keyword matching with trained model:
- Input: Query string + resolved entities
- Output: Action intent + confidence

**Benefits:**
- Handle synonyms ("fix", "repair", "create work order")
- Multi-step intent ("fix gen 2" → diagnose → create WO)
- Learn from user corrections

---

### Phase 3: Predictive Next Action

After user executes action, predict next likely action:
- Input: Current action + entity + user history
- Output: Ranked list of next actions

**Example:**
- User executes `diagnose_fault`
- Prediction: 85% chance next action is `create_work_order_from_fault`
- UI: Show "Create work order?" as primary next action

---

## OPEN QUESTIONS

### Q1: Should thresholds vary by user role?

**Hypothesis:** Experienced Chief Engineers tolerate lower confidence (they know their equipment). New crew need higher confidence (less context).

**Test:** Track accuracy by role. If Chief Engineers rarely need disambiguation, lower their thresholds.

---

### Q2: Should thresholds vary by time of day?

**Hypothesis:** Night shift users prefer fast decisions (lower thresholds, fewer prompts). Day shift users prefer accuracy (higher thresholds, more disambiguation).

**Test:** Track disambiguation rate by shift. Adjust thresholds accordingly.

---

### Q3: Should thresholds vary by operational context?

**Hypothesis:** Emergency situations tolerate lower confidence (speed matters). Normal operations require higher confidence (accuracy matters).

**Test:** If we implement operational context detection, track accuracy by context.

---

**Status:** V0 defaults defined. Production tuning required after deployment.

**Next:** Create `01_threshold_table.md` with implementation-ready threshold constants.
