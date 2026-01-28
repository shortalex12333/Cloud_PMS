# Role Bucket Biasing

This document defines how Celeste biases **handover relevance, ordering, and emphasis** based on the viewing user’s role.

The handover document itself is always uniform.

Biasing affects:

- which sections are expanded by default
- ordering of sections
- ordering of entries inside sections
- which risk tags are visually emphasized
- what is surfaced first in search

Biasing never:

- hides content
- removes content
- changes wording
- changes source references

Biasing is **relevance tuning**, not access control.

---

## Core rule

**All roles see the same handover.  
Not all roles see it in the same order.**

This preserves:

- shared situational awareness
- trust in completeness
- role-specific efficiency

---

## Role bias model

Each role has:

- Primary bucket focus
- Secondary bucket focus
- Risk tag sensitivity
- Command synthesis priority

These parameters tune ranking and presentation.

---

## Role bias table

### Yacht Manager (shore)

Primary buckets:
- Command
- Admin & Compliance

Secondary buckets:
- Engineering

Risk sensitivity:
- Compliance-Critical
- Cost-Impacting
- Safety-Critical

Command synthesis emphasis:
- Operational Risk State
- Vessel Readiness State

---

### Captain

Primary buckets:
- Command
- Engineering
- Deck

Secondary buckets:
- ETO / AV-IT
- Admin & Compliance

Risk sensitivity:
- Safety-Critical
- Compliance-Critical
- Guest-Impacting

Command synthesis emphasis:
- All CMD domains

---

### Chief Engineer

Primary buckets:
- Engineering

Secondary buckets:
- ETO / AV-IT
- Command

Risk sensitivity:
- Safety-Critical
- Operational-Debt
- Cost-Impacting

Command synthesis emphasis:
- Vessel Readiness State

---

### ETO / AV-IT Officer

Primary buckets:
- ETO / AV-IT

Secondary buckets:
- Engineering
- Deck
- Interior

Risk sensitivity:
- Safety-Critical
- Guest-Impacting
- Operational-Debt

Command synthesis emphasis:
- Guest Experience State
- Vessel Readiness State

---

### Bosun

Primary buckets:
- Deck

Secondary buckets:
- Engineering
- ETO / AV-IT

Risk sensitivity:
- Safety-Critical
- Guest-Impacting

Command synthesis emphasis:
- Guest Experience State

---

### Deckhand

Primary buckets:
- Deck

Secondary buckets:
- None

Risk sensitivity:
- Safety-Critical

Command synthesis emphasis:
- None

---

### Chief Stew

Primary buckets:
- Interior

Secondary buckets:
- Deck
- ETO / AV-IT

Risk sensitivity:
- Guest-Impacting
- Safety-Critical

Command synthesis emphasis:
- Guest Experience State

---

### Stew

Primary buckets:
- Interior

Secondary buckets:
- None

Risk sensitivity:
- Guest-Impacting

Command synthesis emphasis:
- None

---

### Purser / Admin

Primary buckets:
- Admin & Compliance

Secondary buckets:
- Command

Risk sensitivity:
- Compliance-Critical
- Cost-Impacting

Command synthesis emphasis:
- Operational Risk State

---

## How bias is applied

### Document view

- Primary bucket opens expanded
- Secondary buckets collapsed
- Others collapsed

### Ordering

- Primary bucket appears first
- Secondary buckets next
- Remaining buckets follow standard order

### Risk emphasis

Entries tagged with role-sensitive risk tags:

- float higher inside bucket
- visually flagged
- included in command synthesis priority

### Search results

Handover entries matching user role bias:

- rank higher
- appear earlier in result sets
- appear with shorter summaries

---

## Why this matters

Without biasing:

- handovers become long and flat
- senior roles miss risk
- junior roles see noise
- relevance feels generic

With biasing:

- everyone sees the same truth
- in the order that matches their job
- without hiding information

---

## Non-negotiable

- Bias never removes content
- Bias never hides risk
- Bias never rewrites meaning
- Bias never alters source traceability

Uniform truth.  
Role-aware presentation.

---
