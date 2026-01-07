Here’s a **clean master list** of *every feature and option* we’ve talked about for the PMS + Inventory system so far (plus extras from best-in-class systems). We’ll use this to decide what’s *minimum* vs *nice to have*.

---

### 🔧 Master Feature List

#### Asset / Equipment Management

* Asset register (all equipment, components, serial numbers)
* Parent/child relationships (system → subsystem → component)
* Location tracking (machinery space, deck, etc)
* Manufacturer & contact info
* Installation date / expected life / lifecycle tracking
* Condition/status monitoring
* Documents/manuals/certificates linked to equipment
* Criticality & risk scoring (if fails, what’s exposure)

#### Work Orders & Maintenance

* Work order creation: scheduled, corrective, unplanned
* Task description, title, priority, status
* Due date / running hours / calendar scheduling
* Frequency: hours, days, months, condition-based
* Equipment link: what piece of equipment the task is for
* Logs: last completed date/hours, next due date/hours
* History of completed work orders
* Parts used & labour logged on work order
* Faults related to tasks
* Comments from engineers / crew
* SOPs & checklists tied to tasks
* Mobile/field access & offline capability
* Escalation / SLA / notifications for overdue tasks
* Technician/contractor portal (external users)

#### Inventory & Spare Parts

* Part master: name, part number, manufacturer, compatibility
* Quantity on board / current stock
* Minimum reorder level, maximum, reorder quantity
* Storage location (deck, locker, shelf/bin)
* Supplier info, last price paid, last purchase date
* Lead time, warranty period
* Parts usage tracking (what tasks used which parts)
* Barcode/QR scanning for parts (field usability)
* On-order status & expected arrival

#### Search + Knowledge + Document Management

* Upload documents/manuals/photos/emails
* OCR + chunking of documents
* Embedding & vector search across documents + history
* Semantic search (natural language queries)
* “Stream by category” results (history, docs, parts, tasks)
* Graph relationships: equipment ↔ part ↔ fault ↔ document
* Toggle “deeper research mode” for extended graph/analysis

#### Handover / Shift / Audit Pack

* Automatically build handover packs from comments + work history + parts usage
* Export to PDF/HTML for shift change or vessel handover
* Comments and engineer log entries feed into handover creation
* Audit trails: who edited what, when

#### Analytics & Reporting

* Dashboard: uptime, MTBF (Mean Time Between Failures), MTTR (Mean Time To Repair)
* Parts consumption trends, cost per system
* Budget & maintenance cost modelling
* Condition-based maintenance suggestions
* Compliance tracking (ISM, class, warranty)
* Role-based dashboards (engineer vs captain vs purser)

#### Integration, Scalability & Architecture

* Multi-vessel / multi-asset support
* Role-based access control (RBAC)
* Tenant isolation (per-yacht database or schema)
* Offline mode for vessel environment
* API access & webhooks (n8n workflows)
* IoT/sensor integration (vibration, temp, hours)
* Security: encryption, backups, audit logs
* Mobile access for field techs

#### Value-Added / Premium

* Risk & criticality scoring of assets
* Predictive maintenance / AI suggestions
* Vendor/contractor portal & service contract tracking
* Warranty tracking & manufacturer service claims
* Graph-powered insight (not just search)
* Customizable workflow & templates per vessel type

---

That’s the full list so far.

---

If you’re okay, next I’ll **mark which of these are absolutely minimum for version 1**, and which can wait for later. Then we’ll build **table contents** (minimum schema) accordingly.
