# Engineering Brief: Initial Scoring & Ranking Model

## 1. Objective

To define and implement a simple, transparent, and effective baseline scoring model within `execute/result_ranker.py`. This model will serve as the "Fan-In" point for the new architecture, responsible for ranking the results from the parallel domain searches before they are passed to the `PrepareModule`.

## 2. The Role of `ResultRanker`

The `ResultRanker` is the component that makes sense of the federated search results. It receives a heterogeneous list of results from multiple domains (Parts, Manuals, Work Orders, etc.) and must rank them in a way that is relevant to the user's query.

For our initial implementation, we will use a simple, weighted scoring algorithm. This will provide a solid foundation that we can build upon in Phase 3.

## 3. The Initial Scoring Algorithm

The final score for each result will be a product of three components: `MatchScore`, `SourceScore`, and `DomainWeight`.

**`FinalScore = MatchScore * SourceScore * DomainWeight`**

### 3.1. `MatchScore` (How good is the match?)

This score reflects the quality of the match within the database. It will be determined by the `MatchType` defined in the capability.

| MatchType       | Score | Rationale                                         |
|-----------------|-------|---------------------------------------------------|
| `EXACT`         | 1.0   | The highest quality match.                        |
| `ILIKE`         | 0.8   | A good, but less precise, pattern match.          |
| `TRIGRAM`       | 0.7   | A fuzzy match, less precise than `ILIKE`.         |
| `VECTOR`        | (variable) | The cosine similarity returned by `pg_vector`. This will be a float between 0.0 and 1.0. |

### 3.2. `SourceScore` (How good is the source of the information?)

This is a simple weighting based on the source of the data. For now, this is a placeholder for more complex scoring, but it allows us to differentiate between, for example, a structured database row and an unstructured document.

| Source          | Score |
|-----------------|-------|
| `SQL`           | 1.0   |
| `RPC`           | 0.9   |
| `RAG` (Vector)  | 0.8   |

### 3.3. `DomainWeight` (How important is this domain?)

This is a configurable weight that allows us to boost results from certain domains. For example, we might decide that `parts` are generally more important than `manuals`. These weights will be defined in a configuration file (e.g., `execute/ranking_config.py`).

**Example `ranking_config.py`:**
```python
DOMAIN_WEIGHTS = {
    "parts": 1.0,
    "inventory": 0.9,
    "work_orders": 0.8,
    "manuals": 0.7,
    "default": 0.5, # For any domain not explicitly listed
}
```

## 4. Implementation in `result_ranker.py`

The `ResultRanker` will have a method, e.g., `rank_results(results: List[QueryResult])`, that performs the following steps:

1.  **Iterate through each `QueryResult`** from the fan-out.
2.  **For each row in the `QueryResult`**, calculate the `FinalScore` using the algorithm above. The necessary information (`MatchType`, `Source`, `Domain`) should be attached to the results by the `CapabilityExecutor`.
3.  **Store the score** in a new `_score` field within each result row.
4.  **Sort the combined list of all rows** from all `QueryResult` objects in descending order based on the `_score`.
5.  **Return the sorted list.**

## 5. Future Enhancements (Phase 3)

This simple model is designed to be extensible. In Phase 3, we will enhance it by:

*   **Incorporating `UserRole`:** Boosting the score of results that are more relevant to the user's role (e.g., a `Chief Engineer` is more likely to be interested in `work_orders` than a `Stewardess`).
*   **Reciprocal Rank Fusion (RRF):** Implementing a more advanced fusion algorithm to better combine results from different domains.
*   **Dynamic Weighting:** Adjusting the `DomainWeight` based on the entities extracted from the query.

This initial scoring model provides a solid, understandable foundation for the "Fan-In" part of our new architecture. It is a critical step towards delivering more relevant and accurate search results.
