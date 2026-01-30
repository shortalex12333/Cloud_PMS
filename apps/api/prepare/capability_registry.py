"""Capability Registry - Auto-Discovery System"""
import pkgutil
import importlib
from pathlib import Path
from typing import List, Dict, Optional
from supabase import Client
from .base_capability import BaseLensCapability, CapabilityMapping, SearchResult, CapabilityExecutionError


class CapabilityRegistry:
    _instance = None

    def __new__(cls, db: Client = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db: Client):
        if self._initialized:
            return
        self.db = db
        self._lenses: Dict[str, BaseLensCapability] = {}
        self._entity_to_lens: Dict[str, str] = {}
        self._entity_mappings: Dict[str, CapabilityMapping] = {}
        self._initialized = True

    def discover_and_register(self) -> None:
        print("[CapabilityRegistry] Discovering lens capabilities...")
        capabilities_path = Path(__file__).parent / "capabilities"
        if not capabilities_path.exists():
            return

        for module_info in pkgutil.iter_modules([str(capabilities_path)]):
            if not module_info.name.endswith('_capabilities'):
                continue
            try:
                module = importlib.import_module(f"prepare.capabilities.{module_info.name}")
                lens_class = self._find_capability_class(module)
                if lens_class:
                    lens_instance = lens_class(self.db)
                    lens_instance.validate()
                    if lens_instance.enabled:
                        self._register_lens(lens_instance)
            except Exception as e:
                print(f"[CapabilityRegistry] Error loading {module_info.name}: {e}")

    def _find_capability_class(self, module):
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseLensCapability) and attr is not BaseLensCapability:
                return attr
        return None

    def _register_lens(self, lens: BaseLensCapability) -> None:
        lens_name = lens.lens_name
        self._lenses[lens_name] = lens
        mappings = lens.get_entity_mappings()
        for mapping in mappings:
            entity_type = mapping.entity_type.upper()
            self._entity_to_lens[entity_type] = lens_name
            self._entity_mappings[entity_type] = mapping
        print(f"[CapabilityRegistry] ✓ Registered: {lens_name} ({len(mappings)} entity types)")

    async def search(self, entity_type: str, yacht_id: str, search_term: str, limit: int = 20) -> List[SearchResult]:
        entity_type = entity_type.upper()
        if entity_type not in self._entity_to_lens:
            raise ValueError(f"Unknown entity type: {entity_type}")
        lens_name = self._entity_to_lens[entity_type]
        mapping = self._entity_mappings[entity_type]
        lens = self._lenses[lens_name]
        return await lens.execute_capability(mapping.capability_name, yacht_id, search_term, limit)

    def get_lens_names(self) -> List[str]:
        return list(self._lenses.keys())

    def get_all_entity_types(self) -> List[str]:
        return list(self._entity_to_lens.keys())
