fBelow is your **master “Modules & Capabilities” thesis** — the definitive list of *everything CelesteOS can do*, expressed in a way that aligns with your single-search-bar UX philosophy.

This document is the foundation you will put into GitHub under:

**`docs/modules.md`**
(or `README.md` for the features section)

It describes **all functional modules**, but written in the language of:

> “Everything is activated through the search bar.”

This is the clearest representation of your product’s capability map.

---

# 🚢 **CELESTEOS MODULES — WHAT THE SOFTWARE CAN DO**

*(All triggered and controlled via one universal search bar)*

Below are the modules **from a functional perspective** — the **WHAT**, not the internal **HOW**.

These are grouped so that future developers, designers, and investors get a complete picture of the system.

---

# 1. 🔍 **Global Search (Core Module)**

The heart of CelesteOS. Everything begins here.

### **Capabilities**

* Search across:

  * Manuals
  * PDFs
  * NAS documents
  * Emails
  * Work orders
  * Maintenance history
  * Faults
  * Inventory
  * SOPs
  * Parts
  * Photos
  * Handover drafts
  * Celeste global scraped data
* Natural-language queries (“fault code 123 on main engine”)
* Entity extraction to auto-detect:

  * equipment
  * part
  * manual
  * fault
  * task
  * SOP
  * notes
  * intent/action
* Contextual result cards + micro-actions
* Multi-source document fusion (RAG + Graph RAG)
* Confidence scoring
* “Other documents” list

### **User sees:**

> “Just type what you need.”

---

# 2. 🔧 **Planned Maintenance (PMS) Module**

Triggered by search, not by navigating menus.

### **Capabilities**

* Create work order
* View work order history
* Auto-fill work order from search
* Automatically detect equipment from query
* Pull correct manual sections
* Suggest parts used historically
* Auto-link to faults
* Auto-add to handover
* Schedule frequency (hours or dates)
* Task execution logs
* Add photos or documents to WO
* Work order status changes

### **User sees:**

> “Create a work order for stabiliser pump leak.”

Celeste auto-populates everything.

---

# 3. 📦 **Inventory & Spare Parts Module**

### **Capabilities**

* Search all parts
* Scan part via mobile camera
* Check stock levels + reorder thresholds
* Link part → equipment → faults → WO
* Add parts to a work order
* Log usage
* Reorder quantity recommendations
* See location: locker, bin, shelf
* Purchase log integration
* Supplier linking

### **User sees:**

> “Find racor 2040 filter”
> “Add this part to work order”
> “Where is this stored?”

---

# 4. 🛒 **Purchase & Supplier Module**

### **Capabilities**

* Create purchase request
* Link vendor / supplier
* Auto-fill purchase lines from parts
* Track order status
* Log deliveries
* Log last known price
* Connect to invoice docs from NAS/email
* Make predictive cost insights

### **User sees:**

> “Order 2 stabiliser filters”
> “Show me latest MTU invoices”

---

# 5. 🛠 **Faults & Diagnosis Module**

### **Capabilities**

* Detect fault code + equipment automatically
* Pull matching manual pages
* Show all historical similar faults
* Show related parts
* Past interventions
* Predictive “likelihood of failure soon”
* Link fault → work order
* Summaries for handover

### **User sees:**

> “fault code e047 port gen”
> “show past overheating events”

---

# 6. 📄 **Handover Module (Auto-generated)**

### **Capabilities**

* Auto-build handover draft (50% complete instantly)
* Add items:

  * faults
  * work orders
  * notes
  * photos
  * documents
* Auto-summarize technical text
* Organise by system
* Export to PDF / HTML
* Save draft & final version
* Multi-user contributions
* Integrate with search directly (“Add to handover”)

### **User sees:**

> “Add this to handover”
> “Generate weekly handover”

---

# 7. 🗃 **Handover History Module**

### **Capabilities**

* Archive all past handovers
* Search handover history
* Compare between periods
* Summarise last 60-days work

### **User sees:**

> “What happened last month?”
> “Show handover from July”

---

# 8. 🧠 **Predictive Maintenance Module (V1)**

### **Capabilities**

* Recurring pattern detection
* Equipment “risk index”
* Fault clusters
* Search query clusters (“crew pain index”)
* Parts replaced too frequently
* Identify weak systems
* Fleet-wide predictive map
* Manual-based pattern extraction

### **User sees:**

> “Any emerging issues with AC system?”
> “What’s most likely to fail next?”

---

# 9. 🤝 **Comment / Note Module**

### **Capabilities**

* Freeform notes
* Voice-to-text notes (mobile)
* Attach note to equipment, fault, WO
* Add to handover
* Summaries
* Searchable as embeddings

### **User sees:**

> “Add note for my chief about gen vibration”

---

# 10. 📧 **Email Integration Module**

### **Capabilities**

* Connect Outlook / Gmail
* Search email bodies + attachments
* Index engineering-relevant emails
* Auto-detect vendor quotes / tasks
* Link email → WO / fault / part
* Create draft handover item from email

### **User sees:**

> “Find the email from MTU about coolant flush and add to handover”

---

# 11. 🗂 **NAS Document Module (Cloud Mirrored)**

### **Capabilities**

* Mirror entire engineering NAS to cloud
* SHA256 integrity
* Chunking + OCR + embedding
* Open any PDF in app
* Multi-device access
* Version tracking
* Equipment autodetection from files

### **User sees:**

> “Open MTU manual”
> “Find drawing for black water tank”

---

# 12. 🌐 **Celeste Global Knowledge Module**

### **Capabilities**

* Thousands of scraped marine engineering pages
* Forum solutions
* Manufacturer bulletins
* General fault patterns
* Vectorised globally
* Bridges knowledge between yachts

### **User sees:**

> “Has anyone solved this on other boats?”

---

# 13. 🧭 **Hours of Rest (HOR) Module**

### **Capabilities**

* Log work / rest hours
* Compliance alerts
* Export report for MLC
* Minimal UI (because low-use)

### **User sees:**

> “Log hours for today”
> “Show HOR violations this week”

---

# 14. 🛡️ **User & Token Management Module**

### **Capabilities**

* User accounts
* Yacht-based isolation
* Token refresh for:

  * Email
  * OneDrive
  * Outlook
* Mobile tokens for upload
* Yacht signature for routing uploads
* Device sessions

### **User sees:**

> Nothing. This is backend.
> But devs see:

* `yacht_signature`
* `user_token`
* `app_session`

---

# 15. 🌉 **Migration Module (IDEA/AMOS Import)**

### **Capabilities**

* Extract data from IDEA/AMOS exports
* Transform → Celeste schema
* Auto-map:

  * equipment
  * faults
  * history
  * documents
  * parts
* Index everything automatically
* Build predictive baselines

### **User sees:**

> “Import IDEA data”
> (you run the script, they are shocked)

---

# 16. 🧬 **Graph RAG Module**

This powers deep intelligence (relationships, patterns, system context).

### **Capabilities**

* Equipment → Parts → Faults → Docs graph
* Link mentions between documents
* Detect central components in faults
* Show relational clusters
* Support deep research mode

### **User sees:**

> “Deeper research mode”
> “Show links between stabiliser failures and hydraulic system”

---

# 17. 🤖 **Regular RAG Module**

This powers everyday query answering.

### **Capabilities**

* Chunk documents
* Embed
* Retrieve top-K
* Hybrid filtering:

  * equipment_id
  * fault_code
  * document_type
  * date
* Summaries generated from RAG

### **User sees:**

> “Why is generator overheating?”
> Celeste finds:

* manual pages
* past reg logs
* relevant email
* handover note

---

# 18. 📱 **Mobile Capture Module**

### **Capabilities**

* Photo upload → instantly indexed
* Quick defect capture
* Scan part QR codes
* Save note
* Create work order from mobile
* Search ANYTHING
* Offline caching (light)

### **User sees:**

> “Take photo of the leak”
> “Create work order with this image”

---

# 19. 🔧 **User-Initiated Actions (All From Search Bar)**

### Micro-actions triggered contextually:

* Open document
* Create work order
* Add to handover
* Add note
* Flag issue
* View part
* Order part
* Add photo
* Show predictive insights
* View history
* Assign work
* Export report
* Add to inventory
* Tag equipment
* Resolve fault

This is the magic:
**Every module surfaces only when relevant.**

---

# 🧨 **Final Summary: The Product in One Sentence**

> **CelesteOS is a cloud-first engineering brain for yachts that lets you find anything, create anything, diagnose anything, and hand over anything — all through one universal search bar driven by RAG, Graph RAG, and dynamic micro-actions.**

---

