# ADR-004-user_added_relations_active_flagged.md

Decision: User-added relations are immediately active but visually neutral and explicitly attributable.

Status: Accepted.

Context:
When deterministic relations do not exist, users must be able to assert truth. However, user-added relations must not be mistaken for system-inferred intelligence or silently influence unrelated behavior.

Decision:
User-added relations:

* Become immediately active in Related expansion.
* Are treated as deterministic relations.
* Are scoped to tenant and permission rules.
* Are visually neutral with an explicit user-added indicator.
* Are attributed to the creating user in audit records.

User-added relations do not:

* Affect ranking or ordering.
* Create implicit inverse relations.
* Propagate beyond explicit usage.
* Train or influence any intelligence system.

Consequences:

* Users can correct gaps without waiting.
* System remains explainable and accountable.
* No hidden learning occurs.

Alternatives Considered:

* Pending approval state: rejected due to friction.
* Delayed activation: rejected due to usability loss.
* Silent activation without attribution: rejected due to trust risk.

Enforcement:
Any change that obscures attribution, delays activation, or allows user-added relations to influence unrelated behavior constitutes a regression.
