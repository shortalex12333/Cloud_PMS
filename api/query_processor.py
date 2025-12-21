"""
Query Processor (Unified Pipeline)
===================================

Combines intent parsing + entity extraction into a single entry point.

Flow:
1. Parse intent (GPT or fallback)
2. Extract entities (regex patterns)
3. Route to appropriate handler

Output:
{
    "intent": {...},
    "entities": [...],
    "routing": {...},
    "processing_time_ms": 45
}
"""

import time
from typing import Dict, Optional

from intent_parser import IntentParser, ParsedIntent, route_query
from module_b_entity_extractor import get_extractor


class QueryProcessor:
    """
    Unified query processing pipeline.
    """

    def __init__(self, use_gpt: bool = True):
        self.use_gpt = use_gpt
        self.intent_parser = IntentParser()
        self.entity_extractor = get_extractor()

    def process(self, query: str, yacht_id: Optional[str] = None) -> Dict:
        """
        Process a query through the full pipeline.

        Args:
            query: User's natural language query
            yacht_id: Optional yacht context for entity extraction

        Returns:
            Complete processing result with intent, entities, and routing
        """
        start_time = time.time()

        # Step 1: Parse intent
        parsed_intent = self.intent_parser.parse(query)

        # Step 2: Extract entities (regex patterns)
        extraction_result = self.entity_extractor.extract_with_unknowns(
            query,
            yacht_id,
            log_unknowns=True
        )

        # Step 3: Merge GPT entities with regex entities (if GPT was used)
        # GPT intent parsing may also extract entities
        gpt_entities = parsed_intent.entities
        if gpt_entities:
            # Convert GPT entities to our format
            for entity_type, value in gpt_entities.items():
                if value:
                    extraction_result['entities'].append({
                        'type': entity_type,
                        'value': value,
                        'canonical': value.upper().replace(' ', '_'),
                    })

        # Step 4: Determine routing
        routing = route_query(parsed_intent)

        # Build response
        processing_time = (time.time() - start_time) * 1000

        return {
            'query': query,
            'intent': {
                'action': parsed_intent.intent,
                'category': parsed_intent.intent_category,
                'query_type': parsed_intent.query_type,
                'confidence': parsed_intent.confidence,
                'requires_mutation': parsed_intent.requires_mutation,
            },
            'entities': extraction_result['entities'],
            'unknowns': extraction_result['unknowns'],
            'routing': routing,
            'processing_time_ms': round(processing_time, 2),
        }


def process_query(query: str, yacht_id: Optional[str] = None) -> Dict:
    """
    Main entry point for query processing.
    """
    processor = QueryProcessor()
    return processor.process(query, yacht_id)


if __name__ == "__main__":
    import json

    print("Query Processor Test")
    print("=" * 70)

    test_queries = [
        "MTU 16V4000 engine overheating",
        "what machines are failing the most",
        "who hasn't completed their hours of rest",
        "create work order for stabilizer fault",
        "show me box 3d contents",
        "order 2 MTU fuel filters",
        "Seakeeper gyro making noise",
    ]

    processor = QueryProcessor()

    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        result = processor.process(query)

        print(f"  Intent: {result['intent']['action']} ({result['intent']['category']})")
        print(f"  Type: {result['intent']['query_type']}")
        print(f"  Mutation: {result['intent']['requires_mutation']}")
        print(f"  Route: {result['routing']['handler']} → {result['routing'].get('endpoint') or result['routing'].get('webhook')}")

        if result['entities']:
            print(f"  Entities: {result['entities']}")
        if result['unknowns']:
            print(f"  Unknowns: {result['unknowns']}")

        print(f"  Time: {result['processing_time_ms']}ms")
