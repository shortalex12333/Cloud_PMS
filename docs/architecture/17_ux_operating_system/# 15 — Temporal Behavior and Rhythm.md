# 15 — Temporal Behavior and Rhythm

## Purpose

Define how Celeste behaves **across time** without dashboards, rituals, or enforced routines. This document connects habit formation to real operational rhythms onboard yachts, while preserving search‑first purity.

Time influences *posture*, not interface.

---

## Core Principle

> **Celeste adapts to time quietly. It never announces time‑based modes.**

There are no “morning views”, “daily dashboards”, or “end‑of‑day screens”.

Only subtle biasing of relevance, tone, and suggestion.

---

## The Yacht Time Reality

Yacht operations are:

* Cyclical
* Watch‑based
* Handover‑dependent
* Incident‑driven

Time awareness must respect this without formalizing rituals.

---

## Temporal Postures

Celeste recognizes **temporal posture**, not schedules.

### 1) Opening Posture (Start of Watch / Day)

**User mindset:** Orientation, reassurance

**System bias:**

* Recent changes
* Exceptions since last interaction
* Summaries over details

**What Celeste does:**

* Prioritises “what changed” answers
* Suggests broad, contextual responses

**What Celeste avoids:**

* Task lists
* Obligations
* Metrics

---

### 2) Active Posture (Mid‑Watch / During Work)

**User mindset:** Execution

**System bias:**

* Precision
* Location
* Direct answers

**What Celeste does:**

* Responds tersely
* Avoids summarization unless asked

**What Celeste avoids:**

* Interruptions
* Suggestions
* Teaching moments

---

### 3) Closing Posture (End of Watch / Day)

**User mindset:** Confirmation, transfer

**System bias:**

* Completeness
* Proof
* Handover relevance

**What Celeste does:**

* Surfaces ledger and handover context naturally
* Frames answers in “state as of now” language

**What Celeste avoids:**

* Forward planning prompts
* New tasks

---

## Time Without Ritual

Celeste must never:

* Require daily check‑ins
* Enforce routines
* Prompt based solely on clock time

Time is a bias, not a trigger.

---

## Interaction History as Temporal Signal

Celeste may infer posture from:

* Time since last interaction
* Previous query patterns
* Handover events

Inference is silent and reversible.

---

## Relationship to Prompts

Temporal context may influence:

* Which orientation prompts appear
* Which examples are shown

But never:

* Number of prompts
* Their authority
* Their urgency

---

## Guardrails

* No daily summaries unless asked
* No automatic end‑of‑day actions
* No “you should review” language
* No time‑driven alerts masquerading as prompts

---

## Implementation Notes

* Temporal biasing is ranking‑level only
* No UI state should explicitly reference time
* All behavior must degrade gracefully if time signals are absent

---

## Summary

Celeste respects time without ritual.

It meets users where they are —
not where a schedule assumes they should be.
