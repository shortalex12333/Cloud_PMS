# 🔍 CelesteOS Viewing Patterns - The READ Dimension

**Question:** "Show me all parts in this box" - what viewing/filtering patterns do users need?

**Answer:** We've defined ACTIONS (what users DO), but not VIEWS (how users SEE data)

---

## The Missing Dimension: Data Retrieval Patterns

### What We Currently Have (57-67 Actions)
- ✅ Actions: create_work_order, mark_complete, add_note, edit_invoice_amount
- ✅ Simple views: view_equipment_details, view_part_stock, view_fault_history

### What We're Missing
- ❌ **Filtered views** - "show me all parts in Box 5"
- ❌ **Grouped views** - "show me WOs grouped by equipment"
- ❌ **Time-based views** - "show me this week's faults"
- ❌ **Comparison views** - "this month vs last month"
- ❌ **Hierarchical views** - "equipment → subsystems → components"
- ❌ **Status-based views** - "show me all low stock items"
- ❌ **Person-based views** - "show me MY tasks"
- ❌ **Location-based views** - "all equipment in engine room"
- ❌ **Trending views** - "fault frequency over time"

---

## Competitor Viewing Capabilities (What We Haven't Captured)

### 1. LOCATION-BASED VIEWS

**User Queries:**
- "Show me all parts in Deck 2 Locker 5"
- "What's in Box 3 on the shelf?"
- "All equipment in engine room"
- "Parts stored on starboard side"

**Traditional PMS Features:**
- Location filters in inventory
- GA drawing with clickable zones
- Storage location drill-down
- Room/deck/zone navigation

**Current CelesteOS Coverage:**
- ❌ No location-based filtering
- ✅ Individual part shows location (view_part_location)
- ❌ Cannot query "all items in location X"

**What We Need:**
```
VIEW PATTERN: filter_by_location
  - Applies to: parts, equipment, work_orders
  - Examples:
    - "all parts in Deck 2, Locker 5, Shelf B"
    - "all equipment in engine room"
    - "all WOs for machinery space"
```

---

### 2. STATUS/CONDITION-BASED VIEWS

**User Queries:**
- "Show me all overdue tasks"
- "What parts are low stock?"
- "All open faults"
- "Pending approvals"
- "Completed WOs this week"

**Traditional PMS Features:**
- Status filters (open, pending, completed, overdue)
- Condition filters (low stock, critical, normal)
- Priority filters (urgent, high, medium, low)
- Compliance filters (compliant, violation, warning)

**Current CelesteOS Coverage:**
- ⚠️ Partial - "show me overdue tasks" returns filtered list
- ❌ No explicit status filter views
- ❌ No low-stock alert view

**What We Need:**
```
VIEW PATTERN: filter_by_status
  - work_orders: open, in_progress, pending_approval, completed, overdue
  - parts: in_stock, low_stock, out_of_stock, on_order
  - faults: open, resolved, recurring
  - purchases: draft, submitted, approved, in_transit, received

VIEW PATTERN: filter_by_condition
  - parts: critical_low, below_min, above_max
  - equipment: operational, degraded, failed, under_maintenance
  - compliance: compliant, warning, violation
```

---

### 3. TIME-BASED VIEWS

**User Queries:**
- "Show me work orders due today"
- "What happened this week?"
- "All faults from last month"
- "Parts ordered in Q4"
- "Maintenance history for past 6 months"

**Traditional PMS Features:**
- Date range filters (today, this week, this month, custom range)
- Calendar views (monthly PMS calendar, Gantt chart)
- Timeline views (maintenance history on timeline)
- Upcoming/overdue views (next 7 days, overdue by X days)

**Current CelesteOS Coverage:**
- ⚠️ Partial - "what's due today" returns filtered WOs
- ❌ No explicit date range filtering UI
- ❌ No calendar visualization

**What We Need:**
```
VIEW PATTERN: filter_by_time
  - Presets: today, this week, this month, last 30 days, last 90 days, this year
  - Custom: date range picker (from/to)
  - Relative: "next 7 days", "overdue by >5 days"

VIEW PATTERN: calendar_view
  - PMS calendar (monthly grid with WOs on due dates)
  - Timeline view (Gantt-style for shipyard work)
  - History timeline (equipment maintenance over time)
```

---

### 4. EQUIPMENT/ENTITY-BASED VIEWS

**User Queries:**
- "Show me all work orders for Generator 1"
- "All faults on CAT 3512"
- "Parts used on stabiliser B"
- "History of watermaker"

**Traditional PMS Features:**
- Equipment filter/selector
- Related items view (all WOs/faults/parts for equipment)
- Equipment hierarchy (system → subsystem → component)

**Current CelesteOS Coverage:**
- ✅ Good - "show me CAT 3512" returns equipment card with linked WOs/faults
- ✅ view_equipment_history, view_linked_faults
- ❌ No hierarchical equipment tree view

**What We Need:**
```
VIEW PATTERN: filter_by_equipment
  - Show all WOs for equipment X
  - Show all faults for equipment X
  - Show all parts compatible with equipment X

VIEW PATTERN: equipment_hierarchy
  - Tree view: Main Engine → Cooling System → Coolant Pump → Impeller
  - Click each level → drill down
  - See WOs/faults at each hierarchy level
```

---

### 5. PERSON/ROLE-BASED VIEWS

**User Queries:**
- "Show me MY tasks"
- "What's assigned to Alex?"
- "All WOs by Chief Engineer"
- "Hours of rest for entire crew"

**Traditional PMS Features:**
- My Tasks filter
- Assigned to filter (crew member selector)
- Created by filter
- Role-based dashboards (engineer view, captain view, management view)

**Current CelesteOS Coverage:**
- ❌ No "my tasks" filter
- ❌ No "assigned to me" view
- ❌ No crew member filter

**What We Need:**
```
VIEW PATTERN: filter_by_person
  - My tasks (assigned to current user)
  - Assigned to [crew member]
  - Created by [crew member]
  - Crew member selector for filtering

VIEW PATTERN: role_based_dashboard
  - Engineer view: My WOs, equipment I manage, recent faults
  - Captain view: Compliance status, overdue tasks, fleet overview
  - Management view: Fleet summary, budget, risk indicators
```

---

### 6. CATEGORY/TYPE-BASED VIEWS

**User Queries:**
- "Show me all HVAC parts"
- "All electrical faults"
- "Preventive maintenance tasks"
- "Safety equipment certificates"

**Traditional PMS Features:**
- Category filters (equipment: HVAC, electrical, plumbing, deck, etc.)
- Part categories (filters, seals, oils, consumables, etc.)
- WO types (preventive, corrective, unplanned, project)
- Document categories (manuals, SOPs, bulletins, certificates)

**Current CelesteOS Coverage:**
- ❌ No category-based filtering
- ❌ Categories likely exist in data but not exposed as views

**What We Need:**
```
VIEW PATTERN: filter_by_category
  - Equipment categories: HVAC, electrical, plumbing, propulsion, hotel, AVIT, deck, galley
  - Part categories: filters, seals, oils, lubricants, consumables, electronics, tools
  - WO categories: preventive, corrective, breakdown, project, upgrade
  - Document categories: manuals, SOPs, bulletins, certificates, drawings
```

---

### 7. QUANTITY/MEASUREMENT-BASED VIEWS

**User Queries:**
- "What is quantity of part X?" (your example!)
- "How many filters do we have?"
- "What's the stock level of oil?"
- "Parts with quantity < 3"
- "Equipment running > 5000 hours"

**Traditional PMS Features:**
- Quantity displays (stock levels)
- Measurement filters (hours > X, temperature > Y)
- Threshold alerts (stock < min, hours > service interval)
- Range filters (price between $X and $Y)

**Current CelesteOS Coverage:**
- ✅ view_part_stock shows quantity
- ❌ No quantity-based filtering (e.g., "all parts with qty < 3")
- ❌ No measurement-based filters

**What We Need:**
```
VIEW PATTERN: filter_by_quantity
  - Stock level filters: qty < X, qty = 0, qty > max
  - Running hours filters: hours > service_interval
  - Measurement filters: temp > threshold, pressure < min

VIEW PATTERN: threshold_alerts
  - Low stock items (qty <= min_level)
  - Service due items (hours >= service_interval)
  - Expired items (cert_expiry < today)
```

---

### 8. GROUPED/AGGREGATED VIEWS

**User Queries:**
- "Show me work orders grouped by equipment"
- "Parts grouped by supplier"
- "Faults grouped by month"
- "Budget by cost center"

**Traditional PMS Features:**
- Group by dropdown (group WOs by: equipment, assigned to, status, priority)
- Pivot tables (parts by supplier × category)
- Aggregated views (total cost by equipment, fault count by system)

**Current CelesteOS Coverage:**
- ❌ No grouping capability
- ❌ Returns flat lists or single cards

**What We Need:**
```
VIEW PATTERN: group_by
  - Group work_orders by: equipment, assigned_to, status, priority, due_date (week)
  - Group parts by: category, supplier, storage_location
  - Group faults by: equipment, severity, month_occurred
  - Group purchases by: supplier, status, cost_center

VIEW PATTERN: aggregated_view
  - Total cost by equipment
  - Fault count by system (bar chart)
  - Part consumption by month (line chart)
  - WO completion rate (%)
```

---

### 9. SEARCH RESULT VIEWS

**User Queries:**
- "Search for 'coolant'"
- "Find all references to MTU"
- "Documents mentioning stabiliser"

**Traditional PMS Features:**
- Keyword search with filters
- Search result grouping (documents, WOs, parts, equipment)
- Search within results
- Saved searches

**Current CelesteOS Coverage:**
- ✅ Good - conversational search returns cards
- ✅ Entity extraction identifies equipment/parts
- ❌ No "search within results" refinement
- ❌ No saved searches

**What We Need:**
```
VIEW PATTERN: search_results
  - Grouped by entity type (documents, WOs, parts, equipment, faults)
  - Filter search results (date range, category, status)
  - Sort search results (relevance, date, priority)
  - Refine search (add more keywords, exclude terms)

VIEW PATTERN: saved_searches
  - Save common queries ("my overdue tasks", "low stock HVAC parts")
  - Quick access from dashboard
```

---

### 10. COMPARISON VIEWS

**User Queries:**
- "This month vs last month"
- "Generator 1 vs Generator 2 performance"
- "Actual vs budgeted costs"
- "Planned vs unplanned maintenance ratio"

**Traditional PMS Features:**
- Period comparison (this month vs last month, YoY)
- Entity comparison (equipment A vs equipment B)
- Budget vs actual views
- Trend analysis (fault frequency trending up/down)

**Current CelesteOS Coverage:**
- ❌ No comparison views
- ❌ No trending analysis

**What We Need:**
```
VIEW PATTERN: compare_periods
  - This week vs last week
  - This month vs last month
  - Q1 vs Q2
  - YoY comparison

VIEW PATTERN: compare_entities
  - Equipment A vs Equipment B (fault count, maintenance cost, uptime)
  - Supplier A vs Supplier B (price, lead time, reliability)

VIEW PATTERN: compare_plan_vs_actual
  - Budgeted cost vs actual cost
  - Planned maintenance vs completed maintenance
  - Forecasted vs actual consumption
```

---

### 11. HIERARCHICAL/TREE VIEWS

**User Queries:**
- "Show me equipment tree"
- "All subsystems of main engine"
- "Component breakdown of HVAC system"

**Traditional PMS Features:**
- Equipment tree (expandable hierarchy)
- Bill of materials (BOM) tree
- Document folder structure
- Work breakdown structure (shipyard projects)

**Current CelesteOS Coverage:**
- ❌ No hierarchical views
- ❌ Equipment relationships not visualized

**What We Need:**
```
VIEW PATTERN: equipment_tree
  - Main Engine
    ├── Cooling System
    │   ├── Coolant Pump
    │   │   └── Impeller
    │   └── Heat Exchanger
    ├── Fuel System
    └── Exhaust System

VIEW PATTERN: bill_of_materials
  - Part → subcomponents → consumables

VIEW PATTERN: document_folders
  - Manuals
    ├── Propulsion
    │   ├── Main Engine
    │   └── Gearbox
    └── Hotel
        └── HVAC
```

---

### 12. MAP/SPATIAL VIEWS

**User Queries:**
- "Show me equipment on GA drawing"
- "Where is this part stored?" (visual map)
- "All WOs on Deck 3"

**Traditional PMS Features:**
- GA drawing overlay (clickable zones)
- Storage location map (visual inventory layout)
- Deck-by-deck view

**Current CelesteOS Coverage:**
- ❌ No spatial/map views
- ✅ Text-based location (view_part_location returns "Deck 2, Locker 5")

**What We Need:**
```
VIEW PATTERN: ga_drawing_overlay
  - Upload GA drawing
  - Tag equipment locations on drawing
  - Click zone → see all equipment in that zone
  - Color-code by status (operational, fault, maintenance)

VIEW PATTERN: storage_map
  - Visual representation of storage areas
  - Click locker → see all parts inside
  - Color-code by stock level (green = full, yellow = low, red = empty)
```

---

### 13. DASHBOARD/WIDGET VIEWS

**User Queries:**
- "Show me engineering dashboard"
- "What's the status overview?"
- "Fleet summary"

**Traditional PMS Features:**
- Customizable dashboards
- Widget library (overdue WOs widget, low stock widget, compliance widget)
- Role-based default dashboards
- KPI tiles (MTBF, MTTR, uptime %)

**Current CelesteOS Coverage:**
- ✅ view_smart_summary (situational briefing)
- ✅ view_fleet_summary (multi-vessel)
- ❌ No customizable dashboards
- ❌ No widget configuration

**What We Need:**
```
VIEW PATTERN: dashboard
  - Tile/widget based layout
  - Customizable per user
  - Pre-built widgets:
    - Overdue tasks (count + list)
    - Low stock items (count + list)
    - Recent faults (timeline)
    - Compliance status (red/yellow/green)
    - Upcoming maintenance (next 7 days)
    - Budget tracker (actual vs planned)

VIEW PATTERN: kpi_view
  - MTBF (Mean Time Between Failures)
  - MTTR (Mean Time To Repair)
  - Uptime %
  - PMS compliance rate
  - Budget utilization %
```

---

### 14. REPORT/EXPORT VIEWS

**User Queries:**
- "Export maintenance report"
- "Generate audit pack"
- "Download inventory list"

**Traditional PMS Features:**
- Pre-built reports (maintenance summary, inventory report, compliance report)
- Custom report builder
- Export formats (PDF, Excel, CSV)
- Scheduled reports (weekly email)

**Current CelesteOS Coverage:**
- ✅ export_handover, export_hours_of_rest, export_worklist, export_fleet_summary
- ❌ No custom report builder
- ❌ No scheduled reports

**What We Need:**
```
VIEW PATTERN: report_view
  - Pre-built reports:
    - Maintenance summary (period-based)
    - Inventory report (current stock levels)
    - Fault report (by equipment/period)
    - Budget report (cost breakdown)
    - Compliance report (cert expiry, HOR violations)

VIEW PATTERN: custom_report_builder
  - Select entity type (WOs, parts, equipment)
  - Select fields to include
  - Apply filters
  - Choose grouping
  - Export as PDF/Excel
```

---

## Reverse Engineering: "Show me all parts in this box"

### The Query Breakdown

**User says:** "Show me all parts in this box"

**What this requires:**

1. **Entity Detection:**
   - Entity type: parts
   - Filter type: location
   - Filter value: "this box" → needs resolution (Box ID, Locker, Shelf)

2. **View Pattern:**
   - VIEW: filter_by_location
   - DISPLAY: part list (table or card grid)
   - GROUPING: optional (by category, by supplier)
   - SORTING: alphabetical, stock level, last used

3. **Backend Query:**
   ```sql
   SELECT * FROM parts
   WHERE storage_location LIKE '%Box 3%'
     OR storage_bin = 'Box 3'
     OR storage_shelf = 'Shelf B - Box 3'
   ORDER BY part_name ASC;
   ```

4. **Response Card:**
   ```json
   {
     "card_type": "part_list",
     "view_pattern": "filter_by_location",
     "filters_applied": {
       "location": "Deck 2, Locker 5, Box 3"
     },
     "items": [
       {
         "part_id": "uuid-1",
         "part_name": "Oil Filter - CAT",
         "part_number": "CAT-OF-2019",
         "quantity": 5,
         "location": "Deck 2, Locker 5, Box 3"
       },
       {
         "part_id": "uuid-2",
         "part_name": "Fuel Filter - MTU",
         "part_number": "MTU-FF-4000",
         "quantity": 3,
         "location": "Deck 2, Locker 5, Box 3"
       }
     ],
     "total_items": 2,
     "actions": [
       "view_part_stock",
       "order_part",
       "log_part_usage"
     ]
   }
   ```

### What We're Missing

**Current state:**
- User asks "show me all parts in this box"
- System returns: "I don't understand 'this box'. Which specific location?"

**What we need:**
- User asks "show me all parts in this box"
- System resolves "this box" → prompts "Which box?" → user says "Box 3, Locker 5"
- System queries parts filtered by location
- Returns part_list card with filter applied
- User sees table of parts with actions available

---

## Reverse Engineering: "What is quantity of X?"

### The Query Breakdown

**User says:** "What is quantity of oil filter?"

**What this requires:**

1. **Entity Detection:**
   - Entity type: part
   - Entity value: "oil filter" → needs resolution (multiple oil filters exist)
   - Query type: quantity lookup

2. **View Pattern:**
   - VIEW: specific_value_query
   - DISPLAY: part card with quantity emphasized
   - OPTIONAL: Disambiguate (show list if multiple matches)

3. **Backend Query:**
   ```sql
   SELECT * FROM parts
   WHERE part_name LIKE '%oil filter%'
      OR part_number LIKE '%oil filter%';
   ```

4. **Response:**

   **If single match:**
   ```json
   {
     "card_type": "part",
     "view_pattern": "specific_value_query",
     "part_name": "Oil Filter - CAT 3512",
     "part_number": "CAT-OF-2019",
     "quantity": 5,
     "min_level": 2,
     "location": "Deck 2, Locker 5, Box 3",
     "answer": "You have 5 oil filters in stock (CAT-OF-2019). Stored in Deck 2, Locker 5, Box 3.",
     "actions": [
       "view_part_stock",
       "order_part"
     ]
   }
   ```

   **If multiple matches:**
   ```json
   {
     "card_type": "part_list",
     "view_pattern": "disambiguate",
     "question": "Which oil filter?",
     "options": [
       {
         "part_id": "uuid-1",
         "part_name": "Oil Filter - CAT 3512",
         "part_number": "CAT-OF-2019",
         "quantity": 5
       },
       {
         "part_id": "uuid-2",
         "part_name": "Oil Filter - MTU 4000",
         "part_number": "MTU-OF-4000",
         "quantity": 3
       },
       {
         "part_id": "uuid-3",
         "part_name": "Oil Filter - Hydraulic System",
         "part_number": "HYD-OF-001",
         "quantity": 8
       }
     ]
   }
   ```

### What We're Missing

**Current state:**
- view_part_stock exists
- But requires specific part identification
- No disambiguation flow
- No "quick answer" for simple quantity queries

**What we need:**
- Handle ambiguous queries gracefully
- Provide quick answers for simple questions
- Offer disambiguation when needed
- Support fuzzy matching ("oil filter" matches multiple parts)

---

## The Complete Viewing Pattern Taxonomy

### 14 Core View Patterns

| Pattern | User Intent | Example Query | Current Support | Priority |
|---------|-------------|---------------|-----------------|----------|
| **filter_by_location** | See items in specific location | "parts in Box 3" | ❌ None | 🔴 HIGH |
| **filter_by_status** | See items in specific state | "overdue tasks" | ⚠️ Partial | 🔴 HIGH |
| **filter_by_time** | See items in time range | "faults this week" | ⚠️ Partial | 🔴 HIGH |
| **filter_by_equipment** | See items for equipment | "WOs for Generator 1" | ✅ Good | ✅ Done |
| **filter_by_person** | See items for person | "my tasks" | ❌ None | 🟡 MEDIUM |
| **filter_by_category** | See items by type | "HVAC parts" | ❌ None | 🟡 MEDIUM |
| **filter_by_quantity** | See items by measurement | "parts qty < 3" | ❌ None | 🟡 MEDIUM |
| **group_by** | See items organized | "WOs by equipment" | ❌ None | 🟡 MEDIUM |
| **search_results** | Find by keyword | "search coolant" | ✅ Good | ✅ Done |
| **compare** | Compare entities/periods | "this month vs last" | ❌ None | 🟢 LOW |
| **hierarchy** | See tree structure | "equipment tree" | ❌ None | 🟢 LOW |
| **map_spatial** | See on drawing/map | "equipment on GA" | ❌ None | 🟢 LOW |
| **dashboard** | See overview widgets | "engineering dashboard" | ⚠️ Partial | 🟡 MEDIUM |
| **report** | Generate reports | "export inventory" | ⚠️ Partial | 🟡 MEDIUM |

---

## What This Means for Micro-Actions

### We Need "View Actions" Separate from "Mutation Actions"

**Current approach:**
- Micro-actions = things that DO something (create, edit, mark complete)
- Views = implied by query intent

**Better approach:**
- **Mutation Actions** (57-67 actions) - Things that change state
- **View Patterns** (14 patterns) - Ways to SEE data
- **Filter Parameters** - How views are refined

### Example: Viewing Parts

**User says:** "Show me all HVAC parts in Deck 2 with stock < 3"

**This is NOT a new action, it's:**
```json
{
  "view_pattern": "filter_by_multiple",
  "entity_type": "parts",
  "filters": [
    {
      "type": "category",
      "value": "HVAC"
    },
    {
      "type": "location",
      "value": "Deck 2"
    },
    {
      "type": "quantity",
      "operator": "<",
      "value": 3
    }
  ],
  "display": "part_list",
  "actions": [
    "view_part_stock",
    "order_part",
    "edit_part_details"
  ]
}
```

**Backend processes:**
1. Parse intent → extract filters
2. Build SQL query with WHERE clauses
3. Return part_list card
4. Each part card has action buttons

**Frontend displays:**
- Table/grid of parts matching filters
- Applied filters shown at top (removable chips)
- Sort options (name, quantity, last used)
- Action buttons on each row

---

## Recommendation: Add View Pattern Specification

### New Document: VIEW_PATTERNS_REGISTRY.md

Similar to MICRO_ACTION_REGISTRY.md, but for viewing patterns:

```markdown
# VIEW_PATTERNS_REGISTRY.md

## filter_by_location

**Pattern Name:** filter_by_location
**Applies To:** parts, equipment, work_orders
**User Queries:**
  - "show me all parts in Box 3"
  - "equipment in engine room"
  - "WOs for machinery space"

**Filter Parameters:**
  - location_type: deck, room, locker, box, shelf, zone
  - location_value: specific location identifier

**Display Format:** list (table or card grid)

**Available Actions:** Depends on entity type
  - parts: view_part_stock, order_part, edit_part_details
  - equipment: view_equipment_details, create_work_order
  - work_orders: mark_work_order_complete, add_work_order_note

**Backend Query Pattern:**
```sql
SELECT * FROM {entity_type}
WHERE storage_location LIKE '%{location_value}%'
   OR location = '{location_value}'
ORDER BY {sort_field} {sort_direction};
```
```

---

## Summary: The READ Dimension

### You're Right - We're Missing:

1. **Location-based views** - "all parts in this box" ❌
2. **Quantity queries** - "what is quantity of X" ⚠️ (exists but no disambiguation)
3. **Status filtering** - "all overdue tasks" ⚠️ (works but not formalized)
4. **Grouping** - "WOs by equipment" ❌
5. **Time filtering** - "faults this week" ⚠️ (works but not explicit)
6. **Comparison** - "this month vs last" ❌
7. **Hierarchical** - "equipment tree" ❌
8. **Spatial** - "on GA drawing" ❌

### What Competitors Have That We Don't:

Most traditional PMS systems have:
- ✅ Filter dropdowns (status, category, assigned to, date range)
- ✅ Grouping options (group by X)
- ✅ Calendar/Gantt views
- ✅ Equipment hierarchy trees
- ✅ GA drawing overlays
- ✅ Customizable dashboards
- ✅ Location-based inventory views
- ✅ Comparison reports

### Recommendation:

**Add VIEW_PATTERNS specification alongside micro-actions:**

- **67 Micro-Actions** (what users DO) ← We have this
- **14 View Patterns** (how users SEE data) ← WE NEED THIS
- **Filter Parameters** (how views are refined) ← WE NEED THIS

This gives complete coverage of user intent:
- CREATE/UPDATE/DELETE → Micro-Actions ✅
- READ/VIEW/FILTER → View Patterns ❌ (missing)

Want me to create the complete VIEW_PATTERNS_REGISTRY.md?
