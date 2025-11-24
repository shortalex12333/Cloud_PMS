# 🌐 **web-ux.md — CelesteOS Web UX Specification (Two-Page Model)**

**Version:** 2.0
**Owner:** Product & UX
**Status:** Approved**

---

# # 🧭 **1. Philosophy of the Web UX**

CelesteOS is built around two pages:

---

# **PAGE 1 → Global Search (Primary)**

This is where **crew live 95% of the time**.

# **PAGE 2 → Dashboard (Secondary)**

This is where **Heads of Department manage configuration**, see fleet status, and adjust vessel settings.

---

This dual-layout preserves simplicity while respecting operational reality:

* **Crew don’t navigate. They search.**
* **HODs need oversight and configuration controls.**

Search drives everything; dashboard *never* becomes a “second product.”

---

# # 🔍 **2. Page One — Global Search Interface (Default)**

This is the homepage.
The starting point.
The main control surface.

There is **no menu**, **no modules**, and **no navigation**.

## **2.1 Layout**

### **A. Top: Universal Search Bar**

Center-aligned, always visible.

```
 Search anything… (fault code, system, part, note, document)
```

The moment a user starts typing:

* entity extraction begins
* suggestions stream in
* micro-actions appear
* cards populate in ranked order

No “submit” button.
Search is live and instantaneous.

---

## **2.2 Middle: Dynamic Result Canvas**

The result canvas adjusts automatically:

* document cards
* fault cards
* equipment cards
* work orders
* handover items
* notes
* emails
* predictive insights
* fleet analytics (for authorised users)

All content is in **card form**, not pages.

Cards fade in/out based on query context.

---

## **2.3 Right-Side Context Panel (Optional)**

Appears only when needed:

* equipment details
* fault timelines
* part compatibility
* predictive score
* metadata extracted from documents

Closes automatically when irrelevant.

---

## **2.4 Interaction Model**

Everything is triggered by the user typing a natural-language instruction:

> "Fault E047 main engine"
> "Find MTU coolant drawing"
> "Order racor 2040 filter"
> "Create WO for chiller leak"
> "Add this page to handover"
> "What's likely to fail next?"

Every query yields:

* relevant cards
* micro-actions
* autofill buttons
* recommendations
* predictive summaries

Search *is* the interface.
No manual navigation needed.

---

# # 🧠 **3. Micro-Actions in Search**

Each card includes **contextual micro-actions**:

| Card       | Micro-Actions                              |
| ---------- | ------------------------------------------ |
| Fault      | Create WO / Add to Handover / View History |
| Document   | Open / Add Page to Handover                |
| Equipment  | Predictive / View WOs / View Docs          |
| Part       | Add to WO / Order / See Stock              |
| Predictive | Add to Handover / Inspect Equipment        |
| Work Order | View / Add to Handover                     |
| Note       | Attach Photo / Add to Handover             |

Micro-actions appear **only when relevant**, keeping the UI minimalist.

---

# # 🧩 **4. Page Two — Dashboard (HOD-only)**

This page is optional for most crew.
It is *not* used for day-to-day engineering work.

The dashboard exists for:

* **Heads of Department**
* **Chief Engineers**
* **Technical Managers**
* **Fleet Managers**

To configure, monitor, and oversee.

---

## **4.1 Dashboard Purpose**

This page is used for:

### **A. Configuration**

* equipment hierarchy
* system categories
* work order templates
* inventory thresholds
* part compatibility
* user access
* yacht settings

### **B. Oversight**

* upcoming scheduled maintenance
* compliance tasks
* overdue WOs
* equipment lifecycle status
* predictive risk overview
* inventory shortages
* fleet comparisons (if applicable)

### **C. High-Level Visualisation**

* charts
* trend lines
* fault patterns
* part usage histograms

It is *not* another workflow.
It is a **control room**, not an action surface.

---

## **4.2 Dashboard Layout**

### **Top Navigation (Dashboard Only)**

A minimal secondary nav:

```
 Overview | Equipment | Inventory | Work Orders | Predictive | Settings
```

Only HOD roles see this.
Crew never need it.

---

## **4.3 Dashboard Widgets**

### **A. Predictive Overview**

* high-risk equipment
* trend arrows
* leading indicators

### **B. Equipment Overview**

* all systems
* statuses
* last service
* next due

### **C. Work Order Status**

* overdue
* upcoming
* high-priority

### **D. Inventory Status**

* low stock
* ordering history
* predicted shortages

### **E. Fleet (If enabled)**

* multi-yacht comparisons (anonymised)
* emerging global patterns

### **F. Settings Panel**

* edit equipment
* add/remove users
* define permissions
* customise workflows

---

# # ✔️ **5. Interaction Rules Between Pages**

### **Rule 1 — Action always happens via the search bar**

Even if the HOD sees something on the dashboard:

If they want to:

* update
* fix
* create
* add
* modify

→ They must do it through the global search bar.

Example:

Dashboard shows:

> “HVAC predicted risk: High”

User types:

> “Create WO for HVAC high pressure issue”

This enforces consistency and reduces training need.

---

### **Rule 2 — Dashboard never duplicates search functionality**

No buttons for:

* “new work order”
* “lookup document”
* “find part”
* “diagnose fault”

These remain search-exclusive.

---

### **Rule 3 — Dashboard is for **awareness**, not input**

Think of it like a car dashboard:

* gauges
* indicators
* only critical toggles

But actions (steering, brakes, gears) still happen elsewhere.

Same here:

* dashboard = monitoring
* search bar = doing

---

# # 🚫 **6. What the Dashboard Is NOT**

* Not a PMS
* Not a module nav tree
* Not a place for daily operations
* Not where crew do their job
* Not a data entry system
* Not a place for running flows
* Not where documents are found
* Not where work orders are created

This prevents CelesteOS from devolving into another bloated enterprise system.

---

# # 🎨 **7. Visual Style & UI Tone**

Both pages share:

* minimal dark/light theme
* Apple-style clean typography
* card-based layout
* smooth transitions
* zero-clutter interface
* gentle animations
* intuitive structure

Search feels like **Spotlight**.
Dashboard feels like **Mission Control**.

---

# # 🧩 **8. Navigation Between Pages**

**Primary Landing Page = Search Bar Page**

A single discrete link leads to Dashboard:

```
Dashboard (HOD)
```

Only visible if:

* user has “HOD” or “Manager” role
* user is authenticated

Back to search:

```
← Back to Search
```

This enforces search as the core model.

---

# # 🏁 **9. Summary**

CelesteOS Web UX contains:

### ✔ **Page One — Global Search**

The main interface for:

* finding
* acting
* diagnosing
* creating
* adding
* controlling

### ✔ **Page Two — Dashboard**

The management and oversight hub for:

* system visibility
* predictive awareness
* configuration
* compliance

### ✔ Search bar = action engine

### ✔ Dashboard = monitoring & config

### ✔ Minimalist design

### ✔ Zero menu philosophy

### ✔ Consistency across all roles

This keeps CelesteOS **simple**, **modern**, and **future-proof**.

---
