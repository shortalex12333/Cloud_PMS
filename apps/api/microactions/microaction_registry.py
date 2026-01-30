"""
Microaction Registry - Auto-Discovery System
===========================================
Automatically discovers and registers lens microaction modules at startup.

Features:
- Scans microactions/lens_microactions/ directory for *_microactions.py files
- Validates each lens before registration
- Provides action suggestion routing
- Thread-safe singleton registry

Usage:
    from microactions.microaction_registry import MicroactionRegistry

    registry = MicroactionRegistry(supabase_client)
    registry.discover_and_register()

    # Get action suggestions for an entity
    suggestions = await registry.get_suggestions(
        lens_name="part_lens",
        entity_type="part",
        entity_id="uuid",
        entity_data={...},
        user_role="chief_engineer",
        yacht_id="uuid"
    )
"""

import pkgutil
import importlib
from pathlib import Path
from typing import List, Dict, Optional
from supabase import Client

from .base_microaction import (
    BaseLensMicroactions,
    ActionSuggestion,
    MicroactionExecutionError
)


class MicroactionRegistry:
    """
    Singleton registry for all lens microactions.
    Auto-discovers microaction modules and provides action routing.
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
        self._lenses: Dict[str, BaseLensMicroactions] = {}
        self._entity_type_to_lens: Dict[str, str] = {}
        self._initialized = True

    def discover_and_register(self) -> None:
        """
        Auto-discover all lens microaction files in microactions/lens_microactions/ directory.
        Validates and registers each lens found.

        Looks for files matching pattern: {lens_name}_microactions.py
        Each file should contain a class: {LensName}LensMicroactions

        Raises:
            ValueError: If lens validation fails
        """
        print("[MicroactionRegistry] Discovering lens microactions...")

        microactions_path = Path(__file__).parent / "lens_microactions"

        if not microactions_path.exists():
            print(f"[MicroactionRegistry] Warning: lens_microactions directory not found at {microactions_path}")
            return

        # Iterate through all Python modules in lens_microactions directory
        for module_info in pkgutil.iter_modules([str(microactions_path)]):
            module_name = module_info.name

            # Skip __init__.py and non-lens files
            if not module_name.endswith('_microactions'):
                continue

            try:
                # Import the module
                module_path = f"microactions.lens_microactions.{module_name}"
                module = importlib.import_module(module_path)

                # Find the microaction class
                # Expected pattern: part_microactions.py → PartLensMicroactions
                lens_class = self._find_microaction_class(module, module_name)

                if lens_class is None:
                    print(f"[MicroactionRegistry] Warning: No microaction class found in {module_name}")
                    continue

                # Instantiate the lens
                lens_instance = lens_class(self.db)

                # Validate the lens
                lens_instance.validate()

                # Register the lens
                self._register_lens(lens_instance)

            except Exception as e:
                print(f"[MicroactionRegistry] Error loading {module_name}: {e}")
                import traceback
                traceback.print_exc()

        print(f"[MicroactionRegistry] Discovery complete. Registered {len(self._lenses)} lenses.")

    def _find_microaction_class(self, module, module_name: str):
        """
        Find the BaseLensMicroactions subclass in a module.

        Args:
            module: Imported module
            module_name: Name of the module file (e.g., 'part_microactions')

        Returns:
            Microaction class or None
        """
        # Expected class name: part_microactions → PartLensMicroactions
        lens_base = module_name.replace('_microactions', '')
        expected_class_name = ''.join(word.capitalize() for word in lens_base.split('_')) + 'LensMicroactions'

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # Check if it's a class and subclass of BaseLensMicroactions
            if (
                isinstance(attr, type) and
                issubclass(attr, BaseLensMicroactions) and
                attr is not BaseLensMicroactions
            ):
                return attr

        return None

    def _register_lens(self, lens: BaseLensMicroactions) -> None:
        """
        Register a lens and its entity types.

        Args:
            lens: Lens instance to register
        """
        lens_name = lens.lens_name
        self._lenses[lens_name] = lens

        # Register entity type mappings
        for entity_type in lens.entity_types:
            entity_type = entity_type.lower()

            # Warn if entity type already registered
            if entity_type in self._entity_type_to_lens:
                print(
                    f"[MicroactionRegistry] Warning: Entity type '{entity_type}' "
                    f"already registered to {self._entity_type_to_lens[entity_type]}, "
                    f"overwriting with {lens_name}"
                )

            self._entity_type_to_lens[entity_type] = lens_name

        print(
            f"[MicroactionRegistry] ✓ Registered: {lens_name} "
            f"({len(lens.entity_types)} entity types)"
        )

    async def get_suggestions(
        self,
        lens_name: str,
        entity_type: str,
        entity_id: str,
        entity_data: Dict,
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str] = None
    ) -> List[ActionSuggestion]:
        """
        Get action suggestions for an entity from a specific lens.

        Args:
            lens_name: Lens to use (e.g., "part_lens")
            entity_type: Entity type (e.g., "part")
            entity_id: Entity ID
            entity_data: Entity data from search result
            user_role: User's role
            yacht_id: Yacht ID
            query_intent: Optional query intent

        Returns:
            List of ActionSuggestion objects

        Raises:
            ValueError: If lens not found
            MicroactionExecutionError: If action generation fails
        """
        if lens_name not in self._lenses:
            # Fail gracefully with empty list
            print(f"[MicroactionRegistry] Warning: Lens '{lens_name}' not found")
            return []

        lens = self._lenses[lens_name]

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
            # Fail gracefully with empty list
            print(f"[MicroactionRegistry] Error getting suggestions from {lens_name}: {e}")
            return []

    def get_lens(self, lens_name: str) -> Optional[BaseLensMicroactions]:
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


# Module-level test function
if __name__ == "__main__":
    """Test the registry with a mock Supabase client."""
    import asyncio

    class MockClient:
        """Mock Supabase client for testing."""
        pass

    async def test_registry():
        print("Testing MicroactionRegistry...")
        mock_db = MockClient()

        registry = MicroactionRegistry(mock_db)
        registry.discover_and_register()

        print(f"\nLenses found: {registry.get_lens_names()}")

        print("\nMicroaction registry test complete!")

    asyncio.run(test_registry())
