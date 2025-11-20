"""
Card Generator
Converts fused results into structured result cards for the frontend
"""
from typing import List, Dict, Any
from models.responses import ResultCard, CardType
import logging

logger = logging.getLogger(__name__)


async def generate_cards(
    fused_results: List[Dict[str, Any]]
) -> List[ResultCard]:
    """
    Generate result cards from fused results

    Args:
        fused_results: List of fused and scored results

    Returns:
        List of ResultCard objects
    """
    logger.info(f"Generating cards for {len(fused_results)} results")

    cards = []

    for result in fused_results:
        try:
            card = create_card(result)
            if card:
                cards.append(card)
        except Exception as e:
            logger.error(f"Failed to create card for result: {e}")
            continue

    logger.info(f"Generated {len(cards)} cards")

    return cards


def create_card(result: Dict[str, Any]) -> ResultCard:
    """
    Create a single result card from a fused result

    Args:
        result: Fused result dictionary

    Returns:
        ResultCard object
    """
    result_type = result.get("type", "document_chunk")
    data = result.get("data", {})

    # Dispatch to type-specific card creator
    if result_type == "document_chunk":
        return create_document_chunk_card(result, data)

    elif result_type == "fault":
        return create_fault_card(result, data)

    elif result_type == "work_order":
        return create_work_order_card(result, data)

    elif result_type == "part":
        return create_part_card(result, data)

    elif result_type == "equipment":
        return create_equipment_card(result, data)

    elif result_type == "email":
        return create_email_card(result, data)

    else:
        # Generic card fallback
        return create_generic_card(result, data)


def create_document_chunk_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create card for document chunk"""

    return ResultCard(
        type=CardType.DOCUMENT_CHUNK,
        title=result.get("title", "Document"),
        score=result.get("final_score", 0.5),
        text_preview=result.get("preview", ""),
        document_id=data.get("document_id"),
        chunk_index=data.get("chunk_index"),
        page_number=data.get("page_number"),
        metadata={
            "source": result.get("source"),
            "is_global": result.get("is_global", False),
            "similarity": result.get("similarity"),
            "boosts": result.get("boosts", {}),
            "equipment_ids": data.get("equipment_ids"),
            "tags": data.get("tags"),
        },
        actions=[]  # Will be populated by micro_actions module
    )


def create_fault_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create card for fault"""

    # Build summary from fault data
    fault_code = data.get("fault_code", "Unknown")
    equipment_name = "Unknown Equipment"

    if "equipment" in data and isinstance(data["equipment"], dict):
        equipment_name = data["equipment"].get("name", equipment_name)

    summary = f"{fault_code} on {equipment_name}"

    return ResultCard(
        type=CardType.FAULT,
        title=result.get("title", summary),
        score=result.get("final_score", 0.5),
        text_preview=data.get("description", ""),
        fault_code=data.get("fault_code"),
        equipment_id=data.get("equipment_id"),
        metadata={
            "severity": data.get("severity"),
            "detected_at": data.get("detected_at"),
            "resolved_at": data.get("resolved_at"),
            "resolved_by": data.get("resolved_by"),
            "work_order_id": data.get("work_order_id"),
        },
        actions=[]
    )


def create_work_order_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create card for work order"""

    title = "Work Order"
    if "work_order" in data and isinstance(data["work_order"], dict):
        title = data["work_order"].get("title", title)

    status = data.get("status_on_completion", "completed")

    return ResultCard(
        type=CardType.WORK_ORDER,
        title=result.get("title", title),
        score=result.get("final_score", 0.5),
        text_preview=result.get("preview", ""),
        work_order_id=data.get("work_order_id"),
        equipment_id=data.get("equipment_id"),
        metadata={
            "completed_at": data.get("completed_at"),
            "completed_by": data.get("completed_by"),
            "status": status,
            "parts_used": data.get("parts_used"),
            "hours_logged": data.get("hours_logged"),
        },
        actions=[]
    )


def create_part_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create card for part/spare"""

    # Extract stock info
    stock_info = ""
    in_stock = 0

    if "stock_levels" in data and isinstance(data["stock_levels"], list):
        for stock in data["stock_levels"]:
            if isinstance(stock, dict):
                qty = stock.get("quantity", 0)
                in_stock += qty

                location = "Unknown"
                if "location" in stock and isinstance(stock["location"], dict):
                    location = stock["location"].get("name", "Unknown")

                stock_info += f"{qty} in {location}; "

    stock_info = stock_info.rstrip("; ")

    preview = data.get("description", "")
    if stock_info:
        preview = f"Stock: {stock_info}\n{preview}"

    return ResultCard(
        type=CardType.PART,
        title=result.get("title", "Part"),
        score=result.get("final_score", 0.5),
        text_preview=preview,
        part_id=data.get("id"),
        metadata={
            "part_number": data.get("part_number"),
            "manufacturer": data.get("manufacturer"),
            "category": data.get("category"),
            "in_stock": in_stock,
            "compatibility": data.get("model_compatibility"),
        },
        actions=[]
    )


def create_equipment_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create card for equipment"""

    preview_parts = []

    if data.get("manufacturer"):
        preview_parts.append(f"Mfr: {data['manufacturer']}")

    if data.get("model"):
        preview_parts.append(f"Model: {data['model']}")

    if data.get("location"):
        preview_parts.append(f"Location: {data['location']}")

    preview = " | ".join(preview_parts)

    return ResultCard(
        type=CardType.EQUIPMENT,
        title=result.get("title", "Equipment"),
        score=result.get("final_score", 0.5),
        text_preview=preview,
        equipment_id=data.get("id"),
        metadata={
            "code": data.get("code"),
            "manufacturer": data.get("manufacturer"),
            "model": data.get("model"),
            "serial_number": data.get("serial_number"),
            "location": data.get("location"),
            "criticality": data.get("criticality"),
            "system_type": data.get("system_type"),
        },
        actions=[]
    )


def create_email_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create card for email message"""

    sender = data.get("sender", "Unknown")
    sent_at = data.get("sent_at", "")

    return ResultCard(
        type=CardType.EMAIL,
        title=result.get("title", "Email"),
        score=result.get("final_score", 0.5),
        text_preview=result.get("preview", ""),
        metadata={
            "sender": sender,
            "sent_at": sent_at,
            "recipients": data.get("recipients"),
            "external_id": data.get("external_id"),
        },
        actions=[]
    )


def create_generic_card(result: Dict[str, Any], data: Dict[str, Any]) -> ResultCard:
    """Create generic card for unknown types"""

    return ResultCard(
        type=CardType.DOCUMENT_CHUNK,  # Default to document
        title=result.get("title", "Result"),
        score=result.get("final_score", 0.5),
        text_preview=result.get("preview", ""),
        metadata={
            "source": result.get("source"),
            "raw_data": data
        },
        actions=[]
    )
