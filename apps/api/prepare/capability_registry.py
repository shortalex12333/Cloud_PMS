"""
Capability Registry - Auto-Discovery & Management
==================================================

Auto-discovers all lens capability modules and provides unified search interface.

At startup:
1. Scans apps/api/prepare/capabilities/ directory
2. Imports all *_capabilities.py modules
3. Finds BaseLensCapability subclasses
4. Validates each lens
5. Registers entity-to-lens mappings

Provides:
- search(): Entity-specific search
- search_all_lenses(): Comprehensive multi-lens search
- get_entity_types(): List all searchable entities
"""

import importlib
import pkgutil
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .base_capability import (
    BaseLensCapability,
    CapabilityMapping,
    SearchResult,
    CapabilityError
)

logger = logging.getLogger(__name__)


# =============================================================================
# CAPABILITY REGISTRY
# =============================================================================

class CapabilityRegistry:
    """
    Auto-discovers and manages all lens capabilities.

    Usage:
        registry = CapabilityRegistry(db_client)
        registry.discover_and_register()

        # Entity-specific search
        results = await registry.search("PART_NUMBER", yacht_id, "1234")

        # Comprehensive search
        results = await registry.search_all_lenses(yacht_id, "filter")
    """

    def __init__(self, db_client):
        """
        Initialize registry.

        Args:
            db_client: Database client (Supabase or async postgres)
        """
        self.db = db_client
        self.lenses: Dict[str, BaseLensCapability] = {}
        self.entity_to_lens: Dict[str, str] = {}  # Entity type -> Lens name
        self.entity_mappings: Dict[str, CapabilityMapping] = {}  # Entity type -> Mapping
        self._initialized = False

    def discover_and_register(self) -> None:
        """
        Auto-discover all lens capability files.

        Scans: apps/api/prepare/capabilities/
        Finds: *_capabilities.py modules
        Loads: BaseLensCapability subclasses
        Validates: Entity mappings and capability implementations
        Registers: Entity-to-lens routing

        Raises:
            ValueError: If validation fails
            ImportError: If module import fails
        """
        if self._initialized:
            logger.warning("[CapabilityRegistry] Already initialized, skipping discovery")
            return

        capabilities_path = Path(__file__).parent / "capabilities"

        if not capabilities_path.exists():
            logger.warning(
                f"[CapabilityRegistry] Capabilities directory not found: {capabilities_path}"
            )
            logger.warning("[CapabilityRegistry] Creating empty capabilities/ directory")
            capabilities_path.mkdir(parents=True, exist_ok=True)
            (capabilities_path / "__init__.py").touch()
            return

        logger.info("[CapabilityRegistry] Discovering lens capabilities...")

        # Import all modules in capabilities/
        for module_info in pkgutil.iter_modules([str(capabilities_path)]):
            if module_info.name == "__init__":
                continue

            module_path = f"apps.api.prepare.capabilities.{module_info.name}"

            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                logger.error(
                    f"[CapabilityRegistry] Failed to import {module_path}: {str(e)}"
                )
                continue

            # Find BaseLensCapability subclasses in module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if not isinstance(attr, type):
                    continue

                if not issubclass(attr, BaseLensCapability):
                    continue

                if attr is BaseLensCapability:
                    continue

                # Found a lens capability class
                try:
                    lens = attr(self.db)
                except Exception as e:
                    logger.error(
                        f"[CapabilityRegistry] Failed to instantiate {attr_name}: {str(e)}"
                    )
                    continue

                # Skip if disabled
                if not lens.enabled:
                    logger.info(
                        f"[CapabilityRegistry] Skipping disabled lens: {lens.lens_name}"
                    )
                    continue

                # Validate lens
                try:
                    lens.validate()
                except Exception as e:
                    raise RuntimeError(
                        f"[CapabilityRegistry] Validation failed for {lens.lens_name} "
                        f"in {module_path}:\n{str(e)}"
                    )

                # Register lens
                self._register_lens(lens)

                logger.info(
                    f"[CapabilityRegistry] ✓ Registered: {lens.lens_name} "
                    f"({len(lens.get_entity_mappings())} entities)"
                )

        self._initialized = True

        logger.info(f"[CapabilityRegistry] Total lenses: {len(self.lenses)}")
        logger.info(f"[CapabilityRegistry] Total entity types: {len(self.entity_mappings)}")

        if len(self.lenses) == 0:
            logger.warning(
                "[CapabilityRegistry] No lenses registered! "
                "Add *_capabilities.py files to apps/api/prepare/capabilities/"
            )

    def _register_lens(self, lens: BaseLensCapability) -> None:
        """
        Register a lens and its entity mappings.

        Args:
            lens: Lens capability instance

        Raises:
            ValueError: If duplicate entity types or lens names
        """
        if lens.lens_name in self.lenses:
            raise ValueError(
                f"[CapabilityRegistry] Duplicate lens name: {lens.lens_name}"
            )

        self.lenses[lens.lens_name] = lens

        # Register entity mappings
        for mapping in lens.get_entity_mappings():
            if mapping.entity_type in self.entity_to_lens:
                existing_lens = self.entity_to_lens[mapping.entity_type]
                raise ValueError(
                    f"[CapabilityRegistry] Duplicate entity type '{mapping.entity_type}' "
                    f"claimed by both {existing_lens} and {lens.lens_name}"
                )

            self.entity_to_lens[mapping.entity_type] = lens.lens_name
            self.entity_mappings[mapping.entity_type] = mapping

    async def search(
        self,
        entity_type: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Search using a specific entity type.

        Args:
            entity_type: Entity type (e.g., "PART_NUMBER", "CERTIFICATE_TYPE")
            yacht_id: Tenant isolation UUID
            search_term: User's search query
            limit: Maximum results to return

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If entity_type not registered
            CapabilityError: If search execution fails
        """
        if not self._initialized:
            raise RuntimeError(
                "[CapabilityRegistry] Not initialized. Call discover_and_register() first."
            )

        if entity_type not in self.entity_to_lens:
            raise ValueError(
                f"[CapabilityRegistry] Unknown entity type: {entity_type}. "
                f"Available: {sorted(self.entity_to_lens.keys())}"
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
            logger.error(
                f"[CapabilityRegistry] Search failed for entity '{entity_type}' "
                f"in lens '{lens_name}': {str(e)}"
            )
            raise CapabilityError(
                f"Search failed for entity '{entity_type}' in lens '{lens_name}': {str(e)}"
            )

    async def search_all_lenses(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 50
    ) -> List[SearchResult]:
        """
        Search across ALL lenses and return ranked results.

        Executes all capabilities in parallel and merges results.

        Args:
            yacht_id: Tenant isolation UUID
            search_term: User's search query
            limit: Maximum total results to return

        Returns:
            List of SearchResult objects, ranked by score and priority
        """
        if not self._initialized:
            raise RuntimeError(
                "[CapabilityRegistry] Not initialized. Call discover_and_register() first."
            )

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
                    logger.warning(
                        f"[CapabilityRegistry] {lens_name}.{mapping.capability_name} "
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

        # Sort by priority (from mapping) and score
        unique_results.sort(
            key=lambda r: (
                self.entity_mappings.get(
                    self.entity_to_lens.get(r.type, ""),
                    CapabilityMapping(
                        entity_type="",
                        capability_name="",
                        table_name="",
                        search_column="",
                        result_type="",
                        priority=1
                    )
                ).priority,
                r.score
            ),
            reverse=True
        )

        return unique_results[:limit]

    def get_entity_types_for_lens(self, lens_name: str) -> List[str]:
        """
        Get all entity types owned by a lens.

        Args:
            lens_name: Lens identifier (e.g., "part_lens")

        Returns:
            List of entity types
        """
        return [
            entity_type
            for entity_type, owner_lens in self.entity_to_lens.items()
            if owner_lens == lens_name
        ]

    def get_all_entity_types(self) -> List[str]:
        """
        Get all registered entity types across all lenses.

        Returns:
            List of entity types
        """
        return sorted(self.entity_to_lens.keys())

    def get_lens_names(self) -> List[str]:
        """
        Get all registered lens names.

        Returns:
            List of lens names
        """
        return sorted(self.lenses.keys())

    def is_initialized(self) -> bool:
        """Check if registry has been initialized."""
        return self._initialized


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    """
    Test the capability registry.

    Usage:
        python -m apps.api.prepare.capability_registry
    """
    import sys
    import asyncio
    from supabase import create_client
    import os

    logging.basicConfig(level=logging.INFO)

    # Check for Supabase credentials
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Create registry
    registry = CapabilityRegistry(client)

    try:
        print("=" * 60)
        print("CAPABILITY REGISTRY TEST")
        print("=" * 60)

        # Discover lenses
        registry.discover_and_register()

        print(f"\nRegistered lenses: {registry.get_lens_names()}")
        print(f"Total entity types: {len(registry.get_all_entity_types())}")

        for lens_name in registry.get_lens_names():
            entities = registry.get_entity_types_for_lens(lens_name)
            print(f"\n{lens_name}:")
            for entity in entities:
                print(f"  - {entity}")

        print("\n" + "=" * 60)
        print("REGISTRY VALIDATION: SUCCESS")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
