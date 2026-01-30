"""
Part Lens - Search Capabilities
================================

Part Lens search capabilities for inventory management.

Entity Types Handled:
- PART_NUMBER: Search by part number
- PART_NAME: Search by part name
- PART: Generic part search
- MANUFACTURER: Search by manufacturer/brand
- PART_BRAND: Alias for manufacturer search
- PART_STORAGE_LOCATION: Search inventory by storage location
- PART_CATEGORY: Search by category
- PART_SUBCATEGORY: Search by subcategory
- SHOPPING_LIST_ITEM: Search shopping list
- PART_EQUIPMENT_USAGE: Search part usage by equipment

Tables Searched:
- pms_parts: Core part data
- pms_inventory_stock: Stock levels by location
- pms_shopping_list_items: Procurement requests
- pms_part_usage: Part-to-equipment relationships

Owner: Part Lens team
"""

from typing import List, Dict, Any
from ..base_capability import (
    BaseLensCapability,
    CapabilityMapping,
    SearchResult,
    CapabilityExecutionError
)


class PartLensCapability(BaseLensCapability):
    """Part Lens search capabilities."""

    lens_name = "part_lens"
    enabled = True

    def __init__(self, db_client):
        """
        Initialize Part Lens capabilities.

        Args:
            db_client: Supabase client or async postgres client
        """
        self.db = db_client

    def get_entity_mappings(self) -> List[CapabilityMapping]:
        """
        Define all Part Lens entity-to-capability mappings.

        Returns:
            List of CapabilityMapping objects
        """
        return [
            # ===== CORE PART SEARCH =====
            CapabilityMapping(
                entity_type="PART_NUMBER",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="part_number",
                result_type="part",
                priority=3,  # High priority for exact part numbers
            ),
            CapabilityMapping(
                entity_type="PART_NAME",
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="name",
                result_type="part",
                priority=2,
            ),
            CapabilityMapping(
                entity_type="PART",  # Align with extraction
                capability_name="part_by_part_number_or_name",
                table_name="pms_parts",
                search_column="name",
                result_type="part",
                priority=2,
            ),

            # ===== MANUFACTURER SEARCH =====
            CapabilityMapping(
                entity_type="MANUFACTURER",
                capability_name="part_by_manufacturer",
                table_name="pms_parts",
                search_column="manufacturer",
                result_type="part",
                priority=1,
            ),
            CapabilityMapping(
                entity_type="PART_BRAND",  # Alias for 'brand' entity type
                capability_name="part_by_manufacturer",
                table_name="pms_parts",
                search_column="manufacturer",
                result_type="part",
                priority=1,
            ),

            # ===== INVENTORY SEARCH =====
            CapabilityMapping(
                entity_type="PART_STORAGE_LOCATION",  # Renamed from LOCATION
                capability_name="inventory_by_storage_location",
                table_name="pms_inventory_stock",
                search_column="storage_location",
                result_type="inventory_stock",
                priority=1,
            ),

            # ===== CATEGORY SEARCH =====
            CapabilityMapping(
                entity_type="PART_CATEGORY",
                capability_name="part_by_category",
                table_name="pms_parts",
                search_column="category",
                result_type="part",
                priority=1,
            ),
            CapabilityMapping(
                entity_type="PART_SUBCATEGORY",
                capability_name="part_by_category",
                table_name="pms_parts",
                search_column="subcategory",
                result_type="part",
                priority=1,
            ),

            # ===== SHOPPING LIST SEARCH =====
            CapabilityMapping(
                entity_type="SHOPPING_LIST_ITEM",
                capability_name="shopping_list_by_part",
                table_name="pms_shopping_list_items",
                search_column="part_name",
                result_type="shopping_list_item",
                priority=1,
            ),

            # ===== PART USAGE SEARCH =====
            CapabilityMapping(
                entity_type="PART_EQUIPMENT_USAGE",
                capability_name="part_usage_by_equipment",
                table_name="pms_part_usage",
                search_column="equipment_name",
                result_type="part_usage",
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
        """
        Route to the correct capability method.

        Args:
            capability_name: Name of capability method to call
            yacht_id: Tenant isolation UUID
            search_term: User's search query
            limit: Maximum results to return

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If capability doesn't exist
            CapabilityExecutionError: If execution fails
        """
        method = getattr(self, capability_name, None)
        if not method:
            raise ValueError(
                f"Part Lens: Capability '{capability_name}' not found. "
                f"Check part_capabilities.py"
            )

        try:
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
                    source_table=r.get("source_table", "")
                )
                for r in results
            ]
        except Exception as e:
            # Find mapping to get table/column info
            mapping = None
            for m in self.get_entity_mappings():
                if m.capability_name == capability_name:
                    mapping = m
                    break

            table_name = mapping.table_name if mapping else "unknown"
            column_name = mapping.search_column if mapping else "unknown"

            raise CapabilityExecutionError(
                lens_name=self.lens_name,
                capability_name=capability_name,
                table_name=table_name,
                column_name=column_name,
                error=e
            )

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

        Uses similarity scoring and ILIKE for flexible matching.

        Args:
            yacht_id: Tenant isolation UUID
            search_term: Search query
            limit: Max results

        Returns:
            List of part records
        """
        try:
            # Use Supabase client
            result = self.db.table("pms_parts").select(
                "id, part_number, name, manufacturer, category, subcategory, "
                "is_critical, min_level"
            ).eq(
                "yacht_id", yacht_id
            ).or_(
                f"part_number.ilike.%{search_term}%,"
                f"name.ilike.%{search_term}%,"
                f"manufacturer.ilike.%{search_term}%"
            ).limit(limit).execute()

            parts = result.data or []

            # Format results
            return [
                {
                    "id": part["id"],
                    "type": "part",
                    "title": f"{part['part_number']} - {part['name']}",
                    "score": self._calculate_part_score(part, search_term),
                    "source_table": "pms_parts",
                    "metadata": {
                        "part_number": part["part_number"],
                        "manufacturer": part.get("manufacturer"),
                        "category": part.get("category"),
                        "subcategory": part.get("subcategory"),
                        "is_critical": part.get("is_critical", False),
                        "min_level": part.get("min_level", 0),
                    }
                }
                for part in parts
            ]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: part_by_part_number_or_name failed. "
                f"Table: pms_parts, Error: {str(e)}"
            )

    async def part_by_manufacturer(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search parts by manufacturer."""
        try:
            result = self.db.table("pms_parts").select(
                "id, part_number, name, manufacturer, category"
            ).eq(
                "yacht_id", yacht_id
            ).ilike(
                "manufacturer", f"%{search_term}%"
            ).limit(limit).execute()

            parts = result.data or []

            return [
                {
                    "id": part["id"],
                    "type": "part",
                    "title": f"{part['name']} ({part['manufacturer']})",
                    "score": 0.8 if search_term.lower() in part.get("manufacturer", "").lower() else 0.5,
                    "source_table": "pms_parts",
                    "metadata": {
                        "part_number": part["part_number"],
                        "manufacturer": part["manufacturer"],
                        "category": part.get("category"),
                    }
                }
                for part in parts
            ]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: part_by_manufacturer failed. "
                f"Table: pms_parts, Column: manufacturer. Error: {str(e)}"
            )

    async def inventory_by_storage_location(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search inventory by storage location."""
        try:
            result = self.db.table("pms_inventory_stock").select(
                "id, part_id, storage_location, on_hand, allocated, available, "
                "pms_parts(part_number, name)"
            ).eq(
                "yacht_id", yacht_id
            ).ilike(
                "storage_location", f"%{search_term}%"
            ).limit(limit).execute()

            stocks = result.data or []

            return [
                {
                    "id": stock["id"],
                    "type": "inventory_stock",
                    "title": f"{stock['pms_parts']['name']} @ {stock['storage_location']} ({stock['on_hand']} units)",
                    "score": 0.8,
                    "source_table": "pms_inventory_stock",
                    "metadata": {
                        "part_id": stock["part_id"],
                        "part_name": stock["pms_parts"]["name"],
                        "part_number": stock["pms_parts"]["part_number"],
                        "storage_location": stock["storage_location"],
                        "on_hand": stock["on_hand"],
                        "allocated": stock["allocated"],
                        "available": stock["available"],
                    }
                }
                for stock in stocks
            ]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: inventory_by_storage_location failed. "
                f"Table: pms_inventory_stock, Column: storage_location. Error: {str(e)}"
            )

    async def part_by_category(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search parts by category or subcategory."""
        try:
            result = self.db.table("pms_parts").select(
                "id, part_number, name, manufacturer, category, subcategory"
            ).eq(
                "yacht_id", yacht_id
            ).or_(
                f"category.ilike.%{search_term}%,"
                f"subcategory.ilike.%{search_term}%"
            ).limit(limit).execute()

            parts = result.data or []

            return [
                {
                    "id": part["id"],
                    "type": "part",
                    "title": f"{part['name']} ({part['category']})",
                    "score": 0.7,
                    "source_table": "pms_parts",
                    "metadata": {
                        "part_number": part["part_number"],
                        "manufacturer": part.get("manufacturer"),
                        "category": part["category"],
                        "subcategory": part.get("subcategory"),
                    }
                }
                for part in parts
            ]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: part_by_category failed. "
                f"Table: pms_parts, Column: category/subcategory. Error: {str(e)}"
            )

    async def shopping_list_by_part(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search shopping list items."""
        try:
            result = self.db.table("pms_shopping_list_items").select(
                "id, part_id, quantity_needed, status, priority, urgency, notes, "
                "pms_parts(part_number, name)"
            ).eq(
                "yacht_id", yacht_id
            ).ilike(
                "pms_parts.name", f"%{search_term}%"
            ).limit(limit).execute()

            items = result.data or []

            return [
                {
                    "id": item["id"],
                    "type": "shopping_list_item",
                    "title": f"{item['pms_parts']['name']} - {item['status']} (qty: {item['quantity_needed']})",
                    "score": 0.8,
                    "source_table": "pms_shopping_list_items",
                    "metadata": {
                        "part_id": item["part_id"],
                        "part_name": item["pms_parts"]["name"],
                        "part_number": item["pms_parts"]["part_number"],
                        "quantity_needed": item["quantity_needed"],
                        "status": item["status"],
                        "priority": item.get("priority"),
                        "urgency": item.get("urgency"),
                        "notes": item.get("notes"),
                    }
                }
                for item in items
            ]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: shopping_list_by_part failed. "
                f"Table: pms_shopping_list_items. Error: {str(e)}"
            )

    async def part_usage_by_equipment(
        self,
        yacht_id: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search part usage by equipment."""
        try:
            result = self.db.table("pms_part_usage").select(
                "id, part_id, equipment_id, quantity_per_service, "
                "pms_parts(part_number, name), "
                "pms_equipment(name, equipment_type)"
            ).eq(
                "yacht_id", yacht_id
            ).ilike(
                "pms_equipment.name", f"%{search_term}%"
            ).limit(limit).execute()

            usages = result.data or []

            return [
                {
                    "id": usage["id"],
                    "type": "part_usage",
                    "title": f"{usage['pms_parts']['name']} used in {usage['pms_equipment']['name']}",
                    "score": 0.7,
                    "source_table": "pms_part_usage",
                    "metadata": {
                        "part_id": usage["part_id"],
                        "part_name": usage["pms_parts"]["name"],
                        "part_number": usage["pms_parts"]["part_number"],
                        "equipment_id": usage["equipment_id"],
                        "equipment_name": usage["pms_equipment"]["name"],
                        "equipment_type": usage["pms_equipment"]["equipment_type"],
                        "quantity_per_service": usage.get("quantity_per_service"),
                    }
                }
                for usage in usages
            ]
        except Exception as e:
            raise RuntimeError(
                f"Part Lens: part_usage_by_equipment failed. "
                f"Table: pms_part_usage. Error: {str(e)}"
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _calculate_part_score(self, part: Dict, search_term: str) -> float:
        """
        Calculate relevance score for part search.

        Scoring:
        - Exact part number match: 1.0
        - Part number contains: 0.9
        - Exact name match: 0.85
        - Name contains: 0.7
        - Manufacturer match: 0.5
        """
        search_lower = search_term.lower()
        part_number_lower = part.get("part_number", "").lower()
        name_lower = part.get("name", "").lower()
        manufacturer_lower = part.get("manufacturer", "").lower()

        if part_number_lower == search_lower:
            return 1.0
        elif search_lower in part_number_lower:
            return 0.9
        elif name_lower == search_lower:
            return 0.85
        elif search_lower in name_lower:
            return 0.7
        elif search_lower in manufacturer_lower:
            return 0.5
        else:
            return 0.3
