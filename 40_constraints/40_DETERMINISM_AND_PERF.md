# 40_DETERMINISM_AND_PERF.md

Determinism and performance are mandatory properties of the Related expansion system.

Behavior must be predictable, explainable, and bounded.

## Determinism Rules

* Given the same situation state, Related must return the same results.
* Results must not vary based on user behavior history.
* Results must not vary based on system load.
* Results must not vary based on time, except for temporal bias within domains.

## Query Constraints

* Related queries must use deterministic filters only.
* Allowed mechanisms:

  * Foreign key joins
  * Explicit relation tables
  * Entity-to-artefact mappings
* Disallowed mechanisms:

  * Full-text search
  * Fuzzy matching
  * Semantic similarity
  * Heuristic scoring

## Performance Targets

* Related expansion must be fast enough to feel instantaneous.
* Latency must be bounded and predictable.
* Queries must scale linearly with artefact count.

## Caching Rules

* In-memory caching may be used per situation.
* Cached data must be discarded when the situation ends.
* Cached data must not persist across refresh.

## Resource Limits

* Related expansion must not allocate unbounded memory.
* Related expansion must not generate background tasks.
* Related expansion must not enqueue async jobs.

## Prohibited Behavior

* Dynamic query generation based on user interaction.
* Adaptive ranking based on prior Related usage.
* Background prefetching of related artefacts.

## Success Conditions

* Related expansion is consistently fast.
* Results are repeatable and explainable.

## Failure Conditions

* Latency spikes under normal load.
* Results change without state change.
* System behavior becomes non-deterministic.
