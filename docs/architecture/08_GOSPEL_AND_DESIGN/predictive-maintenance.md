# 🔮 **predictive-maintenance.md — CelesteOS Predictive Maintenance Specification**

**Version:** 1.0
**Owner:** AI/Backend Engineering
**Status:** Approved for MVP**

---

# # 🎯 **Purpose**

CelesteOS Predictive Maintenance transforms:

* **raw historical maintenance logs**
* **fault codes**
* **work order history**
* **document embeddings**
* **crew notes**
* **global scraped marine knowledge**
* **fleet-level anonymised statistics**

into actionable predictions about:

* what systems are likely to fail
* what components repeatedly show weakness
* where crew attention is drifting
* what deviations from “normal” behaviour are emerging
* what to add to the handover
* what parts should be pre-ordered
* what patterns exist across multiple yachts

Predictive Maintenance is NOT a gimmicky dashboard.
It is a **knowledge-driven early-warning system**.

---

# # 🧠 **1. High-Level Predictive Architecture**

Predictive signals come from **three data layers**:

---

## **1. Crew-Generated Data (Local Vessel)**

* faults
* work orders
* equipment history
* notes
* photos
* recurring issues
* inventory consumption
* search queries (“crew pain index”)
* handover items

These reflect real-world behaviour of the vessel.

---

## **2. Document Intelligence (Local Vessel)**

Using RAG + embeddings of:

* manuals
* safety bulletins
* troubleshooting guides
* manufacturer instructions
* past handovers

This reveals:

* known fault paths
* known wear patterns
* dependency chains
* technical consequences

---

## **3. Celeste Global Knowledge Layer (Cross-Vessels)**

Scraped + curated knowledge:

* global marine engineering forums
* OEM bulletins
* manufacturer best practices
* common faults across yacht models
* known recurring symptoms for specific engines
* anonymised patterns across CelesteOS vessels
* part compatibility mapping

This gives the model **what should normally happen**.

---

# # 🔍 **2. Predictive Signals (Core Inputs)**

CelesteOS uses a combination of **19 real signals**, grouped by domain.

---

## **2.1 Fault Signals**

* Frequency of fault codes
* Recency of fault patterns
* Fault clustering (same component affected repeatedly)
* Fault code severity
* Fault chains (E047 → E118 → high temp → shutdown)
* Deviations from manufacturer recommended intervals

---

## **2.2 Equipment Behaviour Signals**

* Mean time between failures (MTBF)
* Sudden increase in maintenance activity
* Drop in maintenance activity (crew avoidance)
* Equipment dependency graph (GraphRAG)
* Notes mentioning symptoms (“vibration”, “noise”, “leaking”)

---

## **2.3 Work Order Signals**

* Overdue scheduled tasks
* Repeated corrective tasks
* Work orders that reappear within <90 days
* Work orders referencing same part group
* Tasks marked “partially completed”

---

## **2.4 Part Consumption Signals**

* Inventory depletion faster than expected
* Parts repeatedly replaced (filters, seals, temp sensors)
* Delays in receiving parts (predictive risk goes up)
* Cross-compatibility issues (wrong part used)

---

## **2.5 Crew Behaviour Signals**

Collected indirectly from usage:

* repeated search queries on same equipment
* querying fault codes multiple times
* adding notes frequently
* mobile photos tagged to same location
* “unusual” search patterns (crew pain index)

Crew attention is one of the strongest predictors of problems.

---

## **2.6 Climate & Operational Signals**

From metadata:

* long periods of inactivity
* extreme temperatures
* heavy load weeks
* yard periods

---

## **2.7 Document-Based Signals**

From manuals + scraped knowledge:

* known failure curves
* recommended service intervals
* troubleshooting patterns
* fault cascade behaviour (“if A → B → C”)

Extracted using RAG + GraphRAG.

---

# # 🧬 **3. Predictive Algorithm — V1**

### CelesteOS V1 predictive model is **rule-based + statistical**, paired with GraphRAG.

We are NOT training ML models yet — we don’t have data.
But we can produce *ML-level value* with intelligent heuristics.

---

## **3.1 Multi-Signal Weighted Scoring System**

Each equipment item receives a **risk score**:

```
risk_score = 
  0.35*fault_signal 
+ 0.25*work_order_signal 
+ 0.15*crew_activity_signal 
+ 0.15*part_consumption_signal 
+ 0.10*global_knowledge_signal
```

Scores range **0.00 → 1.00**

Thresholds:

* 0.00 – 0.40 → normal
* 0.40 – 0.60 → monitor
* 0.60 – 0.75 → emerging risk
* 0.75 – 1.00 → high risk / likely upcoming failure

---

## **3.2 Predictive Workflows (Cloud)**

### Step 1 — Pull local vessel signals

* faults
* WOs
* notes
* parts
* queries

### Step 2 — Pull global knowledge relations

* manufacturer known issues
* scraped patterns
* analogous failures across fleet

### Step 3 — Build subgraph

From `graph_nodes` + `graph_edges`

### Step 4 — Explore cross-edges

(via DFS/BFS depth=3)

### Step 5 — Score equipment

### Step 6 — Generate “Why explanation?” summary

Using RAG + chunk references.

### Step 7 — Store in `predictive_state` table

---

# # 🧩 **4. Predictive Maintenance Features (User-Facing)**

Here is where predictive becomes *functional*.

---

## **4.1 Equipment Risk Map**

Every piece of equipment shows:

* risk score
* trending arrow (improving/worsening)
* contributing factors
* last issue
* predicted next issue

---

## **4.2 Fault Code Prediction**

Using global data + local patterns:

* “fault E047 likely to recur soon”
* “coolant system has repeated early-stage drift”

---

## **4.3 Work Order Suggestions**

Automatically recommend:

* create WO
* inspect component
* order parts
* update handover

Triggered by risk score thresholds.

---

## **4.4 Crew Pain Index (Search-Based Predictive)**

If crew repeatedly search for:

* “generator vibration”
* “AC pressure”
* “black water smell”

CelesteOS interprets:

> “Crew attention is rising — something is wrong.”

We generate a pre-emptive insight.

---

## **4.5 Handover AI Assistant**

When generating a handover, CelesteOS:

* recommends predictive items
* summarises risk
* highlights weak systems
* includes suggested tasks

Handover becomes **forward-looking**, not reactive.

---

## **4.6 Fleet-Level Insights (Anonymised)**

Across multiple yachts:

* compare main engine issues
* identify common part failures
* highlight emerging industry patterns
* detect at-risk systems per yacht class

No yacht identity is ever revealed.

---

# # 🧱 **5. Predictive Dashboard (Web App)**

The dashboard shows:

### **5.1 High-Risk Systems**

Cards:

* risk score
* equipment summary
* recommended actions

### **5.2 Fault Pattern Graphs**

* frequency over time
* recurrence
* dependencies

### **5.3 Part Forecasting**

* which parts should be ordered soon
* predicted shortages
* common replacements

### **5.4 Crew Activity Map**

Heatmap of crew searches → early anomaly detection.

### **5.5 Global/Local Delta**

Shows differences between:

* this yacht
* global average
* sister ships

Example:

> “This yacht’s chiller shows 2.1x more pressure faults than global average.”

---

# # ⚙️ **6. Implementation Details**

---

## **6.1 Data Tables Needed**

* `faults`
* `work_order_history`
* `notes`
* `search_queries`
* `parts`
* `stock_levels`
* `documents`
* `document_chunks`
* `graph_nodes`
* `graph_edges`
* `celeste_chunks`
* `predictive_state` (new)

---

## **6.2 Supabase Functions**

* SQL RPC for “get signals”
* RPC for “graph subgraph traversal”
* RPC for “ranking sort + return top N”
* Materialized view for “recent behaviour”

---

## **6.3 Cloud Worker (Render.com Python)**

Runs:

* signal extraction
* scoring
* summary generation via RAG
* writes results back

Runs every:

* 6 hours
* on-demand
* pre-export of handover

---

# # 📡 **7. Notifications & Alerts**

### Alerts delivered via:

* mobile push
* email
* web notifications

Triggered when:

* risk > 0.75
* sudden spike in crew queries
* part depletion + fault signal
* failure cascade detected
* global bulletin detected (via scraper)

---

# # 🧩 **8. MVP vs Future ML Model**

### **MVP (Rule-based + statistical + GraphRAG)**

Already extremely powerful because:

* yachts behave similarly
* lack of data solves itself via global layer
* GraphRAG infers relationships
* manual structures give clarity
* patterns are explicit

### **Future ML (LSTM/Transformer per equipment class)**

Once enough yachts upload:

* learn actual failure curves
* learn abnormal signals
* train models per manufacturer/model

CelesteOS becomes the **global engineering dataset** for yachts.

---

# # 🏁 **9. Summary**

CelesteOS Predictive Maintenance:

* uses **19 signals** from logs, notes, faults, parts, and crew behaviour
* merges with **global scraped knowledge**
* uses **GraphRAG** to detect multi-hop fault patterns
* uses **semantic RAG** to read manuals & technical docs
* produces **actionable insights**, not dashboards
* triggers **automated recommendations**
* improves handovers
* guides engineers before failures happen
* compares yachts anonymously for trends

This system evolves from reactive → proactive → predictive.

---