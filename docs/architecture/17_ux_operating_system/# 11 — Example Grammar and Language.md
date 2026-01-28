# 11 — Example Grammar and Language

## Purpose

Define the **shape of valid questions** in Celeste without hardcoding examples or constraining language. This document protects the principle that *anything the user says should work*, while giving engineers and RAG systems clear guidance on interpretation.

This is a language contract between:

* Users (natural, imperfect speech)
* Search (single interaction primitive)
* Retrieval (RAG + entity extraction)

---

## Core Principle

> **Users express intent. Celeste resolves meaning.**

Celeste must accept vague, partial, shorthand, stressed, or non-grammatical input without correction or friction.

---

## What This Document Is (and Is Not)

**This document defines:**

* Question *forms* (grammar patterns)
* Acceptable ambiguity
* Interpretation priorities

**This document does NOT define:**

* Final UI copy
* Fixed prompt text
* Button labels
* Command syntax

---

## Question Grammar Archetypes

These archetypes describe *how* people ask, not *what* they ask.

### 1) Temporal Queries

**Shape:**

* what happened [time]
* what changed since [event]
* anything new [today / last night]

**Characteristics:**

* Time may be implicit or explicit
* Time ranges may be vague

**System expectation:**

* Infer reasonable defaults
* Prefer recent, high-signal events

---

### 2) Status Queries

**Shape:**

* what is [state]
* is anything [overdue / broken / missing]

**Characteristics:**

* Often broad
* Often anxiety-driven

**System expectation:**

* Surface exceptions first
* Avoid exhaustive lists unless requested

---

### 3) Location Queries

**Shape:**

* where is [thing]
* do we have [item]

**Characteristics:**

* Object-first
* Minimal context

**System expectation:**

* Prioritise inventory + location entities
* Return most likely match, not all matches

---

### 4) Responsibility Queries

**Shape:**

* what do I need to [do / check]
* what am I responsible for [now]

**Characteristics:**

* Role- and time-sensitive
* Often implicit urgency

**System expectation:**

* Bias by operational posture
* Provide ordered suggestions, not mandates

---

### 5) Exception Queries

**Shape:**

* is anything wrong
* what needs attention

**Characteristics:**

* Highly abstract
* High cognitive load

**System expectation:**

* Filter aggressively
* Return only high-confidence exceptions

---

### 6) Reference Queries

**Shape:**

* show me [manual / document]
* how does [system] work

**Characteristics:**

* Knowledge-seeking
* Often incomplete naming

**System expectation:**

* Use fuzzy matching
* Prefer authoritative sources

---

## Language Tolerance Rules

Celeste must tolerate:

* Misspellings
* Fragmented sentences
* Mixed languages
* Shorthand and acronyms
* Stress-driven phrasing

Celeste must never:

* Require exact matches
* Correct grammar visibly
* Ask users to rephrase unnecessarily

---

## Ambiguity Handling

When input is ambiguous:

1. Prefer likely intent over completeness
2. Surface best guess first
3. Offer refinement *only if needed*

Never respond with:

> “Please clarify.”

Instead:

> “Here’s what I found. Want me to narrow it?”

---

## Non-Goals

Celeste is not:

* A command-line interface
* A keyword search box
* A form-driven system

Language is **free-form by design**.

---

## RAG Alignment Notes

* Retrieval should prioritise intent resolution over literal matching
* Entity extraction should be permissive
* Ranking should weight recency, role posture, and exception severity

---

## Guardrails

* No enforced query syntax
* No command prefixes
* No required fields
* No mode switching

---

## Summary

Celeste does not teach users how to speak.
Celeste learns how users already speak.

Language is not an interface.
It is the medium.
