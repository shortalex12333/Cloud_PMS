# User Operating Profiles

This folder contains **role operating profiles** for Celeste.

These are **not personas**.
They are **behavioral, operational, and cognitive models** of real yacht roles.

Their purpose is to teach the system how professionals onboard and ashore:

- Think under pressure  
- Ask questions in natural language  
- Judge relevance  
- Detect risk  
- Transfer responsibility during handovers  

They are used to design:

- Search ranking bias  
- Query intent interpretation  
- Answer formatting  
- Trust and uncertainty handling  
- Automation safety rules  
- Handover continuity logic  

They are **foundational system inputs**, not documentation.

---

## Why this exists

Traditional yacht software assumes:

- Everyone needs the same screens  
- Navigation is how work happens  
- Logs equal truth  

Reality:

- Work happens in conversation and action  
- Records are incomplete  
- Context is lost during crew turnover  
- Professionals need answers, not dashboards  

Celeste is search-first.

Relevance depends on role, posture, and risk sensitivity — not permissions or menus.

These profiles define that relevance.

---

## File structure

Each file represents one operational role:

```

01-yacht-manager-shore.md
02-captain.md
03-chief-engineer.md
04-engineer-watchkeeper.md
05-bosun.md
06-deckhand.md
07-chief-stew.md
08-stew.md
09-purser-admin.md
10-eto-avit.md
```

---

## Mandatory schema per role

Each role file follows the same structure:

- Role summary  
- Primary responsibility  
- Daily reality  
- Decision horizon  
- Driving factors  
- Success metrics (informal, real)  
- What they value  
- What they are often misinformed about  
- How legacy software fails them  
- How Celeste should empower them  
- Search behavior profile  
- Handover sensitivity  

Consistency is critical.  
This allows machine interpretation and comparison across roles.

---

## How these are used

These profiles feed directly into:

```

/search-intelligence/
role-intent-libraries
relevance-weight-matrices
uncertainty-handling-rules

```

They drive:

- Query expansion  
- Result ranking  
- Conflict resolution  
- Answer tone and compression  
- Escalation behavior  

---

## Guiding principle

Celeste does not teach professionals how to work.

Celeste preserves operational truth and removes friction from finding it.

These profiles define what “truth” means to each role.

---
