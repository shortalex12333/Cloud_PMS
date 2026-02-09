# Engineering Brief: Async Connection Pooling

## 1. Objective

To implement a robust, asynchronous connection pooling mechanism that can handle the high-concurrency requirements of the new "Fan-Out/Fan-In" search architecture. This is a foundational requirement for Phase 2 and is critical for the stability and performance of the entire search pipeline.

## 2. The Problem: Why the Current Approach is Insufficient

The current `capability_executor.py` uses the standard `supabase-py` client for database operations. This client is suitable for simple, sequential requests but is not designed for our target architecture for two main reasons:

1.  **Lack of Async Support:** The client's methods are synchronous (`.execute()`). While they can be wrapped in `asyncio.to_thread`, this is inefficient and does not provide the full benefits of a native async driver.
2.  **No Connection Pooling:** Each request to the database has the overhead of establishing a new connection. In a fan-out model where we may execute 4+ queries concurrently for a single user request, this will quickly exhaust the available connections on the Supabase (Postgres) instance, leading to errors and poor performance.

## 3. The Solution: `asyncpg`

We will integrate `asyncpg`, a high-performance, async-native PostgreSQL driver for Python.

### 3.1. Architectural Changes

1.  **Introduce a Connection Pool Manager:**
    *   Create a new utility module, e.g., `database/connection_manager.py`.
    *   This module will be responsible for creating and managing a global `asyncpg` connection pool.
    *   It should be implemented as a singleton or a memoized function to ensure only one pool is created per application instance.

2.  **Refactor `CapabilityExecutor`:**
    *   The `CapabilityExecutor` will be refactored to be fully `async`. The `execute` method will become `async def execute(...)`.
    *   Instead of being initialized with a `supabase_client`, it will acquire a connection from the `asyncpg` pool for each execution.
    *   It will use the `async with pool.acquire() as connection:` pattern to ensure connections are properly released back to the pool, even if errors occur.
    *   All database queries will be rewritten using `asyncpg`'s methods (e.g., `connection.fetch`, `connection.execute`).

3.  **Deprecate `supabase-py` for Data Queries:**
    *   The `supabase-py` client should no longer be used for data-intensive queries within the search pipeline.
    *   It can still be used for other purposes like authentication or storage if necessary, but the `execute` layer must use `asyncpg`.

### 3.2. Example Implementation (`database/connection_manager.py`)

```python
import asyncpg
import os

POOL = None

async def get_db_pool():
    global POOL
    if POOL is None:
        POOL = await asyncpg.create_pool(
            dsn=os.environ.get("SUPABASE_POSTGRES_DSN"),
            min_size=5,  # Sensible defaults
            max_size=20,
            # Add other pool configuration as needed
        )
    return POOL
```

### 3.3. Example Usage (`capability_executor.py`)

```python
from database.connection_manager import get_db_pool

class CapabilityExecutor:
    # ... (no client in __init__)

    async def execute(self, ...):
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                # All queries must be parameterized to prevent SQL injection
                rows = await connection.fetch(
                    "SELECT * FROM parts WHERE yacht_id = $1 AND name ILIKE $2",
                    self.yacht_id,
                    f"%{search_term}%"
                )
                # ...
```

## 4. Benefits

*   **Performance:** Reusing connections eliminates the overhead of establishing new connections for each query.
*   **Stability:** Prevents connection pool exhaustion and ensures the application can handle high load.
*   **True Asynchronicity:** Enables the entire search pipeline to be non-blocking, which is essential for meeting our latency budget.

This change is a prerequisite for the successful implementation of the fan-out architecture. It is a critical step in building a robust and scalable search system.
