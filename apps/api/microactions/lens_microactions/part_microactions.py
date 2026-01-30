"""
Part Lens Microactions
======================
Context-aware action suggestions for Part Lens entities.

Features:
- Stock-based filtering (hide consume/transfer if on_hand = 0)
- Role-based filtering (from action_router registry)
- Intent-based prioritization (boost priority if query intent matches action)
- Prefill data generation (pre-populate form fields)

Entity Types:
- part
- inventory_stock
- shopping_list_item
"""

from typing import List, Dict, Any, Optional
from ..base_microaction import (
    BaseLensMicroactions,
    ActionSuggestion,
    ActionVariant
)

# Import action registry for getting available actions
try:
    from action_router.registry import get_actions_for_domain
except ImportError:
    # Fallback if action_router not available
    def get_actions_for_domain(domain: str, role: str = None):
        return []


class PartLensMicroactions(BaseLensMicroactions):
    """Part Lens microaction implementation."""

    lens_name = "part_lens"
    entity_types = ["part", "inventory_stock", "shopping_list_item"]

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
        Generate action suggestions for a part entity.

        Args:
            entity_type: "part", "inventory_stock", or "shopping_list_item"
            entity_id: Part ID or stock ID
            entity_data: Entity data from search result
            user_role: User's role (for role-based filtering)
            yacht_id: Yacht ID
            query_intent: Optional query intent for prioritization

        Returns:
            List of ActionSuggestion objects with filtering and prefill data
        """
        if entity_type == "part":
            return await self._get_part_actions(
                entity_id, entity_data, user_role, yacht_id, query_intent
            )
        elif entity_type == "inventory_stock":
            return await self._get_stock_actions(
                entity_id, entity_data, user_role, yacht_id, query_intent
            )
        elif entity_type == "shopping_list_item":
            return await self._get_shopping_list_actions(
                entity_id, entity_data, user_role, yacht_id, query_intent
            )
        else:
            return []

    # =========================================================================
    # PART ACTIONS
    # =========================================================================

    async def _get_part_actions(
        self,
        part_id: str,
        part_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str]
    ) -> List[ActionSuggestion]:
        """
        Generate actions for a part entity.

        Applies stock-based, role-based, and intent-based filtering.
        """
        # Get all available actions for parts domain (with role filtering)
        all_actions = get_actions_for_domain("parts", user_role)

        # Get stock information for this part
        stock_info = await self._get_stock_info(part_id, yacht_id)

        is_out_of_stock = stock_info["on_hand"] == 0
        is_low_stock = stock_info["on_hand"] <= stock_info.get("min_level", 0)
        is_critical = part_data.get("is_critical", False)

        suggestions = []

        for action in all_actions:
            action_id = action["action_id"]

            # Stock-based filtering
            if is_out_of_stock and action_id in [
                "consume_part",
                "transfer_part",
                "write_off_part"
            ]:
                # Can't consume/transfer/write-off if no stock
                continue

            # Calculate priority based on context
            priority = self._calculate_priority(
                action_id,
                query_intent,
                is_out_of_stock,
                is_low_stock,
                is_critical
            )

            # Get prefill data
            prefill_data = await self._get_prefill_data(
                action_id,
                part_id,
                part_data,
                stock_info,
                yacht_id
            )

            suggestions.append(ActionSuggestion(
                action_id=action_id,
                label=action["label"],
                variant=ActionVariant(action["variant"]),
                entity_id=part_id,
                entity_type="part",
                prefill_data=prefill_data,
                priority=priority
            ))

        return suggestions

    # =========================================================================
    # STOCK INFORMATION
    # =========================================================================

    async def _get_stock_info(self, part_id: str, yacht_id: str) -> Dict[str, Any]:
        """
        Get stock information for a part.

        Returns:
            Dict with on_hand, min_level, location
        """
        try:
            # Stock info is in pms_parts table directly
            result = self.db.table("pms_parts").select(
                "quantity_on_hand, min_level, location, primary_location_id"
            ).eq("id", part_id).eq("yacht_id", yacht_id).execute()

            if result.data and len(result.data) > 0:
                stock = result.data[0]
                return {
                    "on_hand": stock.get("quantity_on_hand", 0),
                    "min_level": stock.get("min_level", 0),
                    "location": stock.get("location"),
                    "primary_location_id": stock.get("primary_location_id")
                }

        except Exception as e:
            print(f"[PartLensMicroactions] Error fetching stock info: {e}")

        # Default: assume out of stock
        return {
            "on_hand": 0,
            "min_level": 0,
            "location": None,
            "primary_location_id": None
        }

    # =========================================================================
    # PRIORITY CALCULATION
    # =========================================================================

    def _calculate_priority(
        self,
        action_id: str,
        query_intent: Optional[str],
        is_out_of_stock: bool,
        is_low_stock: bool,
        is_critical: bool
    ) -> int:
        """
        Calculate action priority based on context.

        Args:
            action_id: Action identifier
            query_intent: Detected query intent (e.g., "receive_part")
            is_out_of_stock: Whether part has 0 stock
            is_low_stock: Whether stock is below min level
            is_critical: Whether part is critical

        Returns:
            Priority (1-5, higher = more important)
        """
        priority = 1  # Default

        # Intent-based boost
        if query_intent and action_id == query_intent:
            priority = 5  # Highest priority if intent matches

        # Stock-based prioritization
        elif is_out_of_stock:
            if action_id == "receive_part":
                priority = 4  # High priority to receive
            elif action_id == "add_to_shopping_list":
                priority = 3  # Medium-high to order
        elif is_low_stock:
            if action_id in ["receive_part", "add_to_shopping_list"]:
                priority = 3  # Medium-high to restock

        # Critical part boost
        if is_critical and action_id in ["receive_part", "add_to_shopping_list"]:
            priority = min(priority + 1, 5)  # Bump priority, max 5

        return priority

    # =========================================================================
    # PREFILL DATA
    # =========================================================================

    async def _get_prefill_data(
        self,
        action_id: str,
        part_id: str,
        part_data: Dict[str, Any],
        stock_info: Dict[str, Any],
        yacht_id: str
    ) -> Dict[str, Any]:
        """
        Generate prefill data for an action.

        Prefills form fields to speed up user interactions.
        """
        prefill = {
            "part_id": part_id,
            "yacht_id": yacht_id
        }

        if action_id == "receive_part":
            prefill.update({
                "current_stock": stock_info["on_hand"],
                "location": stock_info.get("location"),
                "part_number": part_data.get("part_number"),
                "part_name": part_data.get("name")
            })

        elif action_id == "consume_part":
            available_qty = stock_info["on_hand"]
            prefill.update({
                "available_quantity": available_qty,
                "max_quantity": available_qty,
                "part_number": part_data.get("part_number")
            })

        elif action_id == "add_to_shopping_list":
            min_level = part_data.get("min_level", 5)
            current_stock = stock_info["on_hand"]
            suggested_qty = max(min_level - current_stock, 1)

            prefill.update({
                "suggested_quantity": suggested_qty,
                "urgency": "high" if current_stock == 0 else "normal",
                "part_number": part_data.get("part_number"),
                "part_name": part_data.get("name")
            })

        elif action_id == "adjust_stock_quantity":
            prefill.update({
                "current_quantity": stock_info["on_hand"],
                "location": stock_info.get("location")
            })

        elif action_id == "write_off_part":
            prefill.update({
                "available_quantity": stock_info["on_hand"],
                "part_number": part_data.get("part_number")
            })

        elif action_id == "transfer_part":
            prefill.update({
                "from_location": stock_info.get("location"),
                "max_quantity": stock_info["on_hand"]
            })

        elif action_id == "print_part_labels":
            prefill.update({
                "part_ids": [part_id],
                "quantity": 1
            })

        return prefill

    # =========================================================================
    # STOCK ACTIONS
    # =========================================================================

    async def _get_stock_actions(
        self,
        stock_id: str,
        stock_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str]
    ) -> List[ActionSuggestion]:
        """
        Generate actions for inventory stock entity.

        Similar to part actions but focused on stock management.
        """
        # Get the part_id from stock data
        part_id = stock_data.get("part_id")
        if not part_id:
            return []

        # Reuse part actions logic
        # Get part data
        try:
            part_result = self.db.table("pms_parts").select(
                "id, part_number, name, is_critical, min_level"
            ).eq("id", part_id).eq("yacht_id", yacht_id).execute()

            if part_result.data:
                part_data = part_result.data[0]
                return await self._get_part_actions(
                    part_id, part_data, user_role, yacht_id, query_intent
                )
        except Exception as e:
            print(f"[PartLensMicroactions] Error fetching part data: {e}")

        return []

    # =========================================================================
    # SHOPPING LIST ACTIONS
    # =========================================================================

    async def _get_shopping_list_actions(
        self,
        item_id: str,
        item_data: Dict[str, Any],
        user_role: str,
        yacht_id: str,
        query_intent: Optional[str]
    ) -> List[ActionSuggestion]:
        """
        Generate actions for shopping list item.

        Common actions:
        - receive_part (when item arrives)
        - remove_from_shopping_list
        - update_shopping_list_quantity
        """
        all_actions = get_actions_for_domain("parts", user_role)

        shopping_list_action_ids = [
            "receive_part",
            "remove_from_shopping_list",
            "update_shopping_list_quantity"
        ]

        suggestions = []

        for action in all_actions:
            action_id = action["action_id"]

            if action_id not in shopping_list_action_ids:
                continue

            priority = 2 if action_id == "receive_part" else 1

            prefill_data = {
                "shopping_list_item_id": item_id,
                "part_id": item_data.get("part_id"),
                "quantity_needed": item_data.get("quantity_needed"),
                "yacht_id": yacht_id
            }

            suggestions.append(ActionSuggestion(
                action_id=action_id,
                label=action["label"],
                variant=ActionVariant(action["variant"]),
                entity_id=item_id,
                entity_type="shopping_list_item",
                prefill_data=prefill_data,
                priority=priority
            ))

        return suggestions
