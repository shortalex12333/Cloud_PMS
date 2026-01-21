# 30_DATABASE_SCHEMA_ASSUMPTIONS.md

This document defines the minimum database structures required to support Situational Continuity and Related expansion.

Schemas are advisory and may be adapted to existing tables, but semantics must be preserved.

## Core Tables

### situations

Represents a single, ephemeral situation.

Columns:

* id uuid primary key
* tenant_id uuid not null
* created_by_user_id uuid not null
* created_at timestamptz not null default now()
* ended_at timestamptz null
* active_anchor_type text not null
* active_anchor_id uuid not null
* extracted_entities jsonb not null default '{}'
* temporal_bias text not null

Indexes:

* (tenant_id, created_at)
* (tenant_id, ended_at)

Rules:

* Row is created on first artefact open from search
* ended_at is set only when returning to search bar home
* No updates after ended_at except audit linkage

---

### view_states

Represents in-memory navigation stack entries.

Columns:

* id uuid primary key
* situation_id uuid not null
* artefact_type text not null
* artefact_id uuid not null
* view_mode text not null
* created_at timestamptz not null default now()

Indexes:

* (situation_id, created_at)

Rules:

* Stored in memory or transient store only
* Must not be persisted across refresh
* Optional persistence allowed only for debugging in non-prod

---

### explicit_relations

Represents user-added, deterministic relations between artefacts.

Columns:

* id uuid primary key
* tenant_id uuid not null
* created_by_user_id uuid not null
* from_artefact_type text not null
* from_artefact_id uuid not null
* to_artefact_type text not null
* to_artefact_id uuid not null
* created_at timestamptz not null default now()

Indexes:

* (tenant_id, from_artefact_type, from_artefact_id)
* (tenant_id, to_artefact_type, to_artefact_id)

Rules:

* Relations are directional
* No implicit inverse relation is created
* Deletion is forbidden
* Visibility governed by RBAC at query time

---

### audit_events

Immutable ledger of explicit user actions.

Columns:

* id uuid primary key
* tenant_id uuid not null
* user_id uuid not null
* event_name text not null
* payload jsonb not null
* occurred_at timestamptz not null default now()

Indexes:

* (tenant_id, occurred_at)
* (tenant_id, event_name)

Rules:

* Append-only
* No updates or deletes
* Used for audit, insurance, and compliance only

---

## Artefact Tables (Existing)

The following artefact tables are assumed to already exist and are queried read-only:

* documents
* manual_sections
* inventory_items
* work_orders
* shopping_list_items
* history_events
* handovers

Requirements:

* Each artefact table must expose:

  * id uuid
  * tenant_id uuid
  * title or display_name
  * department or RBAC scope

---

## Permission Model Assumptions

* All artefact queries must be permission-filtered
* Permission logic must live server-side
* Related expansion must reuse existing permission checks

---

## Prohibited Persistence

* Navigation stack must not be persisted
* Related view usage must not be stored
* Situation state must not survive refresh

---

## Success Conditions

* Schema supports deterministic Related expansion
* Audit trail is legally defensible
* No implicit or inferred data is stored

---

## Failure Conditions

* Relations inferred without user action
* Navigation state persisted across sessions
* Audit polluted with UI noise
