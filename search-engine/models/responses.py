"""
Response models for search engine API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class CardType(str, Enum):
    """Types of result cards"""
    DOCUMENT_CHUNK = "document_chunk"
    FAULT = "fault"
    WORK_ORDER = "work_order"
    PART = "part"
    EQUIPMENT = "equipment"
    PREDICTIVE = "predictive"
    HANDOVER = "handover"
    EMAIL = "email"


class IntentType(str, Enum):
    """Types of detected intents"""
    DIAGNOSE_FAULT = "diagnose_fault"
    FIND_DOCUMENT = "find_document"
    CREATE_WORK_ORDER = "create_work_order"
    ADD_TO_HANDOVER = "add_to_handover"
    FIND_PART = "find_part"
    PREDICTIVE_REQUEST = "predictive_request"
    GENERAL_SEARCH = "general_search"


class MicroAction(BaseModel):
    """Micro-action attached to a result card"""

    label: str = Field(..., description="Action button label")
    action: str = Field(..., description="Action identifier")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context data for the action"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "label": "Create Work Order",
                "action": "create_work_order",
                "context": {"equipment_id": "uuid-here"}
            }
        }


class ResultCard(BaseModel):
    """Structured result card"""

    type: CardType = Field(..., description="Type of result card")
    title: str = Field(..., description="Card title")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    text_preview: Optional[str] = Field(None, description="Preview text")

    # Type-specific fields
    document_id: Optional[str] = None
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None

    equipment_id: Optional[str] = None
    fault_code: Optional[str] = None
    work_order_id: Optional[str] = None
    part_id: Optional[str] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Actions
    actions: List[MicroAction] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "document_chunk",
                "title": "CAT 3516 Cooling System",
                "score": 0.92,
                "document_id": "uuid-123",
                "chunk_index": 5,
                "page_number": 34,
                "text_preview": "Cooling pressure for CAT3516...",
                "actions": [
                    {
                        "label": "Open Document",
                        "action": "open_document",
                        "context": {"document_id": "uuid-123", "page": 34}
                    }
                ]
            }
        }


class EntityExtractionResult(BaseModel):
    """Extracted entities from query"""

    equipment: List[str] = Field(default_factory=list)
    fault_codes: List[str] = Field(default_factory=list)
    part_numbers: List[str] = Field(default_factory=list)
    action_words: List[str] = Field(default_factory=list)
    document_types: List[str] = Field(default_factory=list)
    system_names: List[str] = Field(default_factory=list)
    severity: Optional[str] = None
    location: Optional[str] = None

    # Confidence scores for each entity type
    confidence: Dict[str, float] = Field(default_factory=dict)


class IntentDetectionResult(BaseModel):
    """Detected intent from query"""

    intent: IntentType = Field(..., description="Detected intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: Optional[str] = Field(None, description="Why this intent was chosen")


class SearchResponse(BaseModel):
    """Response from search endpoint"""

    query_id: str = Field(..., description="Unique query ID for tracking")
    query: str = Field(..., description="Original query text")

    # Analysis
    entities: EntityExtractionResult = Field(..., description="Extracted entities")
    intent: IntentDetectionResult = Field(..., description="Detected intent")

    # Results
    results: List[ResultCard] = Field(default_factory=list, description="Search results")

    # Metadata
    latency_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    sources_searched: List[str] = Field(
        default_factory=list,
        description="Data sources that were searched"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "uuid-abc",
                "query": "fault code E047 on main engine",
                "entities": {
                    "equipment": ["main engine"],
                    "fault_codes": ["E047"],
                    "confidence": {"equipment": 0.95, "fault_code": 1.0}
                },
                "intent": {
                    "intent": "diagnose_fault",
                    "confidence": 0.92,
                    "reasoning": "Fault code and equipment detected"
                },
                "results": [],
                "latency_ms": 245,
                "sources_searched": ["document_chunks", "faults", "work_order_history"]
            }
        }
