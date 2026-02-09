# Engineering Brief: Fan-Out Orchestration & The Capability Composer

## 1. Objective

To refactor the orchestration layer from its current "assumptive" linear model to a robust, parallel "Fan-Out/Fan-In" architecture. This involves deprecating the existing `PrepareModule` logic and introducing a new `CapabilityComposer` responsible for generating the fan-out plan.

## 2. The New Architecture: From "Prepare" to "Compose"

The core principle of the new architecture is to **search first, ask questions later**. We will not try to guess the user's intent upfront. Instead, we will fan-out to all relevant domains based on the extracted entities and then rank the combined results.

### 2.1. Deprecation of the Old `PrepareModule` Logic

The existing `prepare_module.py` is built around the concept of a `TermClassifier` that decides on a `RetrievalPath` (`SQL_ONLY`, `VECTOR_ONLY`, `HYBRID`). This entire paradigm will be removed.

*   **To Be Removed:**
    *   The `TermClassifier` and all its related logic.
    *   The `_prepare_sql_only`, `_prepare_vector_only`, and `_prepare_hybrid` methods.
    *   The concept of a single `RetrievalPath`.

### 2.2. The New `CapabilityComposer`

The "brains" of the new fan-out model will be a new component: `orchestration/capability_composer.py`.

*   **Responsibility:** The `CapabilityComposer`'s sole job is to take the list of `Entity` objects from the extraction layer and compose a list of all possible `capabilities` (domain searches) that can be executed.

*   **Implementation:**
    1.  **Entity-to-Capability Mapping:** The composer will contain a simple, clear mapping of `entity_type` to a list of `capability_name`s. This mapping defines which domains are relevant for which types of entities.

        **Example (`capability_mapping.py`):**
        ```python
        CAPABILITY_MAP = {
            "part_number": ["part_by_part_number", "inventory_by_part_number"],
            "model": ["equipment_by_model", "part_by_model"],
            "location_on_board": ["inventory_by_location", "work_order_by_location"],
            "fault_code": ["fault_by_fault_code", "work_order_by_fault"],
            # A generic "text" entity will trigger broad searches
            "text": ["part_by_name", "work_order_by_title", "manual_by_content"],
        }
        ```

    2.  **`compose()` Method:** The composer will have a `compose(entities: List[Entity])` method that:
        *   Iterates through the input entities.
        *   For each entity, it looks up the corresponding capabilities in the `CAPABILITY_MAP`.
        *   It creates a de-duplicated list of `(capability_name, search_term)` tuples.
        *   It returns this list as the "Execution Plan".

### 2.3. The New Orchestration Flow

The top-level service (e.g., `pipeline_service.py`) will orchestrate the new flow:

1.  **Extraction:** Call the `extraction` layer to get a flat list of `Entity` objects.
2.  **Composition:** Pass the entities to the `CapabilityComposer` to get the list of `(capability_name, search_term)` tuples.
3.  **Execution (Fan-Out):** Create a list of `async` tasks, where each task is a call to `CapabilityExecutor.execute()` for each capability.
4.  **`asyncio.gather()`:** Execute all tasks concurrently using `asyncio.gather(*tasks, return_exceptions=True)`. This is the "Fan-Out". `return_exceptions=True` is critical for handling partial failures.
5.  **Ranking (Fan-In):** Pass the list of results (and any exceptions) to the `ResultRanker`.
6.  **Response:** The `ResultRanker` will return a single, sorted list of the best results, which is then passed to the final response generation layer.

## 3. Implementation Details

*   **Timeouts:** The `asyncio.gather` call should be wrapped in `asyncio.wait_for` to enforce a global timeout on the entire search process (e.g., 500ms), preventing a single slow domain from blocking the entire request.
*   **Error Handling:** The `return_exceptions=True` flag in `asyncio.gather` ensures that if one domain search fails, the others can still succeed. The `ResultRanker` must be able to handle these exceptions gracefully.
*   **The `text` Entity:** The `RegexExtractor` should be configured to also produce a generic `text` entity containing the cleaned, non-entity parts of the query. This will be used to trigger the broad, full-text search capabilities.

This refactoring represents the most significant architectural change in the project. It moves us from a fragile, linear pipeline to a robust, parallel one. It decouples the "what" (the extracted entities) from the "how" (the search execution), which will make the entire system more flexible, scalable, and resilient.
