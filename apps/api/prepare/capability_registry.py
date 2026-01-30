"""
Capability Registry - Auto-Discovery System
==========================================
Automatically discovers and registers lens capability modules at startup.

Features:
- Scans prepare/capabilities/ directory for *_capabilities.py files
- Validates each lens before registration
- Provides entity-based search routing
- Thread-safe singleton registry

Usage:
    from prepare.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry(supabase_client)
    registry.discover_and_register()

    # Entity-specific search
    results = await registry.search("PART_NUMBER", yacht_id, "OF-1234")

    # Search all lenses
    all_results = await registry.search_all_lenses(yacht_id, "oil filter")
"""

import pkgutil
import importlib
from pathlib import Path
from typing import List, Dict, Optional
from supabase import Client

from .base_capability import (
    BaseLensCapability,
    CapabilityMapping,
    SearchResult,
    CapabilityExecutionError
)


class CapabilityRegistry:
    """
    Singleton registry for all lens capabilities.
    Auto-discovers lens modules and provides search routing.
    """

    _instance = None

    def __new__(cls, db: Client = None):
        """Singleton pattern to ensure one registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db: Client):
        """
        Initialize registry with Supabase client.

        Args:
            db: Supabase client instance
        """
        if self._initialized:
            return

        self.db = db
        self._lenses: Dict[str, BaseLensCapability] = {}
        self._entity_to_lens: Dict[str, str] = {}
        self._entity_mappings: Dict[str, CapabilityMapping] = {}
        self._initialized = True

    def discover_and_register(self) -> None:
        """
        Auto-discover all lens capability files in prepare/capabilities/ directory.
        Validates and registers each lens found.

        Looks for files matching pattern: {lens_name}_capabilities.py
        Each file should contain a class: {LensName}LensCapability

        Raises:
            ValueError: If lens validation fails
        """
        print("[CapabilityRegistry] Discovering lens capabilities...")

        capabilities_path = Path(__file__).parent / "capabilities"

        if not capabilities_path.exists():
            print(f"[CapabilityRegistry] Warning: capabilities directory not found at {capabilities_path}")
            return

        # Iterate through all Python modules in capabilities directory
        for module_info in pkgutil.iter_modules([str(capabilities_path)]):
            module_name = module_info.name

            # Skip __init__.py and non-lens files
            if not module_name.endswith('_capabilities'):
                continue

            try:
                # Import the module
                module_path = f"prepare.capabilities.{module_name}"
                module = importlib.import_module(module_path)

                # Find the capability class
                # Expected pattern: part_capabilities.py → PartLensCapability
                lens_class = self._find_capability_class(module, module_name)

                if lens_class is None:
                    print(f"[CapabilityRegistry] Warning: No capability class found in {module_name}")
                    continue

                # Instantiate the lens
                lens_instance = lens_class(self.db)

                # Validate the lens
                lens_instance.validate()

                # Register the lens
                if lens_instance.enabled:
                    self._register_lens(lens_instance)
                else:
                    print(f"[CapabilityRegistry] Skipping disabled lens: {lens_instance.lens_name}")

            except Exception as e:
                print(f"[CapabilityRegistry] Error loading {module_name}: {e}")
                import traceback
                traceback.print_exc()

        print(f"[CapabilityRegistry] Discovery complete. Registered {len(self._lenses)} lenses.")

    def _find_capability_class(self, module, module_name: str):
        """
        Find the BaseLensCapability subclass in a module.

        Args:
            module: Imported module
            module_name: Name of the module file (e.g., 'part_capabilities')

        Returns:
            Capability class or None
        """
        # Expected class name: part_capabilities → PartLensCapability
        lens_base = module_name.replace('_capabilities', '')
        expected_class_name = ''.join(word.capitalize() for word in lens_base.split('_')) + 'LensCapability'

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # Check if it's a class and subclass of BaseLensCapability
            if (
                isinstance(attr, type) and
                issubclass(attr, BaseLensCapability) and
                attr is not BaseLensCapability
            ):
                return attr

        return None

    def _register_lens(self, lens: BaseLensCapability) -> None:
        """
        Register a lens and its entity mappings.

        Args:
            lens: Lens instance to register
        """
        lens_name = lens.lens_name
        self._lenses[lens_name] = lens

        # Register entity mappings
        mappings = lens.get_entity_mappings()

        for mapping in mappings:
            entity_type = mapping.entity_type.upper()

            # Warn if entity type already registered
            if entity_type in self._entity_to_lens:
                print(
                    f"[CapabilityRegistry] Warning: Entity type '{entity_type}' "
                    f"already registered to {self._entity_to_lens[entity_type]}, "
                    f"overwriting with {lens_name}"
                )

            self._entity_to_lens[entity_type] = lens_name
            self._entity_mappings[entity_type] = mapping

        print(
            f"[CapabilityRegistry] ✓ Registered: {lens_name} "
            f"({len(mappings)} entity types)"
        )

    async def search(
        self,
        entity_type: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Search for a specific entity type.

        Args:
            entity_type: Entity type to search (e.g., "PART_NUMBER")
            yacht_id: Yacht ID for RLS filtering
            search_term: Search query
            limit: Maximum results

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If entity type not registered
            CapabilityExecutionError: If search fails
        """
        entity_type = entity_type.upper()

        if entity_type not in self._entity_to_lens:
            raise ValueError(f"Unknown entity type: {entity_type}")

        lens_name = self._entity_to_lens[entity_type]
        mapping = self._entity_mappings[entity_type]
        lens = self._lenses[lens_name]

        try:
            results = await lens.execute_capability(
                capability_name=mapping.capability_name,
                yacht_id=yacht_id,
                search_term=search_term,
                limit=limit
            )
            return results

        except Exception as e:
            raise CapabilityExecutionError(
                lens_name=lens_name,
                capability_name=mapping.capability_name,
                table_name=mapping.table_name,
                original_error=e
            )

    async def search_all_lenses(
        self,
        yacht_id: str,
        search_term: str,
        limit_per_lens: int = 10
    ) -> Dict[str, List[SearchResult]]:
        """
        Search across all registered lenses.

        Args:
            yacht_id: Yacht ID for RLS filtering
            search_term: Search query
            limit_per_lens: Maximum results per lens

        Returns:
            Dict mapping lens_name to list of results
        """
        all_results = {}

        for lens_name, lens in self._lenses.items():
            try:
                # Get all entity mappings for this lens
                mappings = lens.get_entity_mappings()

                lens_results = []
                for mapping in mappings:
                    results = await lens.execute_capability(
                        capability_name=mapping.capability_name,
                        yacht_id=yacht_id,
                        search_term=search_term,
                        limit=limit_per_lens
                    )
                    lens_results.extend(results)

                all_results[lens_name] = lens_results

            except Exception as e:
                print(f"[CapabilityRegistry] Error searching {lens_name}: {e}")
                all_results[lens_name] = []

        return all_results

    def get_lens(self, lens_name: str) -> Optional[BaseLensCapability]:
        """
        Get a lens by name.

        Args:
            lens_name: Name of lens (e.g., "part_lens")

        Returns:
            Lens instance or None if not found
        """
        return self._lenses.get(lens_name)

    def get_lens_names(self) -> List[str]:
        """
        Get list of all registered lens names.

        Returns:
            List of lens names
        """
        return list(self._lenses.keys())

    def get_all_entity_types(self) -> List[str]:
        """
        Get list of all registered entity types.

        Returns:
            List of entity type names
        """
        return list(self._entity_to_lens.keys())

    def get_entity_mapping(self, entity_type: str) -> Optional[CapabilityMapping]:
        """
        Get the capability mapping for an entity type.

        Args:
            entity_type: Entity type name

        Returns:
            CapabilityMapping or None
        """
        return self._entity_mappings.get(entity_type.upper())


# Module-level test function
if __name__ == "__main__":
    """Test the registry with a mock Supabase client."""
    import asyncio

    class MockClient:
        """Mock Supabase client for testing."""
        pass

    async def test_registry():
        print("Testing CapabilityRegistry...")
        mock_db = MockClient()

        registry = CapabilityRegistry(mock_db)
        registry.discover_and_register()

        print(f"\nLenses found: {registry.get_lens_names()}")
        print(f"Entity types: {registry.get_all_entity_types()}")

        print("\nRegistry test complete!")

    asyncio.run(test_registry())
