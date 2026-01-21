# ADR-001-no-vector-no-llm.md

Decision: Exclude vector search and large language models from Related expansion in MVP.

Status: Accepted.

Context:
Related expansion must operate under pressure, during audits, and in legally sensitive situations. Any non-deterministic system introduces explainability risk, unpredictable behavior, and trust erosion. Vector search and LLMs are probabilistic by nature and cannot guarantee repeatable outputs for the same inputs.

Decision:
Related expansion will use deterministic mechanisms only:

* Explicit foreign key relations
* Explicit user-added relations
* Deterministic entity-to-artefact mappings
* Permission-filtered joins

No embeddings will be generated.
No semantic similarity will be computed.
No LLM calls will be made.

Consequences:

* Related results are fully explainable.
* Results are repeatable for the same situation state.
* Empty results are possible and acceptable.
* Coverage may be lower than probabilistic systems, but trust is preserved.

Alternatives Considered:

* Vector similarity search: rejected due to non-determinism.
* LLM-based suggestion: rejected due to hallucination risk and audit indefensibility.
* Hybrid fallback: rejected due to hidden escalation paths.

Enforcement:
Any introduction of embeddings, semantic similarity, or LLM calls in Related expansion constitutes a regression and must be rejected.
