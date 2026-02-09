# Celeste Search: Architectural Principles for the Modern Pipeline

## 1. Preamble: From Failure to Federated

The "Failures Document Analysis" confirms what we suspected: the legacy, sequential pipeline is brittle and cannot handle the ambiguity inherent in user queries. Entity conflicts, precedence ordering issues, and cross-lens contamination are not bugs to be fixed one by one; they are symptoms of a flawed architectural premise.

This document codifies the principles of the new **Federated Search Architecture**. This is our strategic blueprint for building a system that is robust, scalable, and delivers highly relevant results. These principles are not suggestions; they are the mandate for all future development.

## 2. The Core Mandate: From Assumptive to Federated

*   **The Old Way (Assumptive):** `Query -> Guess Intent -> Execute One Path -> Hope For The Best`
*   **The New Way (Federated):** `Query -> Generate All Possible Signals -> Fan-Out to All Relevant Domains -> Rank & Fuse Results`

Our system will no longer guess. It will search, then rank.

## 3. Pillar 1: The Fan-Out/Fan-In Framework (The "How")

This is the central nervous system of our new architecture.

### Principle: Embrace Ambiguity, Federate the Search

We will never assume user intent. When a query contains a term like "pending", which the failure analysis shows can be either an `approval_status` or a `work_order_status`, we will not try to pick a winner upfront.

Instead, we **Fan-Out** to all possible domains. We will search for "pending" in Shopping Lists, Work Orders, and any other relevant domain simultaneously. The results will then compete based on their merit.

**Execution:** `ENGINEERING_BRIEF_FAN_OUT_ORCHESTRATION.md`

### Principle: The "Capability Composer" is the Router

The mapping from an extracted entity to a domain search is the job of the `CapabilityComposer`. This component will be the simple, declarative "router" that kicks off the fan-out. It translates signals into actions.

**Execution:** `ENGINEERING_BRIEF_FAN_OUT_ORCHESTRATION.md`

### Principle: The "ResultRanker" is the Judge

The `ResultRanker` is the "Fan-In" point. It gathers the parallel results and applies a scoring algorithm to determine the final, unified ranking. This is where the "winning" interpretation of a query emerges.

**The Scoring Formula:**
`Score = (MatchScore * 1.0) + (SemanticScore * 0.8) + (RoleBias * 0.5) + (Recency * 0.3)`

*   **`MatchScore`:** Reflects the quality of the match (e.g., `EXACT` > `ILIKE` > `TRIGRAM`).
*   **`SemanticScore`:** The cosine similarity from `pgvector`.
*   **`RoleBias`:** A multiplier based on the user's role (e.g., boost Work Orders by 20% for a Chief Engineer).
*   **`Recency`:** A decay function based on the age of the result.

**Execution:** `ENGINEERING_BRIEF_SCORING_MODEL.md`

## 4. Pillar 2: The Technology Stack (The "What")

### The Async Backbone

*   **Non-Blocking by Default:** All I/O, from extraction to search, will be `async/await`.
*   **Robust Connection Pooling:** We will use `asyncpg` to manage a pool of database connections, preventing the exhaustion that a high-concurrency fan-out would otherwise cause.
*   **Edge Caching:** High-frequency, low-cardinality entities (e.g., from the gazetteer) will be cached in memory (Redis) to meet our latency targets.

**Execution:** `ENGINEERING_BRIEF_CONNECTION_POOLING.md`

### The Hybrid Search Cascade

This tiered strategy ensures we use the most efficient tool for the job.

*   **Tier 1: Exact & Trigram (`<10ms`):** `B-Tree` indexes for IDs (`WO-12345`) and `pg_trgm` for fast, fuzzy text matching (`'Caterpiller' % 'Caterpillar'`). This directly addresses the fuzzy matching gaps identified in the analysis.
*   **Tier 2: Full-Text Search (`~20-50ms`):** `tsvector` for descriptive, multi-word queries ("fuel pump assembly").
*   **Tier 3: Semantic Search (`~200ms`):** `pgvector` for abstract, "what do you mean" queries ("engine overheating issues"). This is the fallback, not the default.

### The Logic & Data Layers

*   **Extraction is Signal Generation:** The `RegexExtractor` is lens-agnostic. It finds all potential signals and passes them downstream. It makes no decisions. **Execution:** `ENGINEERING_BRIEF_REGEX_REFACTOR.md`
*   **Security Belongs in the Database:** All data access control will be handled by Postgres Row Level Security (RLS). Python code will **never** contain logic like `if user.role == 'X': return filter(data, ...)`. The application passes the `auth.uid()` to the database, and the database enforces the security policy.

## 5. Pillar 3: Quality & User Experience (The "Why")

### Quality & Performance are Non-Negotiable

*   **CI/CD for All Lenses:** The test suites for every lens must pass on every PR. No exceptions.
*   **Hard Latency Budgets:**
    *   **Extraction:** `<150ms` (Regex), `<3s` (AI)
    *   **Search Fan-Out (P95):** `<500ms`
    *   **Total Request (P95):** `<800ms`

### The User Experience is the Ultimate Arbiter

*   **Fast Path (Explicit Intent):** If a query contains a high-confidence, unambiguous signal (e.g., "Add X to Handover"), we bypass the search mesh and render the Microaction Button immediately.
*   **Slow Path (Implicit Discovery):** For broad queries ("Main Engine"), we show the ranked, federated feed of results. The user can then "deep link" into a specific result (e.g., open a manual), which may trigger secondary actions.

## 6. How This Solves Our Systemic Failures

| Failure from Analysis                                       | New Principle That Solves It                                                              |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Cross-lens entity conflicts (`pending`, `critical`)         | **Embrace Ambiguity, Federate the Search:** Both domains are searched; `ResultRanker` decides the winner. |
| Pattern precedence order issues (`work_order_id` vs `part_number`) | **Fan-Out/Fan-In:** Precedence is irrelevant. All capabilities are executed. The result with the better `MatchScore` wins. |
| Gaps in `type_precedence` config                            | **Federated Search:** `type_precedence` becomes less critical as we are not making a single choice upfront. |
| Fuzzy matching inconsistencies (`Caterpiller`)                | **Hybrid Search Cascade (Tier 1):** `pg_trgm` provides fuzzy matching at the database layer, acting as a safety net. |
| Single-entity extraction limitation on compound queries     | **Extraction is Signal Generation:** The refactored extractor will return ALL entities, not just the "first" or "best" one. |

This is our path forward. This is how we build a search system that is not just better, but fundamentally different and superior to the one we have today.
