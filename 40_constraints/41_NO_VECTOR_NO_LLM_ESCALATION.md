# 41_NO_VECTOR_NO_LLM_ESCALATION.md

Vector search and large language models are explicitly excluded from Related expansion in MVP.

This document defines the allowed escalation path when deterministic filters return no results.

## Absolute Prohibitions

* No vector embeddings may be generated.
* No semantic similarity may be computed.
* No LLMs may be invoked.
* No probabilistic matching may be introduced.

These prohibitions apply to both backend and frontend.

## Definition of Filter Failure

Filter failure occurs when:

* All allowed domains return zero related artefacts
* No explicit user-added relations exist
* The anchor artefact is valid and accessible

Filter failure does not constitute an error.

## Escalation Behavior

When filter failure occurs:

* Related returns an empty response.
* No retries are performed.
* No alternative matching strategies are attempted.
* No fallback domains are injected.

## User-Controlled Recovery

* The UI may expose an Add Related control.
* Recovery is entirely user-driven.
* Recovery actions are explicit and auditable.

## Future Extension Path

If deterministic filters are insufficient in future versions:

* New explicit relation tables may be introduced.
* New deterministic mappings may be added.
* Escalation must never default to embeddings or LLMs.

Any future change must be captured as an architecture decision record.

## Prohibited Behavior

* Silent fallback to semantic matching.
* Automatic broadening of scope.
* Implicit recovery attempts.

## Success Conditions

* Empty Related states are calm and intentional.
* No hidden intelligence is introduced.

## Failure Conditions

* Any semantic system is invoked.
* Filter failure triggers background processes.
* Results appear without explainable linkage.
