"""Part Lens Microactions - Context-aware action suggestions"""
from typing import List, Dict, Any, Optional
from ..base_microaction import BaseLensMicroactions, ActionSuggestion, ActionVariant

try:
    from action_router.registry import get_actions_for_domain
except ImportError:
    def get_actions_for_domain(domain: str, role: str = None):
        return []


class PartLensMicroactions(BaseLensMicroactions):
    lens_name = "part_lens"
    entity_types = ["part", "inventory_stock", "shopping_list_item"]

    async def get_suggestions(self, entity_type: str, entity_id: str, entity_data: Dict[str, Any],
                              user_role: str, yacht_id: str, query_intent: Optional[str] = None) -> List[ActionSuggestion]:
        if entity_type == "part":
            return await self._get_part_actions(entity_id, entity_data, user_role, yacht_id, query_intent)
        elif entity_type == "inventory_stock":
            return await self._get_stock_actions(entity_id, entity_data, user_role, yacht_id, query_intent)
        elif entity_type == "shopping_list_item":
            return await self._get_shopping_list_actions(entity_id, entity_data, user_role, yacht_id, query_intent)
        return []

    async def _get_part_actions(self, part_id: str, part_data: Dict, user_role: str, yacht_id: str, query_intent: Optional[str]) -> List[ActionSuggestion]:
        all_actions = get_actions_for_domain("parts", user_role)
        stock_info = await self._get_stock_info(part_id, yacht_id)
        is_out_of_stock = stock_info["on_hand"] == 0
        is_low_stock = stock_info["on_hand"] <= stock_info.get("min_level", 0)
        is_critical = part_data.get("is_critical", False)

        suggestions = []
        for action in all_actions:
            action_id = action["action_id"]
            if is_out_of_stock and action_id in ["consume_part", "transfer_part", "write_off_part"]:
                continue
            priority = self._calculate_priority(action_id, query_intent, is_out_of_stock, is_low_stock, is_critical)
            prefill_data = await self._get_prefill_data(action_id, part_id, part_data, stock_info, yacht_id)
            suggestions.append(ActionSuggestion(action_id=action_id, label=action["label"], variant=ActionVariant(action["variant"]),
                                               entity_id=part_id, entity_type="part", prefill_data=prefill_data, priority=priority))
        return suggestions

    async def _get_stock_info(self, part_id: str, yacht_id: str) -> Dict[str, Any]:
        try:
            result = self.db.table("pms_parts").select("quantity_on_hand, min_level, location, primary_location_id").eq("id", part_id).eq("yacht_id", yacht_id).execute()
            if result.data:
                stock = result.data[0]
                return {"on_hand": stock.get("quantity_on_hand", 0), "min_level": stock.get("min_level", 0),
                       "location": stock.get("location"), "primary_location_id": stock.get("primary_location_id")}
        except:
            pass
        return {"on_hand": 0, "min_level": 0, "location": None, "primary_location_id": None}

    def _calculate_priority(self, action_id: str, query_intent: Optional[str], is_out_of_stock: bool, is_low_stock: bool, is_critical: bool) -> int:
        priority = 1
        if query_intent and action_id == query_intent:
            priority = 5
        elif is_out_of_stock:
            if action_id == "receive_part":
                priority = 4
            elif action_id == "add_to_shopping_list":
                priority = 3
        elif is_low_stock and action_id in ["receive_part", "add_to_shopping_list"]:
            priority = 3
        if is_critical and action_id in ["receive_part", "add_to_shopping_list"]:
            priority = min(priority + 1, 5)
        return priority

    async def _get_prefill_data(self, action_id: str, part_id: str, part_data: Dict, stock_info: Dict, yacht_id: str) -> Dict[str, Any]:
        prefill = {"part_id": part_id, "yacht_id": yacht_id}
        if action_id == "receive_part":
            prefill.update({"current_stock": stock_info["on_hand"], "location": stock_info.get("location"),
                           "part_number": part_data.get("part_number"), "part_name": part_data.get("name")})
        elif action_id == "consume_part":
            prefill.update({"available_quantity": stock_info["on_hand"], "max_quantity": stock_info["on_hand"],
                           "part_number": part_data.get("part_number")})
        elif action_id == "add_to_shopping_list":
            suggested_qty = max(stock_info.get("min_level", 5) - stock_info["on_hand"], 1)
            prefill.update({"suggested_quantity": suggested_qty, "urgency": "high" if stock_info["on_hand"] == 0 else "normal",
                           "part_number": part_data.get("part_number"), "part_name": part_data.get("name")})
        elif action_id == "adjust_stock_quantity":
            prefill.update({"current_quantity": stock_info["on_hand"], "location": stock_info.get("location")})
        elif action_id == "write_off_part":
            prefill.update({"available_quantity": stock_info["on_hand"], "part_number": part_data.get("part_number")})
        elif action_id == "transfer_part":
            prefill.update({"from_location": stock_info.get("location"), "max_quantity": stock_info["on_hand"]})
        elif action_id == "print_part_labels":
            prefill.update({"part_ids": [part_id], "quantity": 1})
        return prefill

    async def _get_stock_actions(self, stock_id: str, stock_data: Dict, user_role: str, yacht_id: str, query_intent: Optional[str]) -> List[ActionSuggestion]:
        part_id = stock_data.get("part_id")
        if not part_id:
            return []
        try:
            part_result = self.db.table("pms_parts").select("id, part_number, name, is_critical, min_level").eq("id", part_id).eq("yacht_id", yacht_id).execute()
            if part_result.data:
                return await self._get_part_actions(part_id, part_result.data[0], user_role, yacht_id, query_intent)
        except:
            pass
        return []

    async def _get_shopping_list_actions(self, item_id: str, item_data: Dict, user_role: str, yacht_id: str, query_intent: Optional[str]) -> List[ActionSuggestion]:
        all_actions = get_actions_for_domain("parts", user_role)
        shopping_list_action_ids = ["receive_part", "remove_from_shopping_list", "update_shopping_list_quantity"]
        suggestions = []
        for action in all_actions:
            if action["action_id"] not in shopping_list_action_ids:
                continue
            priority = 2 if action["action_id"] == "receive_part" else 1
            prefill_data = {"shopping_list_item_id": item_id, "part_id": item_data.get("part_id"),
                           "quantity_needed": item_data.get("quantity_needed"), "yacht_id": yacht_id}
            suggestions.append(ActionSuggestion(action_id=action["action_id"], label=action["label"], variant=ActionVariant(action["variant"]),
                                               entity_id=item_id, entity_type="shopping_list_item", prefill_data=prefill_data, priority=priority))
        return suggestions
