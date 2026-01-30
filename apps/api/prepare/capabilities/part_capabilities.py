"""Part Lens Capabilities"""
from typing import List, Dict, Any
from ..base_capability import BaseLensCapability, CapabilityMapping, SearchResult


class PartLensCapability(BaseLensCapability):
    lens_name = "part_lens"
    enabled = True

    def get_entity_mappings(self) -> List[CapabilityMapping]:
        return [
            CapabilityMapping(entity_type="PART_NUMBER", capability_name="part_by_part_number_or_name", table_name="pms_parts", search_column="part_number", result_type="part", priority=5),
            CapabilityMapping(entity_type="PART_NAME", capability_name="part_by_part_number_or_name", table_name="pms_parts", search_column="name", result_type="part", priority=4),
            CapabilityMapping(entity_type="PART", capability_name="part_by_part_number_or_name", table_name="pms_parts", search_column="name", result_type="part", priority=3),
            CapabilityMapping(entity_type="MANUFACTURER", capability_name="part_by_manufacturer", table_name="pms_parts", search_column="manufacturer", result_type="part", priority=3),
            CapabilityMapping(entity_type="PART_BRAND", capability_name="part_by_manufacturer", table_name="pms_parts", search_column="manufacturer", result_type="part", priority=3),
            CapabilityMapping(entity_type="PART_STORAGE_LOCATION", capability_name="inventory_by_storage_location", table_name="pms_inventory_stock", search_column="location", result_type="inventory_stock", priority=2),
            CapabilityMapping(entity_type="PART_CATEGORY", capability_name="part_by_category", table_name="pms_parts", search_column="category", result_type="part", priority=2),
            CapabilityMapping(entity_type="PART_SUBCATEGORY", capability_name="part_by_category", table_name="pms_parts", search_column="category", result_type="part", priority=2),
            CapabilityMapping(entity_type="SHOPPING_LIST_ITEM", capability_name="shopping_list_by_part", table_name="pms_shopping_list_items", search_column="part_id", result_type="shopping_list_item", priority=1),
            CapabilityMapping(entity_type="PART_EQUIPMENT_USAGE", capability_name="part_usage_by_equipment", table_name="pms_part_usage", search_column="equipment_id", result_type="part_usage", priority=1),
        ]

    async def execute_capability(self, capability_name: str, yacht_id: str, search_term: str, limit: int = 20) -> List[SearchResult]:
        if capability_name == "part_by_part_number_or_name":
            raw_results = await self.part_by_part_number_or_name(yacht_id, search_term, limit)
            return self._format_part_results(raw_results, capability_name)
        elif capability_name == "part_by_manufacturer":
            raw_results = await self.part_by_manufacturer(yacht_id, search_term, limit)
            return self._format_part_results(raw_results, capability_name)
        elif capability_name == "part_by_category":
            raw_results = await self.part_by_category(yacht_id, search_term, limit)
            return self._format_part_results(raw_results, capability_name)
        elif capability_name == "inventory_by_storage_location":
            raw_results = await self.inventory_by_storage_location(yacht_id, search_term, limit)
            return self._format_inventory_results(raw_results, capability_name)
        elif capability_name == "shopping_list_by_part":
            raw_results = await self.shopping_list_by_part(yacht_id, search_term, limit)
            return self._format_shopping_list_results(raw_results, capability_name)
        elif capability_name == "part_usage_by_equipment":
            raw_results = await self.part_usage_by_equipment(yacht_id, search_term, limit)
            return self._format_usage_results(raw_results, capability_name)
        raise ValueError(f"Unknown capability: {capability_name}")

    async def part_by_part_number_or_name(self, yacht_id: str, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        result = self.db.table("pms_parts").select("id, part_number, name, manufacturer, category, is_critical, min_level, quantity_on_hand").eq("yacht_id", yacht_id).or_(f"part_number.ilike.%{search_term}%,name.ilike.%{search_term}%").limit(limit).execute()
        return result.data if result.data else []

    async def part_by_manufacturer(self, yacht_id: str, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        result = self.db.table("pms_parts").select("id, part_number, name, manufacturer, category, is_critical").eq("yacht_id", yacht_id).ilike("manufacturer", f"%{search_term}%").limit(limit).execute()
        return result.data if result.data else []

    async def part_by_category(self, yacht_id: str, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        result = self.db.table("pms_parts").select("id, part_number, name, category, manufacturer").eq("yacht_id", yacht_id).ilike("category", f"%{search_term}%").limit(limit).execute()
        return result.data if result.data else []

    async def inventory_by_storage_location(self, yacht_id: str, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        result = self.db.table("pms_inventory_stock").select("id, part_id, location, quantity, min_quantity").eq("yacht_id", yacht_id).ilike("location", f"%{search_term}%").limit(limit).execute()
        return result.data if result.data else []

    async def shopping_list_by_part(self, yacht_id: str, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        parts_result = await self.part_by_part_number_or_name(yacht_id, search_term, limit)
        if not parts_result:
            return []
        part_ids = [part["id"] for part in parts_result]
        result = self.db.table("pms_shopping_list_items").select("id, part_id, quantity_needed, priority, notes").eq("yacht_id", yacht_id).in_("part_id", part_ids).limit(limit).execute()
        return result.data if result.data else []

    async def part_usage_by_equipment(self, yacht_id: str, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        equipment_result = self.db.table("pms_equipment").select("id, name").eq("yacht_id", yacht_id).ilike("name", f"%{search_term}%").execute()
        if not equipment_result.data:
            return []
        equipment_ids = [eq["id"] for eq in equipment_result.data]
        result = self.db.table("pms_part_usage").select("id, part_id, equipment_id, quantity_per_service").eq("yacht_id", yacht_id).in_("equipment_id", equipment_ids).limit(limit).execute()
        return result.data if result.data else []

    def _format_part_results(self, parts: List[Dict[str, Any]], capability_name: str) -> List[SearchResult]:
        return self._format_results(parts, "part", capability_name, "pms_parts",
            title_fn=lambda p: f"{p.get('part_number', 'N/A')} - {p.get('name', 'Unnamed')}",
            subtitle_fn=lambda p: f"{p.get('manufacturer', '')} | {p.get('category', '')}".strip(" |"),
            score_fn=lambda p: 5 if p.get('is_critical') else 3)

    def _format_inventory_results(self, inventory: List[Dict[str, Any]], capability_name: str) -> List[SearchResult]:
        return self._format_results(inventory, "inventory_stock", capability_name, "pms_inventory_stock",
            title_fn=lambda i: f"Stock at {i.get('location', 'Unknown Location')}",
            subtitle_fn=lambda i: f"Quantity: {i.get('quantity', 0)} | Min: {i.get('min_quantity', 0)}")

    def _format_shopping_list_results(self, items: List[Dict[str, Any]], capability_name: str) -> List[SearchResult]:
        return self._format_results(items, "shopping_list_item", capability_name, "pms_shopping_list_items",
            title_fn=lambda i: f"Shopping List: Part {i.get('part_id')}",
            subtitle_fn=lambda i: f"Needed: {i.get('quantity_needed', 0)} | Priority: {i.get('priority', 'Normal')}")

    def _format_usage_results(self, usage: List[Dict[str, Any]], capability_name: str) -> List[SearchResult]:
        return self._format_results(usage, "part_usage", capability_name, "pms_part_usage",
            title_fn=lambda u: f"Part Usage: {u.get('part_id')}",
            subtitle_fn=lambda u: f"Equipment: {u.get('equipment_id')} | Qty/Service: {u.get('quantity_per_service', 0)}")
