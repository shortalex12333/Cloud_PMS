# ADR-003-linear-back-forward-stack.md

Decision: Use a single linear back/forward navigation stack within a situation.

Status: Accepted.

Context:
Crew work involves sequential investigation. Non-linear navigation models, breadcrumbs, or branching stacks introduce cognitive overhead and break continuity. A linear stack mirrors how users retrace steps during troubleshooting and audits.

Decision:
Navigation within a situation will use a single linear stack:

* Back returns to the immediately prior view state.
* Forward returns to the immediately next view state.
* No branching, forks, or multiple stacks exist.
* Navigation never jumps directly to search results.

Returning to the search bar home terminates the situation and destroys the stack.

Consequences:

* Navigation is predictable under stress.
* Users can safely explore without losing context.
* State management remains simple and robust.

Alternatives Considered:

* Breadcrumb navigation: rejected due to query coupling.
* Tree-based navigation: rejected due to complexity.
* Domain-specific stacks: rejected due to inconsistency.

Enforcement:
Any introduction of multiple stacks, breadcrumb trails, or non-linear navigation within a situation constitutes a regression.
