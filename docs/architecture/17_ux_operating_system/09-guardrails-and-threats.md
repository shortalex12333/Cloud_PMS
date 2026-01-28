09-guardrails-and-threats.md# CelesteOS — Guardrails, Drift, and Existential Threats

## Why This Document Exists

Every serious system fails the same way:
not through bad ideas, but through small exceptions.

This document exists to:
- identify where Celeste can drift
- define what must be rejected immediately
- protect the product when pressure mounts

If this document feels restrictive, it is working.

---

## The Core Threat

The greatest threat to Celeste is **becoming familiar**.

Familiarity invites:
- dashboards
- modules
- tiles
- shortcuts
- performance views
- managerial abstractions

These feel safe.
They are regressions.

---

## Drift Vectors (Known and Repeating)

Celeste will be pressured to add:

1. “Just a small dashboard”
2. “A summary view for managers”
3. “Completion indicators”
4. “Overdue states”
5. “A quicker way without asking”
6. “Automation to save time”
7. “A toggle for advanced users”

Each of these has destroyed systems before.

---

## Automatic Rejection List

Any proposal that introduces:

- dashboards as a primary surface
- persistent navigation for daily work
- silent automation
- inferred intent or confidence
- performance scoring
- productivity analytics
- “overdue” logic inside the ledger
- visual reassurance in place of proof
- features that reduce asking

…must be rejected without debate.

---

## The Familiarity Trap

Users will ask for:
- what they already know
- what feels comfortable
- what reduces immediate friction

This is not malicious.
It is human.

But satisfying this instinct preserves:
- legacy failure modes
- post-hoc logging
- unverifiable claims
- blame-shifting

Celeste exists to end this.

---

## Weaknesses We Accept

Celeste deliberately accepts:

- a learning curve
- initial discomfort
- fewer visual cues
- slower perceived speed
- resistance from legacy users

These are costs, not bugs.

---

## Threats We Do Not Accept

Celeste must never accept:

- data loss
- unverifiable actions
- hidden state changes
- ambiguous responsibility
- reliance on memory
- features that bypass accountability

These are existential threats.

---

## The “Investigation Test”

Before shipping any feature, ask:

> “Would this help or hinder a calm reconstruction  
> of events six months from now?”

If it hinders, it does not ship.

---

## The “Asking Test”

Also ask:

> “Does this make users ask more freely,  
> or does it encourage them to click instead?”

If it reduces asking, it is wrong.

---

## Enforcement Mechanism

This document overrides:
- feature requests
- customer pressure
- sales objections
- internal convenience

If a decision violates this document, it is not an exception.
It is drift.

---

## Final Lock

> **Celeste survives by saying no more often than yes.  
> Saying yes is easy.  
> Recoverable truth is hard.**

This document is canonical.
