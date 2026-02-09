# Celeste Search Pipeline Modernization: 3-Phase Execution Plan

## 1. Architectural Critique & Risk Assessment

### 1.1. Flaws & Bottlenecks

*   **Connection Pool Exhaustion:** The async fan-out to 4+ domains risks overwhelming the Supabase connection pool.
    *   **Mitigation:** Implement a robust connection pooling strategy (e.g., using `asyncpg`'s built-in pool) and configure it with sensible limits.
*   **"Noisy Neighbor" Problem:** A slow-running query in one domain can degrade the overall performance of the search.
    *   **Mitigation:** Implement strict timeouts for each domain search within the `asyncio.gather` call. Consider a circuit breaker pattern to temporarily disable a consistently slow domain.
*   **Scoring & Ranking Complexity:** The fusion of `TextMatch`, `VectorDistance`, and `UserRole` is non-trivial. A naive implementation will lead to irrelevant results.
    *   **Mitigation:** Start with a simple, configurable scoring model. We will iterate on this in Phase 3.
*   **Error Handling in Fan-Out:** Failures in one domain search should not cause the entire request to fail.
    *   **Mitigation:** The `PrepareModule` must be designed to handle partial failures gracefully, returning results from the successful domains.

### 1.2. Security Gaps

*   **RLS Complexity in Federated Search:** Propagating user context for RLS across parallel queries is a critical security requirement.
    *   **Mitigation:** The user's security context must be explicitly passed to each domain search. We will need to design a secure, tamper-proof way to do this.
*   **SQL Injection in Dynamic Queries:** `execute/sql_generator.py` is a high-risk component.
    *   **Mitigation:** A thorough audit of this file is required. All queries must be parameterized. We should also consider using a query builder library that enforces this.
*   **Denial of Service (DoS):** Malicious queries could trigger expensive fan-out searches.
    *   **Mitigation:** Implement query cost analysis and rate limiting at the `pipeline_gateway` level.

## 2. The 3-Phase Execution Plan

### Phase 1: Signal Purity & Foundational Stability

*   **Goal:** Decouple extraction from decision-making. The extraction layer should only generate signals (entities), not infer intent.
*   **Key Tasks:**
    1.  **Refactor `regex_extractor.py`:** Remove all "assumptive" logic. The output should be a clean list of extracted entities with their types and positions.
    2.  **API Contract Definition:** Create a formal API contract (`EXTRACTION_API.md`) defining the data structure passed from the `extraction` layer to the `orchestration` layer.
    3.  **Connection Pooling:** Implement a robust connection pooling mechanism for all database interactions in the `execute` layer.
    4.  **Initial Scoring Model:** Implement a simple, baseline scoring model in `result_ranker.py`. This can be a simple weighted average to start.

### Phase 2: Async Implementation & The "PrepareModule"

*   **Goal:** Implement the async fan-out architecture and the core logic of the `PrepareModule`.
*   **Key Tasks:**
    1.  **Async Fan-Out:** Implement the `asyncio.gather` logic in `orchestration/prepare_module.py` to concurrently call the domain handlers.
    2.  **Timeouts & Error Handling:** Implement timeouts and graceful error handling for each domain search.
    3.  **Capability Composer:** Build out `orchestration/prepare/capability_composer.py` to map extracted entities to the appropriate domain searches (capabilities).
    4.  **Fan-In Aggregation:** In `result_ranker.py`, implement the logic to aggregate results from the different domains.

### Phase 3: RLS, Contextual Ranking & Optimization

*   **Goal:** Implement advanced security and ranking features, and optimize for performance.
*   **Key Tasks:**
    1.  **RLS Integration:** Securely pass the user context to all database queries to enforce Row Level Security.
    2.  **Contextual Ranking:** Refine the scoring algorithm in `result_ranker.py` to incorporate `UserRole` and other contextual signals.
    3.  **Performance Optimization:** Benchmark the entire pipeline and optimize to consistently meet the `< 500ms` latency budget.
    4.  **Security Hardening:** Implement rate limiting and query cost analysis. Conduct a security audit of the entire pipeline.

