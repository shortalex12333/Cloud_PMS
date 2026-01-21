# ex08A_situation_refresh_behavior.md

Scenario: User refreshes browser during an active situation

## Initial State

User has an active situation and is viewing an artefact.

Situation state exists in memory only.

## Step 1 — Browser Refresh

User refreshes the browser.

System behavior:

* In-memory navigation state is destroyed
* Situation state is destroyed
* No attempt is made to restore prior state

No ledger event emitted.

## Step 2 — Post-Refresh State

User is returned to search bar home.

No active situation exists.

No Forward navigation is available.

## Expected Outcomes

* System prioritizes safety and compliance over convenience.
* No state restoration occurs after refresh.
* No partial or stale state is reused.
* Ledger contains no ambiguous entries.

## Failure Conditions

* Partial situation is restored.
* Forward navigation remains available.
* UI attempts to reconstruct prior context.
