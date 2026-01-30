"""
Microaction Registry - Auto-Discovery & Management
===================================================

Auto-discovers all lens microaction modules and provides unified interface for action suggestions.

At startup:
1. Scans apps/api/microactions/lens_microactions/ directory
2. Imports all *_microactions.py modules
3. Finds BaseLensMicroactions subclasses
4. Registers entity-to-lens mappings

Provides:
- get_suggestions_for_entity(): Get actions for a specific entity
- get_suggestions_for_entities(): Get actions for multiple entities

Usage:
    registry = MicroactionRegistry(db_client)
    registry.discover_and_register()

    suggestions = await registry.get_suggestions_for_entity(
        entity_type="part",
        entity_id="uuid-1234",
        entity_data={...},
        user_role="captain",
        yacht_id="yacht-uuid",
        query_intent="receive_part"
    )
"""

import importlib
import pkgutil
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .base_microaction import (
    BaseLensMicroactions,
    ActionSuggestion,
    MicroactionError
)

logger = logging.getLogger(__name__)


# =============================================================================
# MICROACTION REGISTRY
# =============================================================================

class MicroactionRegistry:
    """
    Auto-discovers and manages all lens microaction modules.

    Usage:
        registry = MicroactionRegistry(db_client)
        registry.discover_and_register()

        # Get suggestions for single entity
        suggestions = await registry.get_suggestions_for_entity(
            entity_type="part",
            entity_id="uuid",
            entity_data={...},
            user_role="captain",
            yacht_id="yacht-uuid"
        )
    """

    def __init__(self, db_client):
        """
        Initialize registry.

        Args:
            db_client: Database client (Supabase or async postgres)
        """
        self.db = db_client
        self.lenses: Dict[str, BaseLensMicroactions] = {}
        self.entity_type_to_lens: Dict[str, str] = {}  # Entity type -> Lens name
        self._initialized = False

    def discover_and_register(self) -> None:
        """
        Auto-discover all lens microaction files.

        Scans: apps/api/microactions/lens_microactions/
        Finds: *_microactions.py modules
        Loads: BaseLensMicroactions subclasses
        Registers: Entity-to-lens routing

        Raises:
            ValueError: If duplicate entity types found
            ImportError: If module import fails
        """
        if self._initialized:
            logger.warning("[MicroactionRegistry] Already initialized, skipping discovery")
            return

        microactions_path = Path(__file__).parent / "lens_microactions"

        if not microactions_path.exists():
            logger.warning(
                f"[MicroactionRegistry] Microactions directory not found: {microactions_path}"
            )
            logger.warning("[MicroactionRegistry] Creating empty lens_microactions/ directory")
            microactions_path.mkdir(parents=True, exist_ok=True)
            (microactions_path / "__init__.py").touch()
            return

        logger.info("[MicroactionRegistry] Discovering lens microactions...")

        # Import all modules in lens_microactions/
        for module_info in pkgutil.iter_modules([str(microactions_path)]):
            if module_info.name == "__init__":
                continue

            module_path = f"apps.api.microactions.lens_microactions.{module_info.name}"

            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                logger.error(
                    f"[MicroactionRegistry] Failed to import {module_path}: {str(e)}"
                )
                continue

            # Find BaseLensMicroactions subclasses in module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if not isinstance(attr, type):
                    continue

                if not issubclass(attr, BaseLensMicroactions):
                    continue

                if attr is BaseLensMicroactions:
                    continue

                # Found a lens microaction class
                try:
                    lens = attr(self.db)
                except Exception as e:
                    logger.error(
                        f"[MicroactionRegistry] Failed to instantiate {attr_name}: {str(e)}"
                    )
                    continue

                # Register lens
                self._register_lens(lens)

                logger.info(
                    f"[MicroactionRegistry] ✓ Registered: {lens.lens_name} "
                    f"({len(lens.entity_types)} entity types)"
                )

        self._initialized = True

        logger.info(f"[MicroactionRegistry] Total lenses: {len(self.lenses)}")
        logger.info(f"[MicroactionRegistry] Total entity types: {len(self.entity_type_to_lens)}")

        if len(self.lenses) == 0:
            logger.warning(
                "[MicroactionRegistry] No lenses registered! "
                "Add *_microactions.py files to apps/api/microactions/lens_microactions/"
            )

    def _register_lens(self, lens: BaseLensMicroactions) -> None:
        """
        Register a lens and its entity type mappings.

        Args:
            lens: Lens microaction instance

        Raises:
            ValueError: If duplicate entity types or lens names
        """
        if lens.lens_name in self.lenses:
            raise ValueError(
                f"[MicroactionRegistry] Duplicate lens name: {lens.lens_name}"
            )

        self.lenses[lens.lens_name] = lens

        # Register entity type mappings
        for entity_type in lens.entity_types:
            if entity_type in self.entity_type_to_lens:
                existing_lens = self.entity_type_to_lens[entity_type]
                raise ValueError(
                    f"[MicroactionRegistry] Duplicate entity type '{entity_type}' "
                    f"claimed by both {existing_lens} and {lens.lens_name}"
                )

            self.entity_type_to_lens[entity_type] = lens.lens_name

    async def get_suggestions_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict,
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """
        Get action suggestions for a single entity.

        Args:
            entity_type: Type of entity (e.g., "part", "certificate")
            entity_id: UUID of the entity
            entity_data: Full entity data from search result
            user_role: User's role ("crew", "chief_engineer", "captain", etc.)
            yacht_id: Tenant isolation UUID
            query_intent: Optional intent from query (e.g., "receive_part")

        Returns:
            List of ActionSuggestion objects

        Raises:
            MicroactionError: If execution fails
        """
        if not self._initialized:
            raise RuntimeError(
                "[MicroactionRegistry] Not initialized. Call discover_and_register() first."
            )

        # Check if we have microactions for this entity type
        if entity_type not in self.entity_type_to_lens:
            # No microactions registered for this entity type
            logger.debug(
                f"[MicroactionRegistry] No microactions registered for entity type: {entity_type}"
            )
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
            logger.error(
                f"[MicroactionRegistry] Failed to get suggestions for {entity_type} "
                f"from {lens_name}: {str(e)}"
            )
            # Return empty list instead of raising - fail gracefully
            return []

    async def get_suggestions_for_entities(
        self,
        entities: List[Dict],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> Dict[str, List[ActionSuggestion]]:
        """
        Get action suggestions for multiple entities.

        Args:
            entities: List of entity dicts with 'type', 'id', and data
            user_role: User's role
            yacht_id: Tenant isolation UUID
            query_intent: Optional intent from query

        Returns:
            Dict mapping entity_id -> List[ActionSuggestion]
        """
        result = {}

        for entity in entities:
            entity_id = entity.get("id")
            entity_type = entity.get("type")

            if not entity_id or not entity_type:
                continue

            suggestions = await self.get_suggestions_for_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_data=entity,
                user_role=user_role,
                yacht_id=yacht_id,
                query_intent=query_intent
            )

            result[entity_id] = suggestions

        return result

    def get_lens_names(self) -> List[str]:
        """Get all registered lens names."""
        return sorted(self.lenses.keys())

    def get_entity_types(self) -> List[str]:
        """Get all registered entity types."""
        return sorted(self.entity_type_to_lens.keys())

    def is_initialized(self) -> bool:
        """Check if registry has been initialized."""
        return self._initialized


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    """
    Test the microaction registry.

    Usage:
        python -m apps.api.microactions.microaction_registry
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
    registry = MicroactionRegistry(client)

    try:
        print("=" * 60)
        print("MICROACTION REGISTRY TEST")
        print("=" * 60)

        # Discover lenses
        registry.discover_and_register()

        print(f"\nRegistered lenses: {registry.get_lens_names()}")
        print(f"Total entity types: {len(registry.get_entity_types())}")

        for lens_name in registry.get_lens_names():
            lens = registry.lenses[lens_name]
            print(f"\n{lens_name}:")
            for entity_type in lens.entity_types:
                print(f"  - {entity_type}")

        print("\n" + "=" * 60)
        print("REGISTRY VALIDATION: SUCCESS")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
