
```markdown
# Domain to Bucket Map

This document defines how **system domains** map to **handover presentation buckets**.

Domains represent **what system is affected**.  
Buckets represent **how the handover document is structured**.

Domains are used for:

- storage
- relevance ranking
- overlap resolution
- ownership inference

Buckets are used only for:

- document layout
- visual consistency
- crew familiarity

---

## Core rule

Every handover entry has:

- one **primary domain**
- optional **secondary domains**
- exactly one **presentation bucket**

If multiple domains exist, the **primary domain decides the bucket**.  
Secondary domains are used for cross-role relevance, not for duplication.

---

## Engineering Domains → Engineering Bucket

| Domain Code | Domain Name | Typical Subdomains |
|-------------|-------------|--------------------|
| ENG-01 | Propulsion & Drive | Gearbox, shaft, thrusters, stabilizers |
| ENG-02 | Power Generation | Generators, load sharing, shore changeover |
| ENG-03 | Electrical Distribution | Switchboards, breakers, UPS, transformers |
| ENG-04 | HVAC & Refrigeration | Chillers, AHUs, compressors, cold rooms |
| ENG-05 | Plumbing & Sanitation | Fresh water, grey/black, bilge, STP |
| ENG-06 | Fuel & Lubrication | Transfer, purification, day tanks |
| ENG-07 | Hydraulics & Pneumatics | HPUs, actuators, leaks, pressure faults |
| ENG-08 | Fire Detection & Suppression | Panels, loops, alarms, fixed suppression |
| ENG-09 | Safety & Life-Saving Equipment | Lifeboats, mounts, release systems |
| ENG-10 | Machinery Spaces General | Leaks, vibration, abnormal noise |

**Presentation Bucket:** Engineering

---

## ETO / AV-IT Domains → ETO / AV-IT Bucket

| Domain Code | Domain Name | Typical Subdomains |
|-------------|-------------|--------------------|
| ETO-01 | Navigation Electronics | Radar, ECDIS, GPS, AIS, gyro |
| ETO-02 | Networks & Connectivity | VSAT, Starlink, Wi-Fi, switching |
| ETO-03 | AV & Guest Control | Crestron, TVs, audio zones |
| ETO-04 | CCTV & Access Control | Cameras, NVR, door systems |
| ETO-05 | Monitoring & Alarm Routing | AMS, PLC, sensor feeds |
| ETO-06 | Radio & GMDSS | VHF, satcoms, distress systems |

**Presentation Bucket:** ETO / AV-IT

---

## Deck Domains → Deck Bucket

| Domain Code | Domain Name | Typical Subdomains |
|-------------|-------------|--------------------|
| DECK-01 | Deck Machinery | Windlass, cranes, passerelle |
| DECK-02 | Mooring & Anchoring | Lines, fenders, anchors |
| DECK-03 | Tenders & Toys | Tenders, jetskis, chargers |
| DECK-04 | Exterior Maintenance | Teak, paint, corrosion |
| DECK-05 | Bridge Operations | Passage planning, charts, SOPs |
| DECK-06 | On-Deck Safety | PPE, working aloft, near misses |

**Presentation Bucket:** Deck

---

## Interior Domains → Interior Bucket

| Domain Code | Domain Name | Typical Subdomains |
|-------------|-------------|--------------------|
| INT-01 | Guest Services & Preferences | Likes, dislikes, boundaries |
| INT-02 | Housekeeping & Laundry | Laundry machines, linen |
| INT-03 | Galley & Food Service | Galley equipment constraints |
| INT-04 | Interior Inventory | Amenities, wines, consumables |

**Presentation Bucket:** Interior

---

## Admin & Compliance Domains → Admin & Compliance Bucket

| Domain Code | Domain Name | Typical Subdomains |
|-------------|-------------|--------------------|
| ADM-01 | Compliance & Certification | Flag, class, inspections |
| ADM-02 | Crew & HR | Contracts, visas, rotations |
| ADM-03 | Finance & Accounting | Invoices, payments |
| ADM-04 | Procurement & Logistics | POs, deliveries, customs |
| ADM-05 | Port Ops & Agents | Clearances, port docs |
| ADM-06 | Insurance & Claims | Incidents, insurer actions |

**Presentation Bucket:** Admin & Compliance

---

## Command Synthesis Domains → Command Bucket

These domains are **never manually assigned**.  
They are generated during handover assembly.

| Domain Code | Domain Name | Description |
|-------------|-------------|-------------|
| CMD-01 | Operational Risk State | Cross-domain unresolved risk |
| CMD-02 | Guest Experience State | Cross-domain guest-impact summary |
| CMD-03 | Vessel Readiness State | Cross-domain operational readiness |

**Presentation Bucket:** Command

---

## Overlap rule examples

### Example 1 — ETO repairing passerelle control panel

- Primary Domain: DECK-01 (Deck Machinery)
- Secondary Domain: ETO-03 (AV & Guest Control)
- Presentation Bucket: Deck
- Relevance bias: ETO + Bosun + Captain

Result:
Appears once in Deck section.  
ETO still sees it via relevance bias.

---

### Example 2 — Fire detection panel fault

- Primary Domain: ENG-08 (Fire Detection & Suppression)
- Secondary Domain: ETO-05 (Monitoring & Alarm Routing)
- Presentation Bucket: Engineering
- Relevance bias: Chief Engineer + ETO + Captain

---

### Example 3 — Guest Wi-Fi complaints

- Primary Domain: ETO-02 (Networks & Connectivity)
- Secondary Domain: INT-01 (Guest Services)
- Presentation Bucket: ETO / AV-IT
- Relevance bias: ETO + Chief Stew + Captain

---

## Why this mapping matters

- Domains stay precise  
- Buckets stay stable  
- Overlap is supported  
- No duplication in documents  
- No “miscellaneous” category  
- Relevance remains role-aware  

---

## Non-negotiable

- No free-text bucket creation
- No dynamic bucket creation
- No domain deletion without migration plan

Domains evolve.  
Buckets remain stable.

---
