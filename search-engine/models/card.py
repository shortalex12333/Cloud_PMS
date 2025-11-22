"""
Canonical SearchResultCard Model
Standardized card type used by the frontend for all search results
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class CardType(str, Enum):
    """
    Canonical card types for search results
    Each type has specific metadata and action requirements
    """
    EQUIPMENT = "equipment"
    DOCUMENT = "document"
    FAULT = "fault"
    PART = "part"
    PREDICTIVE = "predictive"
    HANDOVER = "handover"
    WORK_ORDER = "work_order"
    NOTE = "note"


class MicroAction(BaseModel):
    """
    Micro-action attached to a result card
    Actions are context-aware based on intent, role, and yacht configuration
    """
    id: str = Field(..., description="Unique action identifier (from catalogue)")
    label: str = Field(..., description="Display label for button")
    icon: Optional[str] = Field(None, description="Icon identifier (e.g., 'document', 'wrench')")
    action_type: str = Field(..., description="Action type: 'navigate', 'modal', 'api_call', 'copy'")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action payload with context data"
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether action requires user confirmation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "create_work_order",
                "label": "Create Work Order",
                "icon": "wrench",
                "action_type": "modal",
                "payload": {
                    "equipment_id": "uuid-here",
                    "fault_code": "E047",
                    "prefill_title": "Fix fault E047"
                },
                "requires_confirmation": False
            }
        }


class SourceLabel(BaseModel):
    """
    Human-readable source label for result provenance
    Format: "{type} . {name} . {location}"
    """
    source_type: str = Field(..., description="Source type: 'manual', 'email', 'work_order', etc.")
    source_name: str = Field(..., description="Source name or filename")
    location: Optional[str] = Field(None, description="Location within source (e.g., 'Page 34')")

    def to_display_string(self) -> str:
        """Generate human-readable display string"""
        parts = [self.source_type]
        if self.source_name:
            parts.append(self.source_name)
        if self.location:
            parts.append(self.location)
        return " . ".join(parts)


class CardMetadata(BaseModel):
    """
    Type-specific metadata for search result cards
    Only relevant fields should be populated based on card_type
    """
    # Common identifiers
    id: Optional[str] = Field(None, description="Primary entity ID")
    yacht_id: Optional[str] = Field(None, description="Yacht ID for RLS")

    # Equipment-related
    equipment_id: Optional[str] = None
    equipment_name: Optional[str] = None
    equipment_code: Optional[str] = None
    system_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    criticality: Optional[str] = None

    # Document-related
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    filename: Optional[str] = None

    # Fault-related
    fault_code: Optional[str] = None
    fault_id: Optional[str] = None
    severity: Optional[str] = None
    detected_at: Optional[str] = None
    resolved_at: Optional[str] = None

    # Part-related
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    stock_level: Optional[int] = None
    stock_location: Optional[str] = None

    # Work order-related
    work_order_id: Optional[str] = None
    work_order_status: Optional[str] = None
    assigned_to: Optional[str] = None
    completed_at: Optional[str] = None

    # Handover-related
    handover_id: Optional[str] = None
    shift_date: Optional[str] = None
    author: Optional[str] = None

    # Predictive-related
    prediction_confidence: Optional[float] = None
    predicted_failure_window: Optional[str] = None
    risk_level: Optional[str] = None

    # Note-related
    note_id: Optional[str] = None
    note_type: Optional[str] = None
    created_by: Optional[str] = None

    # Search metadata
    similarity_score: Optional[float] = None
    graph_depth: Optional[int] = None
    is_global_knowledge: bool = False

    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class SearchResultCard(BaseModel):
    """
    Canonical search result card model

    This is the ONLY card type returned by the search engine to the frontend.
    All result types (equipment, documents, faults, etc.) are normalized to this format.
    """
    # Core fields (required)
    card_type: CardType = Field(..., description="Type of result card")
    title: str = Field(..., description="Card title (max 100 chars)")
    snippet: str = Field(..., description="Preview text snippet (max 300 chars)")

    # Source provenance
    source_label: SourceLabel = Field(..., description="Human-readable source label")

    # Type-specific metadata
    metadata: CardMetadata = Field(
        default_factory=CardMetadata,
        description="Type-specific metadata"
    )

    # Context-aware actions (2-4 per card)
    actions: List[MicroAction] = Field(
        default_factory=list,
        max_length=4,
        description="Micro-actions for this card (max 4)"
    )

    # Scoring (for debugging/transparency)
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final relevance score after fusion"
    )

    # Optional: Graph context (when GraphRAG is enabled)
    graph_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Related nodes/paths from GraphRAG (when enabled)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "card_type": "document",
                "title": "CAT 3516 Cooling System Maintenance",
                "snippet": "The cooling system on CAT 3516 engines requires regular inspection of the heat exchanger...",
                "source_label": {
                    "source_type": "Manual",
                    "source_name": "CAT_3516_Service_Manual.pdf",
                    "location": "Page 34"
                },
                "metadata": {
                    "document_id": "uuid-123",
                    "page_number": 34,
                    "equipment_id": "equip-456",
                    "equipment_name": "Main Engine #1"
                },
                "actions": [
                    {
                        "id": "open_document",
                        "label": "Open Document",
                        "icon": "document",
                        "action_type": "navigate",
                        "payload": {
                            "document_id": "uuid-123",
                            "page": 34
                        }
                    },
                    {
                        "id": "add_to_handover",
                        "label": "Add to Handover",
                        "icon": "clipboard",
                        "action_type": "api_call",
                        "payload": {
                            "source_type": "document",
                            "source_id": "uuid-123"
                        }
                    }
                ],
                "relevance_score": 0.92
            }
        }


# Type aliases for response building
SearchResultCards = List[SearchResultCard]
