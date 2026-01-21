# ADR-002-domain-first-grouping.md

Decision: Group Related results by domain first, not by relevance, confidence, or score.

Status: Accepted.

Context:
Users operate under situational pressure and think in terms of artefact types, not abstract relevance. Grouping by domain mirrors how crew reason about problems: inventory, work orders, manuals, history. Relevance-based grouping introduces opacity and forces users to infer why items appear where they do.

Decision:
Related results will be grouped strictly by domain:

* Inventory
* Work Orders
* Manuals/Documents
* History
* Other supported artefact domains

The order of domains is fixed and deterministic.
Items within each domain are rendered in the order returned by the backend.

No relevance scores are exposed.
No confidence indicators are shown.
No cross-domain ranking is performed.

Consequences:

* Users immediately understand what they are looking at.
* Absence of a domain is meaningful and calm.
* Partial results do not feel degraded.
* Backend logic remains simple and explainable.

Alternatives Considered:

* Global relevance ranking: rejected due to opacity.
* Confidence-weighted grouping: rejected due to implied intelligence.
* Dynamic domain ordering: rejected due to unpredictability.

Enforcement:
Any change that introduces relevance-based ordering, confidence signals, or dynamic domain ordering in Related expansion constitutes a regression.
