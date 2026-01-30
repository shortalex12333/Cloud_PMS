"""Microaction Registry - Auto-Discovery System"""
import pkgutil
import importlib
from pathlib import Path
from typing import List, Dict, Optional
from supabase import Client
from .base_microaction import BaseLensMicroactions, ActionSuggestion


class MicroactionRegistry:
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
        self._lenses: Dict[str, BaseLensMicroactions] = {}
        self._entity_type_to_lens: Dict[str, str] = {}
        self._initialized = True

    def discover_and_register(self) -> None:
        print("[MicroactionRegistry] Discovering lens microactions...")
        microactions_path = Path(__file__).parent / "lens_microactions"
        if not microactions_path.exists():
            return

        for module_info in pkgutil.iter_modules([str(microactions_path)]):
            if not module_info.name.endswith('_microactions'):
                continue
            try:
                module = importlib.import_module(f"microactions.lens_microactions.{module_info.name}")
                lens_class = self._find_microaction_class(module)
                if lens_class:
                    lens_instance = lens_class(self.db)
                    lens_instance.validate()
                    self._register_lens(lens_instance)
            except Exception as e:
                print(f"[MicroactionRegistry] Error loading {module_info.name}: {e}")

    def _find_microaction_class(self, module):
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseLensMicroactions) and attr is not BaseLensMicroactions:
                return attr
        return None

    def _register_lens(self, lens: BaseLensMicroactions) -> None:
        lens_name = lens.lens_name
        self._lenses[lens_name] = lens
        for entity_type in lens.entity_types:
            self._entity_type_to_lens[entity_type.lower()] = lens_name
        print(f"[MicroactionRegistry] ✓ Registered: {lens_name} ({len(lens.entity_types)} entity types)")

    async def get_suggestions(self, lens_name: str, entity_type: str, entity_id: str,
                              entity_data: Dict, user_role: str, yacht_id: str,
                              query_intent: Optional[str] = None) -> List[ActionSuggestion]:
        if lens_name not in self._lenses:
            return []
        lens = self._lenses[lens_name]
        try:
            return await lens.get_suggestions(entity_type, entity_id, entity_data, user_role, yacht_id, query_intent)
        except Exception as e:
            print(f"[MicroactionRegistry] Error getting suggestions from {lens_name}: {e}")
            return []

    def get_lens_names(self) -> List[str]:
        return list(self._lenses.keys())
