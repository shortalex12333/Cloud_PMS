# 21_VIEW_STATE_MACHINE.md

The view state machine defines how artefact views and related expansion are traversed within a situation.

View state governs navigation only. It does not govern data mutation or audit truth.

## View State Definition

A view state represents a single artefact viewer or related expansion view.

Each view state contains:

* view_state_id (uuid)
* situation_id (uuid)
* artefact_type (enum)
* artefact_id (uuid)
* view_mode (enum: viewer, related)
* created_at (timestamp)

## Navigation Model

Navigation operates as a linear stack.

Only one stack exists per situation.

The stack supports:

* push (open new artefact or related view)
* pop (Back)
* forward (Forward)

No branching is permitted.

## Allowed View States

* viewer
  Displays a single artefact as the active anchor.

* related
  Displays related artefacts scoped to the current anchor.

## State Transitions

Allowed transitions:

* viewer → related
* related → viewer
* viewer → viewer (anchor replacement)
* related → related (via Forward only)

Forbidden transitions:

* related → search
* viewer → search (except via explicit return to search bar home)
* related → mutation
* any → query replay

## Back Navigation Rules

* Back pops the current view state.
* Back restores the immediately prior view state.
* Back continues until the search bar home is reached.
* When the search bar home is reached, the situation ends.

## Forward Navigation Rules

* Forward is available only if a prior Back occurred.
* Forward replays the next view state without re-query.
* Forward is cleared when a new view state is pushed.

## Stack Constraints

* Maximum stack size is nine view states.
* When the limit is exceeded, the oldest view state is discarded silently.
* Stack truncation is not visible to the user.

## Database Assumptions

Table: view_states

Columns:

* id uuid primary key
* situation_id uuid not null
* artefact_type text not null
* artefact_id uuid not null
* view_mode text not null
* created_at timestamptz not null default now()

Indexes:

* (situation_id, created_at)

## Prohibited Behavior

* Multiple stacks per situation.
* Persisting stack state beyond situation lifetime.
* Restoring view state after browser refresh.

## Success Conditions

* Back and Forward behave predictably.
* Artefact history is preserved during navigation.
* No context loss occurs within a situation.

## Failure Conditions

* Navigation skips artefacts.
* Forward triggers data fetching.
* Stack becomes inconsistent or branched.
