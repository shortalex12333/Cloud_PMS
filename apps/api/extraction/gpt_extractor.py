"""
GPT Entity Extractor for CelesteOS
===================================

=== PLAIN ENGLISH SUMMARY ===
This file uses OpenAI's ChatGPT AI to understand user queries.
While module_b_entity_extractor.py uses pattern matching (looking for exact words),
this file uses artificial intelligence to UNDERSTAND what the user means.

Example difference:
- Pattern matching: "engine" matches "engine" exactly
- GPT AI: "motor running hot" understands you mean "engine overheating"

=== WHY USE AI INSTEAD OF PATTERNS? ===
1. SYNONYMS: "motor" and "engine" mean the same thing - AI understands this
2. TYPOS: "enginee" still gets understood as "engine"
3. CONTEXT: "manual" after a brand name means "documentation" not "manual mode"
4. NEW TERMS: If someone mentions a brand we've never seen, AI can still guess it's a brand

=== HOW IT WORKS ===
1. User types a query like "Generator is making noise, show me past records"
2. We send this query to OpenAI's GPT-4o-mini model
3. GPT analyzes the text and returns structured data:
   - entities: Generator (equipment), noise (symptom)
   - action: view_history (because "show me past records")
4. We use this data to search our database

=== EMBEDDINGS EXPLAINED ===
An "embedding" converts text into numbers that represent meaning.
Example: "engine overheating" becomes [0.23, -0.45, 0.87, ...] (1536 numbers)
Similar texts have similar numbers, so we can find related documents.

=== COST & PERFORMANCE ===
- GPT-4o-mini: ~$0.15 per 1M tokens (~$0.0001 per query)
- text-embedding-3-small: ~$0.02 per 1M tokens (very cheap)
- Response time: ~200-500ms per query

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

# =============================================================================
# IMPORTS
# =============================================================================

# os: Allows reading environment variables (like API keys stored in system settings)
import os

# json: Handles converting between Python dictionaries and JSON text format
# GPT returns JSON text, we need to convert it to Python objects
import json

# logging: Creates log messages for debugging and monitoring
# Helps us see what's happening when things go wrong
import logging

# typing: Provides type hints - helps developers understand what data types are expected
# Dict = dictionary (key-value pairs), List = array, Optional = can be None
from typing import Dict, List, Optional

# dataclass: A shortcut for creating classes that mainly store data
# Reduces boilerplate code - no need to write __init__ manually
from dataclasses import dataclass

# =============================================================================
# OPENAI LIBRARY CHECK
# =============================================================================

# Try to import the openai library (the official OpenAI Python package)
# This library lets us call GPT and embedding APIs
try:
    import openai  # OpenAI's official Python client library
    OPENAI_AVAILABLE = True  # Flag: openai package IS installed
except ImportError:
    # If openai package isn't installed, set flag to False
    # The code will still load, but will error if you try to use it
    OPENAI_AVAILABLE = False  # Flag: openai package is NOT installed

# =============================================================================
# LOGGING SETUP
# =============================================================================

# Set up logging to print INFO level messages and above
# Levels: DEBUG < INFO < WARNING < ERROR < CRITICAL
logging.basicConfig(level=logging.INFO)

# Create a logger specifically for this module
# __name__ = "gpt_extractor" (the module name)
logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION PROMPT (Maritime Domain)
# =============================================================================

# This is the SYSTEM PROMPT we send to GPT to tell it how to behave.
# Think of it as instructions for an employee - it tells GPT:
# 1. What its job is (maritime entity extractor)
# 2. What entity types to look for
# 3. What format to return results in
#
# CRITICAL: This prompt defines the AI's behavior and output format.
# If you change this prompt, the AI's responses will change.
#
# IMPORTANT DESIGN DECISION:
# - LLM extracts RAW values only (no canonical IDs)
# - Canonicalization happens in a separate module (module_c_canonicalizer.py)
# - This prevents "fake certainty" where LLM invents IDs that don't exist in our system
# - evidence + char spans enable: hallucination detection, deduplication, training data

EXTRACTION_PROMPT = """You are a maritime entity extractor for a yacht PMS.

Task:
Extract ONLY entities explicitly present in the user query and return JSON.

Entity types:
- equipment: Main Engine, Generator, Bilge Pump, Sea Water Pump, Turbocharger, etc.
- part: Oil Filter, Fuel Filter, Impeller, Gasket, Seal, Bearing, Valve, etc.
- symptom: overheating, vibration, leak, noise, pressure drop, alarm, etc.
- fault_code: E047, SPN 123 FMI 4, P0420, MTU codes, etc.
- person: Captain, Chief Engineer, 2nd Engineer, Electrician, Bosun, etc.
- measurement: 24V, 85°C, 3 bar, 1500 RPM, etc.
- system: Cooling System, Fuel System, Electrical System, Hydraulic System, etc.
- doc_type: manual, procedure, checklist, schematic, etc.

Actions:
- create_work_order, view_history, diagnose_fault, find_document
- add_to_handover, check_stock, order_parts
- If unclear: general_search

Output JSON ONLY with this schema:
{
  "entities": [
    {
      "type": "equipment|part|symptom|fault_code|person|measurement|system|doc_type",
      "value": "exact text from query",
      "confidence": 0.0-1.0,
      "evidence": "exact substring from query",
      "start_char": integer,
      "end_char": integer
    }
  ],
  "action": "string",
  "action_confidence": 0.0-1.0,
  "person_filter": "string or null",
  "new_terms": [
    { "term": "string", "reason": "unknown_abbrev|unknown_model|unclassified", "evidence": "string" }
  ]
}

RULES:
- Do NOT invent canonical IDs (we handle that separately)
- evidence MUST appear verbatim in the query
- start_char and end_char are 0-indexed character positions
- Prefer specific phrases over generic words
- If unsure about an entity, put it in new_terms instead
- new_terms is for: unknown abbreviations, unfamiliar model numbers, ambiguous terms
- Extract ALL entities mentioned, not just the first"""


# =============================================================================
# DATA CLASSES - ExtractedEntity
# =============================================================================

# @dataclass is a Python decorator that automatically generates:
# - __init__ method (constructor)
# - __repr__ method (for printing)
# - __eq__ method (for comparing)
# It's a shortcut for creating simple data-holding classes.

@dataclass
class ExtractedEntity:
    """
    Represents a single entity extracted by GPT from the user's query.

    === WHAT THIS STORES ===
    When GPT finds something like "Main Engine is overheating", it creates:
    - type="equipment", value="Main Engine", confidence=0.95, evidence="Main Engine", start_char=0, end_char=11
    - type="symptom", value="overheating", confidence=0.90, evidence="overheating", start_char=15, end_char=26

    === DESIGN DECISION ===
    NO canonical field here! Canonicalization happens AFTER extraction in module_c_canonicalizer.py.
    This prevents "fake certainty" where LLM invents IDs that don't exist in our system.

    === FIELDS EXPLAINED ===
    - type: Category of entity (equipment, part, symptom, fault_code, person, measurement, system)
    - value: The exact text found in the query ("Main Engine")
    - confidence: How sure GPT is about this extraction (0.0 = guess, 1.0 = certain)
    - evidence: The exact substring from the query that supports this entity
    - start_char: Starting character position in query (0-indexed)
    - end_char: Ending character position in query (0-indexed)

    === WHY EVIDENCE + CHAR SPANS? ===
    1. Hallucination detection: If evidence doesn't appear in query, reject it
    2. Deduplication: Overlapping spans indicate duplicate entities
    3. Training data: Build labeled dataset for future fine-tuning
    """

    # The category/type of this entity
    # Examples: "equipment", "part", "symptom", "fault_code"
    type: str

    # The exact text that was found in the user's query
    # Examples: "Main Engine", "oil filter", "overheating"
    value: str

    # How confident GPT is about this extraction (0.0 to 1.0)
    # 0.9 is the default - fairly confident
    # Lower confidence (0.6-0.7) means GPT is guessing
    # Higher confidence (0.95+) means GPT is very sure
    confidence: float = 0.9  # Default value of 0.9 (90% confident)

    # The exact substring from the query that supports this entity
    # MUST appear verbatim in the original query
    # Used to verify LLM didn't hallucinate
    evidence: str = ""

    # Starting character position in the query (0-indexed)
    # Used for span-based deduplication and overlap detection
    start_char: int = -1

    # Ending character position in the query (0-indexed)
    # Used for span-based deduplication and overlap detection
    end_char: int = -1

    def to_dict(self) -> Dict:
        """
        Convert this entity to a dictionary format.

        === WHY WE NEED THIS ===
        When sending data over HTTP or saving to JSON, we need dictionaries.
        Python objects can't be directly converted to JSON, but dictionaries can.

        Returns:
            Dictionary with type, value, confidence, evidence, and char positions
        """
        return {
            "type": self.type,           # Entity category
            "value": self.value,         # Original text
            "confidence": self.confidence, # Confidence score
            "evidence": self.evidence,   # Verbatim substring from query
            "start_char": self.start_char, # Start position
            "end_char": self.end_char      # End position
        }

    def validate_evidence(self, query: str) -> bool:
        """
        Verify that evidence actually appears in the query.

        === HALLUCINATION DETECTION ===
        If the LLM invents an entity that doesn't appear in the query,
        this check will catch it.

        Args:
            query: The original user query

        Returns:
            True if evidence is found in query, False if hallucinated
        """
        if not self.evidence:
            return False
        return self.evidence.lower() in query.lower()


# =============================================================================
# DATA CLASSES - NewTerm (for uncertain/unknown entities)
# =============================================================================

@dataclass
class NewTerm:
    """
    Represents an uncertain or unknown term that the LLM couldn't confidently classify.

    === WHAT THIS STORES ===
    When GPT encounters something it can't classify with confidence, it goes here:
    - Unknown abbreviations: "MPSV" (what does this mean?)
    - Unfamiliar model numbers: "XJ-4500" (is this equipment or part?)
    - Ambiguous terms: "unit" (too vague to classify)

    === WHY THIS MATTERS ===
    Instead of forcing low-confidence guesses into entities (which poisons data),
    we capture uncertain items separately. This allows:
    1. Human review of edge cases
    2. Building a learning dataset
    3. Preventing bad data from entering the system
    """

    # The term that couldn't be classified
    term: str

    # Why it couldn't be classified
    # Options: "unknown_abbrev", "unknown_model", "unclassified"
    reason: str

    # The evidence/context from the query
    evidence: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "term": self.term,
            "reason": self.reason,
            "evidence": self.evidence
        }


# =============================================================================
# DATA CLASSES - ExtractionResult
# =============================================================================

@dataclass
class ExtractionResult:
    """
    Complete result from GPT extraction - contains all entities and detected action.

    === WHAT THIS STORES ===
    For query "Engine is overheating, show historic data from 2nd engineer":
    - entities: [Engine (equipment), overheating (symptom)]
    - action: "view_history" (because "show historic data")
    - action_confidence: 0.92
    - person_filter: "2nd engineer" (raw value, NOT canonical)
    - new_terms: [] (empty if everything was classified)

    === DESIGN DECISION ===
    person_filter is now RAW value, not canonical. Canonicalization happens separately.

    === WHEN IS THIS USED ===
    1. GPT analyzes the user's query
    2. GPT returns JSON with entities and action
    3. We parse that JSON into this ExtractionResult object
    4. The rest of the system uses this to search/route/process
    """

    # List of all entities found in the query
    # Can be empty if GPT didn't find any entities
    entities: List[ExtractedEntity]

    # What action the user wants to perform
    # Examples: "create_work_order", "view_history", "diagnose_fault", "general_search"
    action: str

    # How confident GPT is about the detected action (0.0 to 1.0)
    action_confidence: float

    # Optional: If the user wants to filter by a person/role
    # Example: "show work from the 2nd engineer" → "2nd engineer" (raw, not canonical)
    # None if no person filter mentioned
    person_filter: Optional[str] = None

    # List of uncertain terms that couldn't be confidently classified
    # These go into a separate lane for human review or learning
    new_terms: List[NewTerm] = None

    # The raw JSON response from GPT (for debugging)
    # Stored so we can inspect what GPT actually returned
    raw_response: Optional[Dict] = None

    def __post_init__(self):
        """Initialize new_terms to empty list if None."""
        if self.new_terms is None:
            self.new_terms = []

    def to_dict(self) -> Dict:
        """
        Convert the full extraction result to a dictionary.

        === WHY WE NEED THIS ===
        When returning results over API or saving to database,
        we need everything in dictionary format that can be JSON-serialized.

        Returns:
            Dictionary with entities array, action, confidence, person filter, and new_terms
        """
        return {
            # Convert each entity to a dictionary
            "entities": [e.to_dict() for e in self.entities],
            "action": self.action,
            "action_confidence": self.action_confidence,
            "person_filter": self.person_filter,
            "new_terms": [t.to_dict() for t in self.new_terms]
            # Note: raw_response is intentionally excluded (debugging only)
        }

    def get_validated_entities(self, query: str) -> List[ExtractedEntity]:
        """
        Return only entities whose evidence appears in the query.

        === HALLUCINATION FILTERING ===
        Removes any entities that the LLM may have hallucinated.

        Args:
            query: The original user query

        Returns:
            List of entities that passed validation
        """
        return [e for e in self.entities if e.validate_evidence(query)]


# =============================================================================
# GPT EXTRACTOR CLASS
# =============================================================================

class GPTExtractor:
    """
    Main class for GPT-based entity extraction and text embeddings.

    === WHAT THIS CLASS DOES ===
    1. extract(): Send text to GPT, get back structured entities
    2. embed(): Convert text to numbers (embedding) for similarity search
    3. embed_batch(): Do multiple embeddings in one API call (faster)

    === HOW TO USE ===
    ```python
    extractor = GPTExtractor()  # Create extractor (needs OPENAI_API_KEY)

    # Extract entities from a query
    result = extractor.extract("Engine is overheating, show historic data")
    print(result.entities)  # [Engine, overheating]
    print(result.action)    # "view_history"

    # Create embedding for similarity search
    embedding = extractor.embed("Engine is overheating")
    print(len(embedding))   # 1536 numbers
    ```

    === MODELS USED ===
    - gpt-4o-mini: For entity extraction (fast, cheap, good quality)
    - text-embedding-3-small: For embeddings (1536 dimensions, same as index)
    """

    def __init__(self, api_key: str = None):
        """
        Initialize the GPT extractor.

        === WHAT HAPPENS HERE ===
        1. Check if openai package is installed
        2. Get API key from parameter or environment variable
        3. Create OpenAI client connection
        4. Set model names and dimensions

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY environment variable.

        Raises:
            ImportError: If openai package not installed
            ValueError: If no API key provided
        """

        # Check if the openai package was successfully imported at top of file
        if not OPENAI_AVAILABLE:
            # If not installed, raise an error with installation instructions
            raise ImportError("openai package not installed. Run: pip install openai>=1.3.0")

        # Get API key - either from parameter or from environment variable
        # Environment variables are set in system settings, not in code (for security)
        # On Render: Set in Dashboard → Environment Variables
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        # If still no API key, we can't continue
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Create the OpenAI client - this handles all API communication
        # The client manages authentication, retries, and connection pooling
        self.client = openai.OpenAI(api_key=self.api_key)

        # === MODEL CONFIGURATION ===

        # Model for entity extraction
        # gpt-4o-mini is optimized for speed and cost while maintaining quality
        # Alternatives: gpt-4o (higher quality, slower, more expensive)
        self.extraction_model = "gpt-4o-mini"

        # Model for creating embeddings (converting text to numbers)
        # CRITICAL: Must match the model used when indexing documents in n8n!
        # If you use a different model at query time vs index time, similarity search breaks.
        self.embedding_model = "text-embedding-3-small"

        # Number of dimensions in embedding vectors
        # text-embedding-3-small produces 1536-dimensional vectors
        # This must match your Supabase vector column dimension
        self.embedding_dimensions = 1536

    def extract(self, query: str) -> ExtractionResult:
        """
        Extract entities and detect action from user query using GPT-4o-mini.

        === HOW THIS WORKS ===
        1. We send the query to GPT with our EXTRACTION_PROMPT (the instructions)
        2. GPT reads the query and identifies entities and actions
        3. GPT returns a JSON response with structured data
        4. We parse that JSON into an ExtractionResult object

        === EXAMPLE ===
        Input: "Engine is overheating, show historic data from the 2nd engineer"
        Output: ExtractionResult with:
            - entities: [Engine (equipment), overheating (symptom)]
            - action: "view_history"
            - person_filter: "2ND_ENGINEER"

        Args:
            query: Natural language user query (what the user typed)

        Returns:
            ExtractionResult with entities, action, and confidence scores
        """

        # Handle empty or whitespace-only queries
        # Return empty result immediately without calling API
        if not query or not query.strip():
            return ExtractionResult(
                entities=[],              # No entities found
                action="general_search",  # Default action
                action_confidence=0.0     # Zero confidence (no query to analyze)
            )

        # Try to call GPT API
        try:
            # Call OpenAI's Chat Completions API
            # This is the same API used by ChatGPT, but we're calling it programmatically
            response = self.client.chat.completions.create(

                # Which model to use
                model=self.extraction_model,  # "gpt-4o-mini"

                # The conversation to send to GPT
                # "system" message = instructions for how GPT should behave
                # "user" message = the actual query to analyze
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},  # Our instructions
                    {"role": "user", "content": query}                 # User's query
                ],

                # IMPORTANT: Force GPT to return valid JSON
                # Without this, GPT might return prose text which would break our parsing
                response_format={"type": "json_object"},

                # Temperature controls randomness (creativity vs consistency)
                # 0.0 = always same answer, 1.0 = very random
                # 0.1 = low randomness, we want consistent extractions
                temperature=0.1,

                # Maximum tokens (words/pieces) in the response
                # 500 is plenty for our structured JSON output
                max_tokens=500
            )

            # Parse the JSON response from GPT
            # response.choices[0].message.content is the text GPT returned
            # json.loads() converts JSON text to Python dictionary
            raw = json.loads(response.choices[0].message.content)

            # === VALIDATE JSON STRUCTURE ===
            # Basic validation to catch malformed responses
            if not isinstance(raw, dict):
                logger.error("GPT response is not a dictionary")
                return self._fallback_extraction(query)

            # === PARSE ENTITIES FROM GPT RESPONSE ===

            # Create empty list to store entities
            entities = []

            # Loop through each entity in GPT's response
            # raw.get("entities", []) returns the entities array, or empty array if missing
            for e in raw.get("entities", []):
                # Skip if not a dictionary
                if not isinstance(e, dict):
                    continue

                # Extract evidence and char positions
                evidence = e.get("evidence", e.get("value", ""))
                start_char = e.get("start_char", -1)
                end_char = e.get("end_char", -1)

                # Validate evidence appears in query (hallucination check)
                if evidence and evidence.lower() not in query.lower():
                    logger.warning(f"Skipping hallucinated entity: {evidence}")
                    continue

                # Create an ExtractedEntity object for each entity GPT found
                entity = ExtractedEntity(
                    # Entity type (equipment, part, symptom, etc.)
                    type=e.get("type", "unknown"),

                    # Original text from query
                    value=e.get("value", ""),

                    # Confidence score (default 0.9 if not provided)
                    confidence=e.get("confidence", 0.9),

                    # Evidence and char spans for validation
                    evidence=evidence,
                    start_char=start_char if isinstance(start_char, int) else -1,
                    end_char=end_char if isinstance(end_char, int) else -1
                )

                entities.append(entity)

            # === PARSE NEW_TERMS (uncertain entities) ===
            new_terms = []
            for t in raw.get("new_terms", []):
                if not isinstance(t, dict):
                    continue
                new_terms.append(NewTerm(
                    term=t.get("term", ""),
                    reason=t.get("reason", "unclassified"),
                    evidence=t.get("evidence", "")
                ))

            # Create and return the full ExtractionResult
            return ExtractionResult(
                entities=entities,                              # List of entities
                action=raw.get("action", "general_search"),     # Detected action
                action_confidence=raw.get("action_confidence", 0.8),  # Action confidence
                person_filter=raw.get("person_filter"),         # Person filter (raw, not canonical)
                new_terms=new_terms,                            # Uncertain terms
                raw_response=raw                                # Store raw response for debugging
            )

        # === ERROR HANDLING ===

        # Handle case where GPT returns invalid JSON
        except json.JSONDecodeError as e:
            logger.error(f"GPT returned invalid JSON: {e}")
            # Fall back to simple keyword extraction
            return self._fallback_extraction(query)

        # Handle OpenAI API errors (rate limits, auth failures, etc.)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            # Fall back to simple keyword extraction
            return self._fallback_extraction(query)

        # Handle any other unexpected errors
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            # Fall back to simple keyword extraction
            return self._fallback_extraction(query)

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text using text-embedding-3-small.

        === WHAT IS AN EMBEDDING? ===
        An embedding converts text into a list of numbers (vector) that represents its meaning.
        Similar texts have similar numbers, different texts have different numbers.

        Example:
        - "engine overheating" → [0.23, -0.45, 0.87, 0.12, ...] (1536 numbers)
        - "motor running hot" → [0.25, -0.42, 0.85, 0.10, ...] (similar numbers!)
        - "birthday cake" → [-0.65, 0.32, -0.21, 0.98, ...] (very different numbers)

        === WHY WE USE THIS ===
        We store embeddings of all documents in Supabase.
        When user searches, we embed their query and find documents with similar embeddings.
        This enables semantic search - finding related content even if words are different.

        === CRITICAL: MODEL CONSISTENCY ===
        MUST use the same embedding model at index time (n8n) and query time (Render).
        If models don't match, similarity scores will be meaningless!

        Args:
            text: Text to embed

        Returns:
            List of 1536 floats (embedding vector)
        """

        # Handle empty or whitespace-only text
        # Return zero vector (all zeros) - this won't match anything well
        if not text or not text.strip():
            return [0.0] * self.embedding_dimensions  # List of 1536 zeros

        try:
            # Call OpenAI's Embeddings API
            response = self.client.embeddings.create(
                model=self.embedding_model,  # "text-embedding-3-small"
                input=text.strip()           # The text to embed (whitespace removed)
            )

            # Return the embedding vector
            # response.data is a list, [0] gets first item, .embedding is the vector
            return response.data[0].embedding

        # Handle OpenAI API errors
        except openai.APIError as e:
            logger.error(f"Embedding API error: {e}")
            # Return zero vector on error (won't match anything well)
            return [0.0] * self.embedding_dimensions

        # Handle any other unexpected errors
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            # Return zero vector on error
            return [0.0] * self.embedding_dimensions

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in one API call.

        === WHY USE BATCH? ===
        More efficient than calling embed() multiple times.
        - Single embed(): 1 API call
        - 10 × embed(): 10 API calls
        - embed_batch(10 texts): 1 API call (10x faster!)

        === WHEN TO USE ===
        Use when you need embeddings for multiple texts at once.
        Example: embedding all chunks of a document at index time.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per input text)
        """

        # Handle empty input
        if not texts:
            return []

        # Clean the texts - remove whitespace and filter empty strings
        # List comprehension: [result for item in list if condition]
        clean_texts = [t.strip() for t in texts if t and t.strip()]

        # If all texts were empty after cleaning, return zero vectors
        if not clean_texts:
            return [[0.0] * self.embedding_dimensions for _ in texts]

        try:
            # Call OpenAI's Embeddings API with multiple inputs
            # The API can embed up to 2048 texts in one call
            response = self.client.embeddings.create(
                model=self.embedding_model,  # "text-embedding-3-small"
                input=clean_texts            # List of texts
            )

            # Extract embedding from each item in response
            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Return zero vectors for all texts on error
            return [[0.0] * self.embedding_dimensions for _ in texts]

    def _fallback_extraction(self, query: str) -> ExtractionResult:
        """
        Fallback extraction when GPT fails (API error, invalid response, etc.)

        === WHAT THIS DOES ===
        Uses simple keyword matching as a backup when GPT is unavailable.
        Much simpler than GPT - just looks for exact keywords.
        Quality is lower (confidence 0.5-0.6) but better than nothing.

        === WHEN THIS IS USED ===
        - OpenAI API is down
        - Rate limit exceeded
        - API key invalid
        - GPT returns malformed JSON

        Args:
            query: The original query text

        Returns:
            ExtractionResult with lower-confidence extractions
        """

        # Log that we're using fallback (for debugging)
        logger.warning(f"Using fallback extraction for: {query}")

        # Create empty list for found entities
        entities = []

        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()

        # === SIMPLE EQUIPMENT DETECTION ===
        # Dictionary of keywords to look for
        equipment_keywords = ["engine", "generator", "pump", "compressor", "heat exchanger"]

        # Check each keyword
        for keyword in equipment_keywords:
            # Find position in query
            pos = query_lower.find(keyword)
            if pos != -1:  # Found
                entities.append(ExtractedEntity(
                    type="equipment",
                    value=keyword,
                    confidence=0.6,  # Lower confidence than GPT
                    evidence=keyword,
                    start_char=pos,
                    end_char=pos + len(keyword)
                ))

        # === SIMPLE SYMPTOM DETECTION ===
        symptom_keywords = ["overheating", "leak", "vibration", "noise"]

        for keyword in symptom_keywords:
            pos = query_lower.find(keyword)
            if pos != -1:
                entities.append(ExtractedEntity(
                    type="symptom",
                    value=keyword,
                    confidence=0.6,
                    evidence=keyword,
                    start_char=pos,
                    end_char=pos + len(keyword)
                ))

        # === SIMPLE ACTION DETECTION ===
        action = "general_search"  # Default action

        # Check for history-related keywords
        if "history" in query_lower or "historic" in query_lower:
            action = "view_history"
        # Check for work order creation keywords
        elif "create" in query_lower and "work" in query_lower:
            action = "create_work_order"
        # Check for diagnostic keywords
        elif "diagnose" in query_lower or "troubleshoot" in query_lower:
            action = "diagnose_fault"

        # Return result with lower confidence
        return ExtractionResult(
            entities=entities,
            action=action,
            action_confidence=0.5,  # Low confidence - this is a fallback
            new_terms=[]  # No new terms in fallback mode
        )


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

# Singleton = Only one instance of GPTExtractor exists in the entire application.
# This is important because:
# 1. Avoid creating multiple OpenAI clients (wasteful)
# 2. Ensure consistent configuration across all uses
# 3. Reuse the same connection for efficiency

# Module-level variable to store the single instance
# Starts as None, will be created on first use
_extractor_instance = None

def get_gpt_extractor() -> GPTExtractor:
    """
    Get or create the singleton GPT extractor instance.

    === WHAT IS A SINGLETON? ===
    A pattern where only ONE instance of a class exists.
    Every time you call this function, you get the SAME instance.

    === WHY USE THIS? ===
    1. Efficiency: Don't create multiple OpenAI clients
    2. Consistency: Same configuration everywhere
    3. Resource management: Only one connection to OpenAI

    === HOW TO USE ===
    Don't create GPTExtractor directly. Instead:
    ```python
    extractor = get_gpt_extractor()  # Gets the singleton
    result = extractor.extract("some query")
    ```

    Returns:
        The singleton GPTExtractor instance
    """

    # Reference the global variable
    global _extractor_instance

    # If instance doesn't exist yet, create it
    if _extractor_instance is None:
        _extractor_instance = GPTExtractor()

    # Return the (existing or newly created) instance
    return _extractor_instance


# =============================================================================
# TEST / MAIN
# =============================================================================

# This block only runs when you execute this file directly:
# python extraction/gpt_extractor.py
#
# It does NOT run when you import this file:
# from extraction import GPTExtractor
#
# This is useful for testing the module independently.

if __name__ == "__main__":
    # Print header
    print("GPT Extractor Test")
    print("=" * 60)

    try:
        # Create a GPT extractor instance
        # Will raise error if OPENAI_API_KEY not set
        extractor = GPTExtractor()

        # Test queries to demonstrate extraction
        test_queries = [
            "Engine is overheating, show historic data from the 2nd engineer",
            "What does error code E047 mean?",
            "Create work order for bilge pump inspection",
            "Find oil filter for generator 1",
            "The XYZABC unit is making noise"  # Test new_terms with unknown term
        ]

        # Process each test query
        for query in test_queries:
            print(f"\nQuery: '{query}'")

            # Extract entities and action
            result = extractor.extract(query)

            # Print results
            print(f"Action: {result.action} (confidence: {result.action_confidence:.2f})")
            print(f"Person filter: {result.person_filter}")
            print(f"Entities:")
            for e in result.entities:
                print(f"  - {e.type}: '{e.value}' @ chars {e.start_char}-{e.end_char}")
                print(f"    evidence: '{e.evidence}' (conf: {e.confidence:.2f})")

            # Print new_terms if any
            if result.new_terms:
                print(f"New Terms (uncertain):")
                for t in result.new_terms:
                    print(f"  - '{t.term}' ({t.reason})")

            # Test embedding
            embedding = extractor.embed(query)
            print(f"Embedding: {len(embedding)} dimensions")

    except Exception as e:
        # If anything fails, print error and hint
        print(f"Error: {e}")
        print("Make sure OPENAI_API_KEY is set")
