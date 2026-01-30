"""
Part Lens Capabilities
======================
Search capabilities for Part Lens domain.

Entity Types Supported:
- PART_NUMBER, PART_NAME, PART
- MANUFACTURER, PART_BRAND
- PART_STORAGE_LOCATION
- PART_CATEGORY, PART_SUBCATEGORY
- SHOPPING_LIST_ITEM
- PART_EQUIPMENT_USAGE

Tables Queried:
- pms_parts
- pms_inventory_stock
- pms_shopping_list_items
- pms_part_usage
"""

from typing import List, Dict, Any
from ..base_capability import (
    BaseLensCapability,
    CapabilityMapping,
    SearchResult
)


class PartLensCapability(BaseLensCapability):
    """Part Lens search implementation."""

    lens_name = "part_lens"
    enabled = True

    def get_entity_mappings(self) -> List[CapabilityMapping]:
        """
        Define entity → capability mappings for Part Lens.

        Returns 10 entity type mappings across 6 capabilities.
        """
        return [
            # Part identification (highest priority)
            CapabilityMapping(
                entity_type="PART_NUMBER",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="part_number",
                result_type="part",
                priority=5
            ),
            CapabilityMapping(
                entity_type="PART_NAME",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="name",
                result_type="part",
                priority=4
            ),
            CapabilityMapping(
                entity_type="PART",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="name",
                result_type="part",
                priority=3
            ),

            # Manufacturer/brand
            CapabilityMapping(
                entity_type="MANUFACTURER",
                capability_name="part_by_manufacturer",
                table_name="pms_parts",
                search_column="manufacturer",
                result_type="part",
                priority=3
            ),
            CapabilityMapping(
                entity_type="PART_BRAND",
                capability_name="part_by_manufacturer",
                table_name="pms_parts",
                search_column="manufacturer",
                result_type="part",
                priority=3
            ),

            # Storage location
            CapabilityMapping(
                entity_type="PART_STORAGE_LOCATION",
                capability_name="inventory_by_storage_location",
                table_name="pms_inventory_stock",
                search_column="storage_location_id",
                result_type="inventory_stock",
                priority=2
            ),

            # Category/subcategory
            CapabilityMapping(
                entity_type="PART_CATEGORY",
                capability_name="part_by_category",
                table_name="pms_parts",
                search_column="category",
                result_type="part",
                priority=2
            ),
            CapabilityMapping(
                entity_type="PART_SUBCATEGORY",
                capability_name="part_by_category",
                table_name="pms_parts",
                search_column="subcategory",
                result_type="part",
                priority=2
            ),

            # Shopping list
            CapabilityMapping(
                entity_type="SHOPPING_LIST_ITEM",
                capability_name="shopping_list_by_part",
                table_name="pms_shopping_list_items",
                search_column="part_id",
                result_type="shopping_list_item",
                priority=1
            ),

            # Equipment usage
            CapabilityMapping(
                entity_type="PART_EQUIPMENT_USAGE",
                capability_name="part_usage_by_equipment",
                table_name="pms_part_usage",
                search_column="equipment_id",
                result_type="part_usage",
                priority=1
            ),
        ]

    async def execute_capability(
        self,
        capability_name: str,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Route capability execution to the appropriate method.

        Args:
            capability_name: Name of capability to execute
            yacht_id: Yacht ID for RLS filtering
            search_term: Search query
            limit: Maximum results

        Returns:
            List of SearchResult objects
        """
        # Route to appropriate capability method
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

        else:
            raise ValueError(f"Unknown capability: {capability_name}")

    # =========================================================================
    # CAPABILITY IMPLEMENTATIONS
    # =========================================================================

    async def part_by_part_number_or_name(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search parts by part number or name.

        Args:
            yacht_id: Yacht ID
            search_term: Search query
            limit: Maximum results

        Returns:
            List of part records
        """
        result = self.db.table("pms_parts").select(
            "id, part_number, name, manufacturer, category, is_critical, min_level, quantity_on_hand"
        ).eq("yacht_id", yacht_id).or_(
            f"part_number.ilike.%{search_term}%,"
            f"name.ilike.%{search_term}%"
        ).limit(limit).execute()

        return result.data if result.data else []

    async def part_by_manufacturer(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search parts by manufacturer/brand.

        Args:
            yacht_id: Yacht ID
            search_term: Manufacturer name
            limit: Maximum results

        Returns:
            List of part records
        """
        result = self.db.table("pms_parts").select(
            "id, part_number, name, manufacturer, category, is_critical"
        ).eq("yacht_id", yacht_id).ilike(
            "manufacturer", f"%{search_term}%"
        ).limit(limit).execute()

        return result.data if result.data else []

    async def part_by_category(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search parts by category.

        Args:
            yacht_id: Yacht ID
            search_term: Category name
            limit: Maximum results

        Returns:
            List of part records
        """
        result = self.db.table("pms_parts").select(
            "id, part_number, name, category, manufacturer"
        ).eq("yacht_id", yacht_id).ilike(
            "category", f"%{search_term}%"
        ).limit(limit).execute()

        return result.data if result.data else []

    async def inventory_by_storage_location(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search inventory by storage location.

        Args:
            yacht_id: Yacht ID
            search_term: Location name
            limit: Maximum results

        Returns:
            List of inventory stock records
        """
        # Search pms_inventory_stock by location field
        result = self.db.table("pms_inventory_stock").select(
            "id, part_id, location, quantity, min_quantity"
        ).eq("yacht_id", yacht_id).ilike(
            "location", f"%{search_term}%"
        ).limit(limit).execute()

        return result.data if result.data else []

    async def shopping_list_by_part(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search shopping list items related to parts.

        Args:
            yacht_id: Yacht ID
            search_term: Part search term
            limit: Maximum results

        Returns:
            List of shopping list item records
        """
        # First find matching parts
        parts_result = await self.part_by_part_number_or_name(yacht_id, search_term, limit)

        if not parts_result:
            return []

        part_ids = [part["id"] for part in parts_result]

        # Then find shopping list items for those parts
        result = self.db.table("pms_shopping_list_items").select(
            "id, part_id, quantity_needed, priority, notes"
        ).eq("yacht_id", yacht_id).in_(
            "part_id", part_ids
        ).limit(limit).execute()

        return result.data if result.data else []

    async def part_usage_by_equipment(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search part usage by equipment.

        Args:
            yacht_id: Yacht ID
            search_term: Equipment name
            limit: Maximum results

        Returns:
            List of part usage records
        """
        # Search equipment first
        equipment_result = self.db.table("pms_equipment").select(
            "id, name"
        ).eq("yacht_id", yacht_id).ilike(
            "name", f"%{search_term}%"
        ).execute()

        if not equipment_result.data:
            return []

        equipment_ids = [eq["id"] for eq in equipment_result.data]

        # Find part usage for that equipment
        result = self.db.table("pms_part_usage").select(
            "id, part_id, equipment_id, quantity_per_service"
        ).eq("yacht_id", yacht_id).in_(
            "equipment_id", equipment_ids
        ).limit(limit).execute()

        return result.data if result.data else []

    # =========================================================================
    # RESULT FORMATTING
    # =========================================================================

    def _format_part_results(
        self,
        parts: List[Dict[str, Any]],
        capability_name: str
    ) -> List[SearchResult]:
        """Format part records as SearchResults."""
        return self._format_results(
            raw_results=parts,
            result_type="part",
            capability_name=capability_name,
            table_name="pms_parts",
            title_fn=lambda p: f"{p.get('part_number', 'N/A')} - {p.get('name', 'Unnamed')}",
            subtitle_fn=lambda p: f"{p.get('manufacturer', '')} | {p.get('category', '')}".strip(" |"),
            score_fn=lambda p: 5 if p.get('is_critical') else 3
        )

    def _format_inventory_results(
        self,
        inventory: List[Dict[str, Any]],
        capability_name: str
    ) -> List[SearchResult]:
        """Format inventory stock records as SearchResults."""
        return self._format_results(
            raw_results=inventory,
            result_type="inventory_stock",
            capability_name=capability_name,
            table_name="pms_inventory_stock",
            title_fn=lambda i: f"Stock at {i.get('location', 'Unknown Location')}",
            subtitle_fn=lambda i: f"Quantity: {i.get('quantity', 0)} | Min: {i.get('min_quantity', 0)}",
            score_fn=lambda i: 1
        )

    def _format_shopping_list_results(
        self,
        items: List[Dict[str, Any]],
        capability_name: str
    ) -> List[SearchResult]:
        """Format shopping list items as SearchResults."""
        return self._format_results(
            raw_results=items,
            result_type="shopping_list_item",
            capability_name=capability_name,
            table_name="pms_shopping_list_items",
            title_fn=lambda i: f"Shopping List: Part {i.get('part_id')}",
            subtitle_fn=lambda i: f"Needed: {i.get('quantity_needed', 0)} | Priority: {i.get('priority', 'Normal')}",
            score_fn=lambda i: 3 if i.get('priority') == 'High' else 1
        )

    def _format_usage_results(
        self,
        usage: List[Dict[str, Any]],
        capability_name: str
    ) -> List[SearchResult]:
        """Format part usage records as SearchResults."""
        return self._format_results(
            raw_results=usage,
            result_type="part_usage",
            capability_name=capability_name,
            table_name="pms_part_usage",
            title_fn=lambda u: f"Part Usage: {u.get('part_id')}",
            subtitle_fn=lambda u: f"Equipment: {u.get('equipment_id')} | Qty/Service: {u.get('quantity_per_service', 0)}",
            score_fn=lambda u: 1
        )
