"""
GPT Entity Extractor for CelesteOS
===================================

Uses OpenAI GPT-4o-mini for entity extraction and text-embedding-3-small for embeddings.
Same models used at index time (n8n) and query time (Render) for consistency.

Architecture:
    Index Time:  n8n → GPT-4 extraction → text-embedding-3-small → Supabase
    Query Time:  Render → GPT-4o-mini extraction → text-embedding-3-small → match_documents()

Why GPT over regex:
    - "motor running hot" matches "engine overheating" (semantic understanding)
    - "2nd engineer" = "second engineer" (normalization)
    - New equipment names handled automatically (no pattern updates)
    - ~95% precision vs ~70% with regex
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION PROMPT (Maritime Domain)
# =============================================================================

EXTRACTION_PROMPT = """You are a maritime entity extractor for yacht planned maintenance systems (PMS).

Extract entities from the user query and return structured JSON.

ENTITY TYPES:
1. equipment: Main Engine, Generator, Bilge Pump, Sea Water Pump, Heat Exchanger, Turbocharger, etc.
2. part: Oil Filter, Fuel Filter, Impeller, Gasket, Seal, Bearing, Valve, Sensor, Belt, etc.
3. symptom: overheating, vibration, leak, noise, pressure drop, shutdown, failure, alarm, etc.
4. fault_code: E047, SPN 123 FMI 4, P0420, MTU codes, etc.
5. person: Captain, Chief Engineer, 2nd Engineer, 3rd Engineer, Electrician, Bosun, etc.
6. measurement: 24V, 85°C, 3 bar, 1500 RPM, etc.
7. system: Cooling System, Fuel System, Electrical System, Hydraulic System, etc.

ACTIONS (detect user intent):
- create_work_order: "create work order", "raise wo", "new task"
- view_history: "show history", "historic data", "past records"
- diagnose_fault: "diagnose", "troubleshoot", "what does error mean"
- find_document: "find manual", "open document", "show procedure"
- add_to_handover: "add to handover", "include in handover"
- check_stock: "check stock", "inventory level"
- order_parts: "order parts", "request spares"

RESPONSE FORMAT (JSON only):
{
    "entities": [
        {"type": "equipment", "value": "Main Engine", "canonical": "MAIN_ENGINE", "confidence": 0.95},
        {"type": "symptom", "value": "overheating", "canonical": "OVERHEAT", "confidence": 0.90}
    ],
    "action": "view_history",
    "action_confidence": 0.92,
    "person_filter": "2ND_ENGINEER" or null
}

RULES:
- canonical should be UPPERCASE_WITH_UNDERSCORES
- confidence is 0.0-1.0 based on how clear the entity is
- If no clear action, use "general_search"
- Extract ALL entities mentioned, not just the first
- person_filter only if query mentions filtering by a specific person/role"""


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExtractedEntity:
    """Entity extracted by GPT"""
    type: str
    value: str
    canonical: str
    confidence: float = 0.9

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "value": self.value,
            "canonical": self.canonical,
            "confidence": self.confidence
        }


@dataclass
class ExtractionResult:
    """Full extraction result from GPT"""
    entities: List[ExtractedEntity]
    action: str
    action_confidence: float
    person_filter: Optional[str] = None
    raw_response: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "action": self.action,
            "action_confidence": self.action_confidence,
            "person_filter": self.person_filter
        }


# =============================================================================
# GPT EXTRACTOR
# =============================================================================

class GPTExtractor:
    """
    Entity extraction using GPT-4o-mini and embeddings using text-embedding-3-small.

    Usage:
        extractor = GPTExtractor()
        result = extractor.extract("Engine is overheating, show historic data from 2nd engineer")
        embedding = extractor.embed("Engine is overheating")
    """

    def __init__(self, api_key: str = None):
        """
        Initialize GPT extractor.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai>=1.3.0")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = openai.OpenAI(api_key=self.api_key)

        # Model configuration
        self.extraction_model = "gpt-4o-mini"  # Fast, cheap, good for extraction
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions, same as index
        self.embedding_dimensions = 1536

    def extract(self, query: str) -> ExtractionResult:
        """
        Extract entities and detect action from user query using GPT-4o-mini.

        Args:
            query: Natural language user query

        Returns:
            ExtractionResult with entities, action, and confidence scores
        """
        if not query or not query.strip():
            return ExtractionResult(
                entities=[],
                action="general_search",
                action_confidence=0.0
            )

        try:
            response = self.client.chat.completions.create(
                model=self.extraction_model,
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=500
            )

            raw = json.loads(response.choices[0].message.content)

            # Parse entities
            entities = []
            for e in raw.get("entities", []):
                entities.append(ExtractedEntity(
                    type=e.get("type", "unknown"),
                    value=e.get("value", ""),
                    canonical=e.get("canonical", e.get("value", "").upper().replace(" ", "_")),
                    confidence=e.get("confidence", 0.9)
                ))

            return ExtractionResult(
                entities=entities,
                action=raw.get("action", "general_search"),
                action_confidence=raw.get("action_confidence", 0.8),
                person_filter=raw.get("person_filter"),
                raw_response=raw
            )

        except json.JSONDecodeError as e:
            logger.error(f"GPT returned invalid JSON: {e}")
            return self._fallback_extraction(query)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return self._fallback_extraction(query)
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return self._fallback_extraction(query)

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text using text-embedding-3-small.

        IMPORTANT: This is the SAME model used at index time in n8n.
        Using the same model ensures consistent similarity scores.

        Args:
            text: Text to embed

        Returns:
            List of 1536 floats (embedding vector)
        """
        if not text or not text.strip():
            return [0.0] * self.embedding_dimensions

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text.strip()
            )
            return response.data[0].embedding

        except openai.APIError as e:
            logger.error(f"Embedding API error: {e}")
            return [0.0] * self.embedding_dimensions
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return [0.0] * self.embedding_dimensions

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in one API call.

        More efficient than calling embed() multiple times.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        clean_texts = [t.strip() for t in texts if t and t.strip()]
        if not clean_texts:
            return [[0.0] * self.embedding_dimensions for _ in texts]

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=clean_texts
            )
            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return [[0.0] * self.embedding_dimensions for _ in texts]

    def _fallback_extraction(self, query: str) -> ExtractionResult:
        """
        Fallback extraction when GPT fails.
        Uses simple keyword matching as backup.
        """
        logger.warning(f"Using fallback extraction for: {query}")

        entities = []
        query_lower = query.lower()

        # Simple equipment detection
        equipment_keywords = {
            "engine": "MAIN_ENGINE",
            "generator": "GENERATOR",
            "pump": "PUMP",
            "compressor": "COMPRESSOR",
            "heat exchanger": "HEAT_EXCHANGER"
        }
        for keyword, canonical in equipment_keywords.items():
            if keyword in query_lower:
                entities.append(ExtractedEntity(
                    type="equipment",
                    value=keyword,
                    canonical=canonical,
                    confidence=0.6
                ))

        # Simple symptom detection
        symptom_keywords = {
            "overheating": "OVERHEAT",
            "leak": "LEAK",
            "vibration": "VIBRATION",
            "noise": "NOISE"
        }
        for keyword, canonical in symptom_keywords.items():
            if keyword in query_lower:
                entities.append(ExtractedEntity(
                    type="symptom",
                    value=keyword,
                    canonical=canonical,
                    confidence=0.6
                ))

        # Simple action detection
        action = "general_search"
        if "history" in query_lower or "historic" in query_lower:
            action = "view_history"
        elif "create" in query_lower and "work" in query_lower:
            action = "create_work_order"
        elif "diagnose" in query_lower or "troubleshoot" in query_lower:
            action = "diagnose_fault"

        return ExtractionResult(
            entities=entities,
            action=action,
            action_confidence=0.5
        )


# =============================================================================
# SINGLETON
# =============================================================================

_extractor_instance = None

def get_gpt_extractor() -> GPTExtractor:
    """Get or create singleton GPT extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = GPTExtractor()
    return _extractor_instance


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("GPT Extractor Test")
    print("=" * 60)

    try:
        extractor = GPTExtractor()

        test_queries = [
            "Engine is overheating, show historic data from the 2nd engineer",
            "What does error code E047 mean?",
            "Create work order for bilge pump inspection",
            "Find oil filter for generator 1"
        ]

        for query in test_queries:
            print(f"\nQuery: '{query}'")
            result = extractor.extract(query)
            print(f"Action: {result.action} (confidence: {result.action_confidence:.2f})")
            print(f"Person filter: {result.person_filter}")
            print(f"Entities:")
            for e in result.entities:
                print(f"  - {e.type}: {e.value} → {e.canonical} ({e.confidence:.2f})")

            # Test embedding
            embedding = extractor.embed(query)
            print(f"Embedding: {len(embedding)} dimensions, first 5: {embedding[:5]}")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure OPENAI_API_KEY is set")
