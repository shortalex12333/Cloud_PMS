# Prepare Module Refactor - Bulletproof Architecture

**Date**: 2026-01-30
**Status**: 🔵 ARCHITECTURAL DESIGN
**Goal**: Organize search capabilities with clear lens ownership, easy debugging, and zero merge conflicts

---

## Current Problems

### Problem 1: Monolithic Configuration
**File**: `apps/api/prepare/capability_composer.py` (lines 113-137)

```python
# ALL lenses crammed into one dictionary
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    "PART_NUMBER": ("part_by_part_number_or_name", "part_number"),      # Part Lens
    "CERTIFICATE_TYPE": ("certificate_by_type", "certificate_type"),     # Certificate Lens
    "CREW_NAME": ("crew_by_name", "full_name"),                          # Crew Lens
    "WORK_ORDER_ID": ("work_order_by_id", "wo_number"),                  # Work Order Lens
    # ... 50+ more entities
}
```

**Issues**:
- ❌ Multiple lenses editing same file → merge conflicts
- ❌ No clear ownership (who owns "PART_NUMBER"?)
- ❌ No validation (typos discovered at runtime)
- ❌ Hard to debug (which lens caused the error?)
- ❌ Can't disable a lens without breaking others

### Problem 2: Scattered Implementations
**Files**: `capability_composer.py` (lines 200-800)

```python
class CapabilityComposer:
    async def part_by_part_number_or_name(self, ...):  # Part Lens
        # ... 50 lines

    async def certificate_by_type(self, ...):           # Certificate Lens
        # ... 40 lines

    async def crew_by_name(self, ...):                  # Crew Lens
        # ... 35 lines

    # ... 30+ methods in one class
```

**Issues**:
- ❌ 800+ line class
- ❌ Part Lens worker must navigate Certificate/Crew code
- ❌ No isolation (bug in Part code breaks Certificate)
- ❌ Testing requires mocking entire class

### Problem 3: No Validation
**Runtime Errors Only**:

```python
# Typo in entity type - discovered when user searches
"PART_NUBMER": ("part_by_part_number_or_name", "part_number")  # Typo!

# Non-existent capability - crashes at runtime
"CERTIFICATE_TYPE": ("certificate_by_tpye", "certificate_type")  # Method doesn't exist!
```

**Issues**:
- ❌ No startup validation
- ❌ Users discover config errors
- ❌ No type safety

### Problem 4: Intent Extraction Disconnect
**File**: `apps/api/entity_extraction/extractor.py`

```python
# Entity types defined separately from capabilities
ENTITY_TYPES = ["PART_NUMBER", "CREW_NAME", "CERTIFICATE_TYPE", ...]

# No link to which lens owns which entity
# No link to which capabilities handle which entities
```

**Issues**:
- ❌ Entity extraction and prepare module are decoupled
- ❌ Can extract entities we can't search
- ❌ Can search entities we don't extract

---

## Design Principles

### 1. **Lens Ownership**
Each lens owns its:
- Entity type definitions
- Search capability implementations
- Validation schemas
- Test fixtures

**Rule**: Part Lens worker ONLY touches Part Lens files. Zero visibility into Certificate Lens code.

### 2. **Single Source of Truth**
Each lens has ONE canonical file:

```
apps/api/prepare/capabilities/part_capabilities.py
```

This file contains:
- Entity type enum
- Entity-to-capability mappings
- Capability implementations
- Input/output schemas

### 3. **Auto-Discovery Registry**
At startup, registry scans `capabilities/` directory and auto-registers all lenses.

**Benefits**:
- Adding new lens = drop file in folder
- Disabling lens = delete file or add `ENABLED = False`
- No manual registration

### 4. **Fail Fast Validation**
Validate ALL configurations at startup:

```python
# Server won't start if:
- Entity type typos exist
- Capability method missing
- Schema validation fails
- Duplicate entity types across lenses
```

### 5. **Traceable Errors**
Every error includes:
- Lens name
- File location
- Entity type
- Capability name

**Example**:
```
SearchCapabilityError: Part Lens (part_capabilities.py:127)
  Entity: PART_NUMBER
  Capability: part_by_part_number_or_name
  Error: Column 'part_nubmer' does not exist in table 'pms_parts'
  Fix: Check line 127 in apps/api/prepare/capabilities/part_capabilities.py
```

### 6. **Type Safety**
Use Pydantic models for all configs:

```python
class CapabilityMapping(BaseModel):
    entity_type: str
    capability_name: str
    table_name: str
    search_column: str
    result_type: str

    # Validates at definition time, not runtime
```

---

## Proposed Architecture

### File Structure

```
apps/api/
├── entity_extraction/
│   ├── extractor.py                    # Entity extraction (small tweaks)
│   └── entity_types/                   # NEW: Lens-specific entity types
│       ├── __init__.py
│       ├── part_entities.py            # Part Lens entity types
│       ├── certificate_entities.py     # Certificate Lens entity types
│       └── crew_entities.py            # Crew Lens entity types
│
├── prepare/
│   ├── capability_composer.py          # REFACTORED: Orchestrator only
│   ├── capability_registry.py          # NEW: Auto-discovery
│   ├── base_capability.py              # NEW: Base class + schemas
│   │
│   └── capabilities/                   # NEW: Lens-owned files
│       ├── __init__.py
│       ├── part_capabilities.py        # Part Lens OWNS
│       ├── certificate_capabilities.py # Certificate Lens OWNS
│       ├── crew_capabilities.py        # Crew Lens OWNS
│       ├── work_order_capabilities.py  # Work Order Lens OWNS
│       ├── document_capabilities.py    # Document Lens OWNS
│       ├── equipment_capabilities.py   # Equipment Lens OWNS
│       └── fault_capabilities.py       # Fault Lens OWNS
│
└── graphrag_query.py                   # TWEAKED: Use registry instead of hardcoded
```

### Component Responsibilities

#### 1. Base Capability Class
**File**: `apps/api/prepare/base_capability.py`

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Dict, Any

class CapabilityMapping(BaseModel):
    """Single entity-to-capability mapping."""
    entity_type: str           # e.g., "PART_NUMBER"
    capability_name: str       # e.g., "part_by_part_number_or_name"
    table_name: str           # e.g., "pms_parts"
    search_column: str        # e.g., "part_number"
    result_type: str          # e.g., "part"
    priority: int = 1         # Higher = ranked first in multi-lens results

class SearchResult(BaseModel):
    """Standardized search result."""
    id: str
    type: str                 # "part", "certificate", "crew", etc.
    title: str
    score: float
    metadata: Dict[str, Any]
    lens_name: str            # Which lens returned this

class BaseLensCapability(ABC):
    """Base class all lens capabilities must inherit."""

    @property
    @abstractmethod
    def lens_name(self) -> str:
        """Lens identifier (e.g., 'part_lens')."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether this lens is enabled."""
        return True

    @abstractmethod
    def get_entity_mappings(self) -> List[CapabilityMapping]:
        """Return all entity-to-capability mappings for this lens."""
        pass

    @abstractmethod
    async def execute_capability(
        self,
        capability_name: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """Execute a capability and return standardized results."""
        pass

    def validate(self) -> None:
        """Validate all mappings at startup (override if needed)."""
        mappings = self.get_entity_mappings()

        # Check for duplicate entity types within lens
        entity_types = [m.entity_type for m in mappings]
        if len(entity_types) != len(set(entity_types)):
            raise ValueError(f"{self.lens_name}: Duplicate entity types found")

        # Check all capabilities are implemented
        for mapping in mappings:
            if not hasattr(self, mapping.capability_name):
                raise ValueError(
                    f"{self.lens_name}: Capability '{mapping.capability_name}' "
                    f"not implemented for entity '{mapping.entity_type}'"
                )
```

#### 2. Part Lens Capability (Example)
**File**: `apps/api/prepare/capabilities/part_capabilities.py`

```python
from typing import List, Dict, Any
from ..base_capability import BaseLensCapability, CapabilityMapping, SearchResult

class PartLensCapability(BaseLensCapability):
    """Part Lens search capabilities."""

    lens_name = "part_lens"
    enabled = True

    def __init__(self, db_client):
        self.db = db_client

    def get_entity_mappings(self) -> List[CapabilityMapping]:
        """Define all Part Lens entity-to-capability mappings."""
        return [
            CapabilityMapping(
                entity_type="PART_NUMBER",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="part_number",
                result_type="part",
                priority=2,  # High priority for exact part number matches
            ),
            CapabilityMapping(
                entity_type="PART_NAME",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="name",
                result_type="part",
                priority=1,
            ),
            CapabilityMapping(
                entity_type="MANUFACTURER",
                capability_name="part_by_manufacturer",
                table_name="pms_parts",
                search_column="manufacturer",
                result_type="part",
                priority=1,
            ),
            CapabilityMapping(
                entity_type="STOCK_LOCATION",
                capability_name="inventory_by_location",
                table_name="pms_inventory_stock",
                search_column="storage_location",
                result_type="inventory_stock",
                priority=1,
            ),
            CapabilityMapping(
                entity_type="SHOPPING_LIST_ITEM",
                capability_name="shopping_list_by_part",
                table_name="pms_shopping_list_items",
                search_column="part_name",
                result_type="shopping_list_item",
                priority=1,
            ),
        ]

    async def execute_capability(
        self,
        capability_name: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """Route to the correct capability method."""
        method = getattr(self, capability_name, None)
        if not method:
            raise ValueError(
                f"Part Lens: Capability '{capability_name}' not found. "
                f"Check part_capabilities.py"
            )

        results = await method(yacht_id, search_term, limit)

        # Wrap in SearchResult models
        return [
            SearchResult(
                id=r["id"],
                type=r["type"],
                title=r["title"],
                score=r.get("score", 0.0),
                metadata=r.get("metadata", {}),
                lens_name=self.lens_name,
            )
            for r in results
        ]

    # ===== CAPABILITY IMPLEMENTATIONS =====

    async def part_by_part_number_or_name(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search parts by part number or name."""
        query = """
            SELECT
                id,
                'part' as type,
                CONCAT(part_number, ' - ', name) as title,
                similarity(CONCAT(part_number, ' ', name), %s) as score,
                jsonb_build_object(
                    'part_number', part_number,
                    'manufacturer', manufacturer,
                    'category', category,
                    'subcategory', subcategory
                ) as metadata
            FROM pms_parts
            WHERE yacht_id = %s
              AND (
                part_number ILIKE %s
                OR name ILIKE %s
                OR manufacturer ILIKE %s
              )
            ORDER BY score DESC, name ASC
            LIMIT %s
        """

        pattern = f"%{search_term}%"
        params = [search_term, yacht_id, pattern, pattern, pattern, limit]

        try:
            results = await self.db.fetch_all(query, params)
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: part_by_part_number_or_name failed. "
                f"Table: pms_parts, Column: part_number/name. "
                f"Error: {str(e)}"
            )

    async def part_by_manufacturer(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search parts by manufacturer."""
        query = """
            SELECT
                id,
                'part' as type,
                CONCAT(name, ' (', manufacturer, ')') as title,
                similarity(manufacturer, %s) as score,
                jsonb_build_object(
                    'part_number', part_number,
                    'manufacturer', manufacturer,
                    'category', category
                ) as metadata
            FROM pms_parts
            WHERE yacht_id = %s
              AND manufacturer ILIKE %s
            ORDER BY score DESC, manufacturer ASC, name ASC
            LIMIT %s
        """

        pattern = f"%{search_term}%"
        params = [search_term, yacht_id, pattern, limit]

        try:
            results = await self.db.fetch_all(query, params)
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: part_by_manufacturer failed. "
                f"Table: pms_parts, Column: manufacturer. "
                f"Error: {str(e)}"
            )

    async def inventory_by_location(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search inventory by storage location."""
        query = """
            SELECT
                s.id,
                'inventory_stock' as type,
                CONCAT(p.name, ' @ ', s.storage_location, ' (', s.on_hand, ' units)') as title,
                similarity(s.storage_location, %s) as score,
                jsonb_build_object(
                    'part_id', s.part_id,
                    'part_name', p.name,
                    'storage_location', s.storage_location,
                    'on_hand', s.on_hand,
                    'allocated', s.allocated,
                    'available', s.available
                ) as metadata
            FROM pms_inventory_stock s
            JOIN pms_parts p ON s.part_id = p.id
            WHERE s.yacht_id = %s
              AND s.storage_location ILIKE %s
            ORDER BY score DESC, s.storage_location ASC
            LIMIT %s
        """

        pattern = f"%{search_term}%"
        params = [search_term, yacht_id, pattern, limit]

        try:
            results = await self.db.fetch_all(query, params)
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: inventory_by_location failed. "
                f"Table: pms_inventory_stock, Column: storage_location. "
                f"Error: {str(e)}"
            )

    async def shopping_list_by_part(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search shopping list items."""
        query = """
            SELECT
                sl.id,
                'shopping_list_item' as type,
                CONCAT(p.name, ' - ', sl.status, ' (qty: ', sl.quantity_needed, ')') as title,
                similarity(p.name, %s) as score,
                jsonb_build_object(
                    'part_id', sl.part_id,
                    'part_name', p.name,
                    'quantity_needed', sl.quantity_needed,
                    'status', sl.status,
                    'priority', sl.priority
                ) as metadata
            FROM pms_shopping_list_items sl
            JOIN pms_parts p ON sl.part_id = p.id
            WHERE sl.yacht_id = %s
              AND p.name ILIKE %s
            ORDER BY score DESC, sl.priority DESC
            LIMIT %s
        """

        pattern = f"%{search_term}%"
        params = [search_term, yacht_id, pattern, limit]

        try:
            results = await self.db.fetch_all(query, params)
            return [dict(row) for row in results]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: shopping_list_by_part failed. "
                f"Table: pms_shopping_list_items. "
                f"Error: {str(e)}"
            )
```

#### 3. Capability Registry
**File**: `apps/api/prepare/capability_registry.py`

```python
from typing import Dict, List, Type
from .base_capability import BaseLensCapability, CapabilityMapping, SearchResult
import importlib
import pkgutil
from pathlib import Path

class CapabilityRegistry:
    """Auto-discovers and manages all lens capabilities."""

    def __init__(self, db_client):
        self.db = db_client
        self.lenses: Dict[str, BaseLensCapability] = {}
        self.entity_to_lens: Dict[str, str] = {}  # Entity type -> Lens name
        self.entity_mappings: Dict[str, CapabilityMapping] = {}

    def discover_and_register(self):
        """Auto-discover all lens capability files."""
        capabilities_path = Path(__file__).parent / "capabilities"

        # Import all modules in capabilities/
        for module_info in pkgutil.iter_modules([str(capabilities_path)]):
            if module_info.name == "__init__":
                continue

            module_path = f"apps.api.prepare.capabilities.{module_info.name}"
            module = importlib.import_module(module_path)

            # Find BaseLensCapability subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseLensCapability)
                    and attr is not BaseLensCapability
                ):
                    lens = attr(self.db)

                    # Skip if disabled
                    if not lens.enabled:
                        print(f"[Registry] Skipping disabled lens: {lens.lens_name}")
                        continue

                    # Validate lens
                    try:
                        lens.validate()
                    except Exception as e:
                        raise RuntimeError(
                            f"[Registry] Validation failed for {lens.lens_name} "
                            f"in {module_path}: {str(e)}"
                        )

                    # Register lens
                    self.lenses[lens.lens_name] = lens

                    # Register entity mappings
                    for mapping in lens.get_entity_mappings():
                        if mapping.entity_type in self.entity_to_lens:
                            existing_lens = self.entity_to_lens[mapping.entity_type]
                            raise ValueError(
                                f"[Registry] Duplicate entity type '{mapping.entity_type}' "
                                f"claimed by both {existing_lens} and {lens.lens_name}"
                            )

                        self.entity_to_lens[mapping.entity_type] = lens.lens_name
                        self.entity_mappings[mapping.entity_type] = mapping

                    print(f"[Registry] ✓ Registered: {lens.lens_name} "
                          f"({len(lens.get_entity_mappings())} entities)")

        print(f"[Registry] Total lenses: {len(self.lenses)}")
        print(f"[Registry] Total entity types: {len(self.entity_mappings)}")

    async def search(
        self,
        entity_type: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """Search using entity type."""
        if entity_type not in self.entity_to_lens:
            raise ValueError(
                f"[Registry] Unknown entity type: {entity_type}. "
                f"Available: {list(self.entity_to_lens.keys())}"
            )

        lens_name = self.entity_to_lens[entity_type]
        lens = self.lenses[lens_name]
        mapping = self.entity_mappings[entity_type]

        try:
            results = await lens.execute_capability(
                capability_name=mapping.capability_name,
                yacht_id=yacht_id,
                search_term=search_term,
                limit=limit
            )
            return results
        except Exception as e:
            raise RuntimeError(
                f"[Registry] Search failed for entity '{entity_type}' "
                f"in lens '{lens_name}': {str(e)}"
            )

    async def search_all_lenses(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 50
    ) -> List[SearchResult]:
        """Search across ALL lenses and return ranked results."""
        all_results = []

        for lens_name, lens in self.lenses.items():
            for mapping in lens.get_entity_mappings():
                try:
                    results = await lens.execute_capability(
                        capability_name=mapping.capability_name,
                        yacht_id=yacht_id,
                        search_term=search_term,
                        limit=10  # Get top 10 from each capability
                    )
                    all_results.extend(results)
                except Exception as e:
                    # Log error but continue with other lenses
                    print(
                        f"[Registry] Warning: {lens_name}.{mapping.capability_name} "
                        f"failed for '{search_term}': {str(e)}"
                    )
                    continue

        # Deduplicate by ID
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)

        # Sort by score (descending) and priority
        unique_results.sort(
            key=lambda r: (
                self.entity_mappings[self.entity_to_lens[r.type]].priority,
                r.score
            ),
            reverse=True
        )

        return unique_results[:limit]

    def get_entity_types_for_lens(self, lens_name: str) -> List[str]:
        """Get all entity types owned by a lens."""
        return [
            entity_type
            for entity_type, owner_lens in self.entity_to_lens.items()
            if owner_lens == lens_name
        ]

    def get_all_entity_types(self) -> List[str]:
        """Get all registered entity types across all lenses."""
        return list(self.entity_to_lens.keys())
```

#### 4. Refactored Capability Composer
**File**: `apps/api/prepare/capability_composer.py`

```python
from .capability_registry import CapabilityRegistry
from .base_capability import SearchResult
from typing import List

class CapabilityComposer:
    """
    Orchestrator for search capabilities.

    Delegates to CapabilityRegistry which auto-discovers lens capabilities.
    """

    def __init__(self, db_client):
        self.registry = CapabilityRegistry(db_client)
        self.registry.discover_and_register()

    async def search_by_entity(
        self,
        entity_type: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """Search using a specific entity type."""
        return await self.registry.search(
            entity_type=entity_type,
            yacht_id=yacht_id,
            search_term=search_term,
            limit=limit
        )

    async def comprehensive_search(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 50
    ) -> List[SearchResult]:
        """Search across ALL lenses."""
        return await self.registry.search_all_lenses(
            yacht_id=yacht_id,
            search_term=search_term,
            limit=limit
        )

    def get_supported_entity_types(self) -> List[str]:
        """Get all entity types supported by registered lenses."""
        return self.registry.get_all_entity_types()
```

#### 5. Entity Extraction Tweaks
**File**: `apps/api/entity_extraction/extractor.py`

```python
from apps.api.prepare.capability_registry import CapabilityRegistry

class EntityExtractor:
    def __init__(self, capability_registry: CapabilityRegistry):
        self.registry = capability_registry

        # Sync entity types from registry (single source of truth)
        self.supported_entity_types = self.registry.get_all_entity_types()

    def extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities from query."""
        entities = []

        # ... existing extraction logic ...

        # Validate extracted entities against registry
        for entity in entities:
            if entity["type"] not in self.supported_entity_types:
                # Log warning but don't fail
                print(f"[Extractor] Warning: Extracted unknown entity type: {entity['type']}")

        return entities
```

#### 6. SQL RAG Tweaks
**File**: `apps/api/graphrag_query.py`

```python
from apps.api.prepare.capability_composer import CapabilityComposer

class GraphRAGQuery:
    def __init__(self, db_client):
        self.composer = CapabilityComposer(db_client)

    async def execute_query(self, yacht_id: str, query: str, entities: List[Dict]):
        """Execute query using capability registry."""

        if not entities:
            # No entities extracted → comprehensive search
            results = await self.composer.comprehensive_search(
                yacht_id=yacht_id,
                search_term=query,
                limit=50
            )
        else:
            # Use entity-specific search
            all_results = []
            for entity in entities:
                try:
                    results = await self.composer.search_by_entity(
                        entity_type=entity["type"],
                        yacht_id=yacht_id,
                        search_term=entity["value"],
                        limit=20
                    )
                    all_results.extend(results)
                except Exception as e:
                    print(f"[GraphRAG] Entity search failed: {str(e)}")
                    continue

            results = all_results

        return self._format_results(results)
```

---

## Implementation Phases

### Phase 1: Foundation (2-3 hours)
**Goal**: Create base infrastructure

1. Create `base_capability.py` with:
   - `CapabilityMapping` Pydantic model
   - `SearchResult` Pydantic model
   - `BaseLensCapability` abstract class

2. Create `capability_registry.py` with:
   - Auto-discovery logic
   - Validation at startup
   - Error reporting

3. Test framework:
   ```bash
   pytest tests/unit/prepare/test_base_capability.py
   pytest tests/unit/prepare/test_registry.py
   ```

**Success Criteria**:
- ✅ Registry discovers capabilities
- ✅ Validation catches duplicates
- ✅ Clear error messages
- ✅ All tests pass

### Phase 2: Migrate Part Lens (3-4 hours)
**Goal**: Prove pattern works with real lens

1. Create `capabilities/part_capabilities.py`
2. Migrate Part Lens entity types + implementations
3. Test against existing E2E tests
4. Document pattern for other lens workers

**Success Criteria**:
- ✅ Part Lens search works
- ✅ E2E tests pass
- ✅ Zero changes to other lenses
- ✅ Clear error traces

### Phase 3: Parallel Lens Migration (1 week)
**Goal**: All lens teams migrate in parallel

Each lens team creates their `{lens_name}_capabilities.py`:
- Certificate Lens → `certificate_capabilities.py`
- Crew Lens → `crew_capabilities.py`
- Work Order Lens → `work_order_capabilities.py`
- Document Lens → `document_capabilities.py`
- Equipment Lens → `equipment_capabilities.py`
- Fault Lens → `fault_capabilities.py`

**Process**:
1. Copy `part_capabilities.py` as template
2. Update entity mappings from lens spec
3. Implement capability methods
4. Run validation: `python -m apps.api.prepare.capability_registry`
5. Submit PR (zero conflicts - each lens owns separate file)

**Success Criteria**:
- ✅ All lenses registered
- ✅ No merge conflicts
- ✅ Comprehensive search works
- ✅ Startup validation passes

### Phase 4: Update Dependent Modules (2-3 hours)
**Goal**: Integrate new registry into existing code

1. Update `capability_composer.py`:
   - Remove monolithic dict
   - Delegate to registry

2. Update `entity_extraction/extractor.py`:
   - Sync entity types from registry

3. Update `graphrag_query.py`:
   - Use registry for search
   - Add comprehensive search fallback

**Success Criteria**:
- ✅ All search endpoints work
- ✅ Entity extraction aligned
- ✅ SQL RAG uses registry

### Phase 5: Validation & Testing (2 hours)
**Goal**: Bulletproof with tests

1. Unit tests for each lens capability
2. Integration tests for registry
3. E2E tests for comprehensive search
4. Startup validation in CI/CD

**Success Criteria**:
- ✅ 100% test coverage on registry
- ✅ Each lens has unit tests
- ✅ CI fails if validation fails
- ✅ All E2E tests pass

---

## Migration Path

### Step 1: Create New Structure (Don't Break Old)
Add new files alongside old code:

```
apps/api/prepare/
├── capability_composer.py      # Keep existing (mark deprecated)
├── base_capability.py          # NEW
├── capability_registry.py      # NEW
└── capabilities/               # NEW
    └── part_capabilities.py    # NEW
```

### Step 2: Feature Flag
Add environment variable:

```python
USE_CAPABILITY_REGISTRY = os.getenv("USE_CAPABILITY_REGISTRY", "false") == "true"

if USE_CAPABILITY_REGISTRY:
    composer = CapabilityComposer(db)  # New registry-based
else:
    composer = LegacyCapabilityComposer(db)  # Old monolithic
```

### Step 3: Gradual Rollout
1. Deploy with flag OFF (test in staging)
2. Enable flag for 10% traffic
3. Monitor errors, performance
4. Enable for 100% traffic
5. Remove old code

---

## Debugging Improvements

### Before (Cryptic)
```
Traceback (most recent call last):
  File "capability_composer.py", line 456
    results = await self.db.fetch_all(query, params)
psycopg2.errors.UndefinedColumn: column "part_nubmer" does not exist

# Where did this come from? Which lens? Which entity?
```

### After (Clear)
```
SearchCapabilityError: Part Lens capability failed
  File: apps/api/prepare/capabilities/part_capabilities.py
  Line: 127
  Lens: part_lens
  Entity Type: PART_NUMBER
  Capability: part_by_part_number_or_name
  Table: pms_parts
  Column: part_nubmer

Error: column "part_nubmer" does not exist

Fix: Check column name in part_capabilities.py:127
Spec: docs/pipeline/entity_lenses/part_lens/v2/part_lens_v2_FINAL.md (line 45)
```

### Startup Validation Output
```bash
$ python -m apps.api.main

[Registry] Discovering lens capabilities...
[Registry] ✓ Registered: part_lens (5 entities)
[Registry] ✓ Registered: certificate_lens (4 entities)
[Registry] ✓ Registered: crew_lens (6 entities)
[Registry] ✓ Registered: work_order_lens (3 entities)
[Registry] Skipping disabled lens: legacy_equipment_lens
[Registry] ✗ Validation failed: document_lens

DocumentLensError: Capability 'document_by_tpye' not implemented
  File: apps/api/prepare/capabilities/document_capabilities.py
  Entity: DOCUMENT_TYPE
  Expected method: document_by_tpye
  Available methods: document_by_type, document_by_category

Fix: Line 23 in document_capabilities.py has typo in capability_name
Change: "document_by_tpye" → "document_by_type"

Startup aborted. Fix errors and restart.
```

---

## Benefits Summary

### For Lens Workers
- ✅ **Isolation**: Only touch your lens file
- ✅ **Template**: Copy Part Lens as starting point
- ✅ **Validation**: Errors caught at startup, not production
- ✅ **Debugging**: Clear error messages with file/line
- ✅ **Testing**: Unit test your lens independently

### For System
- ✅ **Bulletproof**: Startup fails if config invalid
- ✅ **Organized**: Clear ownership structure
- ✅ **Scalable**: Drop new lens file, auto-discovered
- ✅ **Zero Conflicts**: Each lens = separate file
- ✅ **Comprehensive Search**: All lenses queried in parallel

### For Debugging
- ✅ **Traceable**: Errors show lens name, file, line
- ✅ **Validated**: Typos caught at startup
- ✅ **Documented**: Each lens file is self-documenting
- ✅ **Testable**: Mock individual lenses

---

## Next Steps

1. **Review Architecture**: Approve/modify this design
2. **Implement Phase 1**: Base classes + registry
3. **Migrate Part Lens**: Prove pattern works
4. **Distribute to Lens Teams**: Share template + instructions
5. **Parallel Migration**: All lenses migrate simultaneously
6. **Integrate + Test**: Update dependent modules
7. **Deploy**: Feature flag → gradual rollout → remove old code

**Estimated Timeline**: 2-3 weeks with all lens teams working in parallel

---

---

## Microaction Addition Module (Missing Piece)

### Problem

Current flow STOPS at search results. Missing: **Action suggestion layer**

**Current Flow**:
```
Entity Extraction → Prepare Module → SQL RAG → Results → Frontend
                                                 ↑
                                         STOPS HERE!
```

**Expected Flow** (from user feedback):
```
Entity Extraction → Prepare Module → SQL RAG → Microaction Addition → Frontend
                                                       ↑
                                              MISSING MODULE!
```

### What Microactions Do

**Purpose**: Add context-valid actions to search results based on:
- Entity type (part, certificate, crew, etc.)
- Entity state (stock level, expiry date, status)
- User role (captain, chief_engineer, crew)
- Query intent (receive, diagnose, view)

**Example**:
```
Search: "engine oil filter"
   ↓
SQL RAG returns: Part #1234 (on_hand: 10)
   ↓
Microaction module adds:
  - receive_part (always available)
  - consume_part (on_hand > 0)
  - write_off_part (Captain only, on_hand > 0)
  - adjust_stock_quantity (Captain only)
  - generate_part_labels
   ↓
Frontend renders: Entity card + action buttons
```

### Architecture

#### File Structure

```
apps/api/
├── prepare/
│   ├── capability_registry.py       # Search capabilities
│   └── capabilities/
│       └── part_capabilities.py
│
├── microactions/                     # NEW MODULE
│   ├── __init__.py
│   ├── microaction_registry.py      # Auto-discovery
│   ├── base_microaction.py          # Base class
│   │
│   └── lens_microactions/           # Lens-specific action logic
│       ├── __init__.py
│       ├── part_microactions.py     # Part Lens
│       ├── certificate_microactions.py
│       ├── crew_microactions.py
│       └── ...
│
└── graphrag_query.py                # UPDATED: Call microaction registry
```

#### Base Microaction Class

**File**: `apps/api/microactions/base_microaction.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class ActionSuggestion(BaseModel):
    """Single action suggestion."""
    action_id: str              # e.g., "receive_part"
    label: str                  # e.g., "Receive Part"
    variant: str                # "READ", "MUTATE", "SIGNED"
    entity_id: str              # UUID of entity
    entity_type: str            # "part", "certificate", etc.
    prefill_data: Dict = {}     # Pre-filled form data
    priority: int = 1           # Higher = shown first

class BaseLensMicroactions(ABC):
    """Base class for lens-specific microaction logic."""

    @property
    @abstractmethod
    def lens_name(self) -> str:
        """Lens identifier."""
        pass

    @property
    @abstractmethod
    def entity_types(self) -> List[str]:
        """Entity types this lens handles."""
        pass

    @abstractmethod
    async def get_suggestions(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """
        Get context-valid actions for an entity.

        Args:
            entity_type: "part", "certificate", etc.
            entity_id: UUID of the entity
            entity_data: Full entity data from search
            user_role: "crew", "chief_engineer", "captain", etc.
            yacht_id: Tenant isolation
            query_intent: Optional intent (e.g., "receive_part")

        Returns:
            List of suggested actions, filtered by role and state
        """
        pass
```

#### Part Lens Microactions (Example)

**File**: `apps/api/microactions/lens_microactions/part_microactions.py`

```python
from typing import List, Dict, Any, Optional
from ..base_microaction import BaseLensMicroactions, ActionSuggestion
from apps.api.action_router.registry import get_actions_for_domain

class PartLensMicroactions(BaseLensMicroactions):
    """Part Lens microaction logic."""

    lens_name = "part_lens"
    entity_types = ["part", "inventory_stock", "shopping_list_item"]

    def __init__(self, db_client):
        self.db = db_client

    async def get_suggestions(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """Get part-specific actions."""

        suggestions = []

        # Get all part actions for user role
        all_actions = get_actions_for_domain("parts", user_role)

        # Fetch current stock state
        stock_info = await self._get_stock_info(entity_id, yacht_id)
        on_hand = stock_info.get("on_hand", 0)

        # Filter actions based on stock state and role
        for action in all_actions:
            # Stock-based filtering
            if on_hand == 0 and action.action_id in ["consume_part", "write_off_part", "transfer_part"]:
                continue  # Can't consume/write-off if no stock

            # Intent-based prioritization
            priority = 1
            if query_intent and action.action_id == query_intent:
                priority = 3  # Boost priority for intent match

            # Build suggestion
            suggestions.append(ActionSuggestion(
                action_id=action.action_id,
                label=action.label,
                variant=action.variant.value,
                entity_id=entity_id,
                entity_type=entity_type,
                prefill_data=await self._get_prefill_data(action.action_id, entity_id, yacht_id),
                priority=priority
            ))

        # Sort by priority (descending)
        suggestions.sort(key=lambda s: s.priority, reverse=True)

        return suggestions

    async def _get_stock_info(self, part_id: str, yacht_id: str) -> Dict:
        """Fetch current stock information."""
        query = """
            SELECT on_hand, allocated, available
            FROM pms_inventory_stock
            WHERE part_id = %s AND yacht_id = %s
            LIMIT 1
        """
        result = await self.db.fetch_one(query, [part_id, yacht_id])
        return dict(result) if result else {"on_hand": 0, "allocated": 0, "available": 0}

    async def _get_prefill_data(self, action_id: str, part_id: str, yacht_id: str) -> Dict:
        """Get pre-fill data for action."""

        # Fetch part details
        query = """
            SELECT id, part_number, name, category, manufacturer
            FROM pms_parts
            WHERE id = %s AND yacht_id = %s
        """
        part = await self.db.fetch_one(query, [part_id, yacht_id])

        if not part:
            return {}

        # Fetch stock info
        stock_info = await self._get_stock_info(part_id, yacht_id)

        # Action-specific prefill
        if action_id == "receive_part":
            return {
                "part_id": part["id"],
                "part_name": part["name"],
                "part_number": part["part_number"],
                "current_stock": stock_info["on_hand"],
                "suggested_location": "Engine Room",  # Could be smart suggestion
            }
        elif action_id == "consume_part":
            return {
                "part_id": part["id"],
                "part_name": part["name"],
                "available_quantity": stock_info["available"],
                "max_quantity": stock_info["available"],
            }
        elif action_id == "write_off_part":
            return {
                "part_id": part["id"],
                "part_name": part["name"],
                "current_stock": stock_info["on_hand"],
                "max_quantity": stock_info["on_hand"],
            }
        elif action_id == "adjust_stock_quantity":
            return {
                "part_id": part["id"],
                "part_name": part["name"],
                "current_quantity": stock_info["on_hand"],
            }
        else:
            # Generic prefill
            return {
                "part_id": part["id"],
                "part_name": part["name"],
            }
```

#### Microaction Registry

**File**: `apps/api/microactions/microaction_registry.py`

```python
from typing import Dict, List
from .base_microaction import BaseLensMicroactions, ActionSuggestion
import importlib
import pkgutil
from pathlib import Path

class MicroactionRegistry:
    """Auto-discovers and manages lens microaction modules."""

    def __init__(self, db_client):
        self.db = db_client
        self.lenses: Dict[str, BaseLensMicroactions] = {}
        self.entity_type_to_lens: Dict[str, str] = {}

    def discover_and_register(self):
        """Auto-discover all lens microaction files."""
        microactions_path = Path(__file__).parent / "lens_microactions"

        for module_info in pkgutil.iter_modules([str(microactions_path)]):
            if module_info.name == "__init__":
                continue

            module_path = f"apps.api.microactions.lens_microactions.{module_info.name}"
            module = importlib.import_module(module_path)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseLensMicroactions)
                    and attr is not BaseLensMicroactions
                ):
                    lens = attr(self.db)

                    # Register lens
                    self.lenses[lens.lens_name] = lens

                    # Map entity types to lens
                    for entity_type in lens.entity_types:
                        if entity_type in self.entity_type_to_lens:
                            raise ValueError(
                                f"[MicroactionRegistry] Duplicate entity type '{entity_type}' "
                                f"claimed by {self.entity_type_to_lens[entity_type]} and {lens.lens_name}"
                            )
                        self.entity_type_to_lens[entity_type] = lens.lens_name

                    print(f"[MicroactionRegistry] ✓ Registered: {lens.lens_name} "
                          f"({len(lens.entity_types)} entity types)")

        print(f"[MicroactionRegistry] Total lenses: {len(self.lenses)}")

    async def get_suggestions_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict,
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """Get action suggestions for an entity."""

        if entity_type not in self.entity_type_to_lens:
            # No microactions for this entity type
            return []

        lens_name = self.entity_type_to_lens[entity_type]
        lens = self.lenses[lens_name]

        try:
            suggestions = await lens.get_suggestions(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_data=entity_data,
                user_role=user_role,
                yacht_id=yacht_id,
                query_intent=query_intent
            )
            return suggestions
        except Exception as e:
            print(
                f"[MicroactionRegistry] Error getting suggestions for {entity_type} "
                f"from {lens_name}: {str(e)}"
            )
            return []
```

#### Integration with GraphRAG Query

**File**: `apps/api/graphrag_query.py` (updated)

```python
from apps.api.microactions.microaction_registry import MicroactionRegistry

class GraphRAGQuery:
    def __init__(self, db_client):
        self.composer = CapabilityComposer(db_client)
        self.microactions = MicroactionRegistry(db_client)  # NEW
        self.microactions.discover_and_register()

    async def query(
        self,
        yacht_id: str,
        query_text: str,
        user_role: str,
        limit: int = 20
    ) -> Dict:
        """
        Execute query with microaction addition.

        Flow:
        1. Entity extraction
        2. SQL RAG search (capability composer)
        3. Microaction addition (for each result)
        4. Return enriched results
        """

        # Step 1: Extract entities and intent
        extractor = get_gpt_extractor()
        extraction = extractor.extract(query_text)
        entities = extraction.entities
        intent = extraction.intent  # e.g., "receive_part"

        # Step 2: SQL RAG search
        if not entities:
            results = await self.composer.comprehensive_search(
                yacht_id=yacht_id,
                search_term=query_text,
                limit=limit
            )
        else:
            results = []
            for entity in entities:
                entity_results = await self.composer.search_by_entity(
                    entity_type=entity["type"],
                    yacht_id=yacht_id,
                    search_term=entity["value"],
                    limit=limit
                )
                results.extend(entity_results)

        # Step 3: Add microactions to each result
        enriched_results = []
        for result in results:
            # Get action suggestions for this entity
            suggestions = await self.microactions.get_suggestions_for_entity(
                entity_type=result.type,
                entity_id=result.id,
                entity_data=result.metadata,
                user_role=user_role,
                yacht_id=yacht_id,
                query_intent=intent  # Pass intent for prioritization
            )

            # Attach actions to result
            enriched_result = {
                **result.to_dict(),
                "suggested_actions": [s.dict() for s in suggestions]
            }

            enriched_results.append(enriched_result)

        return {
            "success": True,
            "results": enriched_results,
            "total_count": len(enriched_results),
            "intent": intent,  # Return intent to frontend
            "entities": entities
        }
```

### Integration with Frontend

**File**: `apps/web/src/hooks/useCelesteSearch.ts` (updated)

```typescript
const searchResponse = await fetch('/webhook/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: searchTerm })
});

const data = await searchResponse.json();

// NEW: Results now include suggested_actions
setState(prev => ({
  ...prev,
  results: data.results,
  intent: data.intent,  // NEW: Intent from backend
  entities: data.entities,  // NEW: Extracted entities
}));

// Each result has suggested_actions array
data.results.forEach(result => {
  console.log(result.suggested_actions);  // Action buttons to render
});
```

**File**: `apps/web/src/components/spotlight/SpotlightSearch.tsx` (updated)

```tsx
{results.map((result) => (
  <div key={result.id}>
    {/* Entity card */}
    <EntityCard data={result} />

    {/* Action buttons (from microactions) */}
    <SuggestedActions
      actions={result.suggested_actions}
      yachtId={yachtId}
    />
  </div>
))}
```

### Benefits

**Separation of Concerns**:
- Capability Composer: **Find** entities
- Microaction Registry: **Suggest actions** for entities
- Frontend: **Render** entities + actions

**Lens Ownership**:
- Each lens owns its microaction logic
- Part Lens worker updates `part_microactions.py`
- Certificate Lens worker updates `certificate_microactions.py`

**Context-Aware**:
- Actions filtered by entity state (stock level, expiry, etc.)
- Actions filtered by user role
- Actions prioritized by query intent

**Bulletproof**:
- Auto-discovery (drop file in folder)
- Fail-fast validation at startup
- Clear error traces

---

**Questions for Review**:
1. Does this structure meet "bulletproof" requirements?
2. Any additional validation needed at startup?
3. Should we add capability-level caching?
4. Naming conventions acceptable?
5. **NEW**: Does microaction architecture solve the "actions on top" pattern gap?
6. **NEW**: Should prefill data be cached or fetched on-demand?
