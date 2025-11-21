"""
Module A: Strict Micro-Action & Intent Detector
================================================

STRICT RULES:
- Only verb-based action patterns
- NO phrasal regex ("find the", "tell me", "where is")
- NO patterns that could match maritime terms
- Confidence scoring required
- Maritime nouns CANNOT trigger actions
- Fault codes NEVER trigger actions

This module detects what the user WANTS TO DO, not what they're talking about.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ActionDetection:
    """Detected action with confidence"""
    action: str
    confidence: float
    matched_text: str
    verb: str

    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "confidence": self.confidence,
            "matched_text": self.matched_text,
            "verb": self.verb
        }


class StrictMicroActionDetector:
    """
    Strict micro-action detector using ONLY explicit verb patterns.

    Design principles:
    1. Actions must start with explicit verbs
    2. No ambiguous phrases
    3. No patterns that could match entity descriptions
    4. Confidence based on pattern specificity
    """

    def __init__(self):
        # Strict verb-based patterns for each action
        # Format: action_name -> [(pattern, base_confidence, verb), ...]
        self.action_patterns = {
            # Work Order actions - EXPLICIT VERBS ONLY
            "create_work_order": [
                (r"^create\s+(a\s+)?(new\s+)?work\s*order", 0.95, "create"),
                (r"^open\s+(a\s+)?(new\s+)?work\s*order", 0.95, "open"),
                (r"^raise\s+(a\s+)?work\s*order", 0.92, "raise"),
                (r"^generate\s+work\s*order", 0.90, "generate"),
                (r"^add\s+(a\s+)?work\s*order", 0.88, "add"),
                (r"^log\s+(a\s+)?work\s*order", 0.88, "log"),
            ],

            "list_work_orders": [
                (r"^show\s+(all\s+)?(open\s+|pending\s+|active\s+)?work\s*orders", 0.93, "show"),
                (r"^list\s+(all\s+)?(open\s+)?work\s*orders", 0.93, "list"),
                (r"^view\s+(all\s+)?work\s*orders", 0.90, "view"),
                (r"^display\s+work\s*orders", 0.90, "display"),
            ],

            "update_work_order": [
                (r"^update\s+(the\s+)?work\s*order", 0.93, "update"),
                (r"^edit\s+(the\s+)?work\s*order", 0.93, "edit"),
                (r"^modify\s+(the\s+)?work\s*order", 0.90, "modify"),
                (r"^change\s+(the\s+)?work\s*order", 0.88, "change"),
            ],

            "close_work_order": [
                (r"^close\s+(the\s+)?work\s*order", 0.95, "close"),
                (r"^complete\s+(the\s+)?work\s*order", 0.93, "complete"),
                (r"^finish\s+(the\s+)?work\s*order", 0.90, "finish"),
            ],

            # Handover actions - EXPLICIT VERBS ONLY
            "add_to_handover": [
                (r"^add\s+(this\s+|it\s+)?to\s+(the\s+)?handover", 0.95, "add"),
                (r"^put\s+in\s+handover", 0.90, "put"),
                (r"^include\s+in\s+handover", 0.88, "include"),
            ],

            "export_handover": [
                (r"^export\s+(the\s+)?handover", 0.95, "export"),
                (r"^download\s+(the\s+)?handover", 0.93, "download"),
                (r"^generate\s+(the\s+)?handover", 0.90, "generate"),
            ],

            "view_handover": [
                (r"^view\s+(the\s+)?handover", 0.92, "view"),
                (r"^show\s+(the\s+)?handover", 0.92, "show"),
                (r"^display\s+handover", 0.90, "display"),
            ],

            # Fault actions - EXPLICIT VERBS ONLY
            "report_fault": [
                (r"^report\s+(a\s+)?fault", 0.95, "report"),
                (r"^log\s+(a\s+)?fault", 0.93, "log"),
                (r"^raise\s+(a\s+)?fault", 0.90, "raise"),
            ],

            "diagnose_fault": [
                (r"^diagnose\s+(the\s+)?fault", 0.95, "diagnose"),
                (r"^diagnose\s+[EePp]\d{3,4}", 0.93, "diagnose"),  # diagnose E047, P0420, etc.
                (r"^diagnose\s+SPN", 0.93, "diagnose"),  # diagnose SPN
                (r"^diagnose\s+\w+", 0.85, "diagnose"),  # diagnose <anything>
                (r"^troubleshoot\s+(the\s+)?fault", 0.93, "troubleshoot"),
                (r"^investigate\s+(the\s+)?fault", 0.90, "investigate"),
            ],

            "acknowledge_fault": [
                (r"^acknowledge\s+(the\s+)?fault", 0.95, "acknowledge"),
                (r"^ack\s+(the\s+)?fault", 0.93, "ack"),
            ],

            # Inventory actions - EXPLICIT VERBS ONLY
            "check_stock": [
                (r"^check\s+stock", 0.95, "check"),
                (r"^check\s+inventory", 0.93, "check"),
                (r"^view\s+stock\s+levels", 0.90, "view"),
            ],

            "order_parts": [
                (r"^order\s+parts?", 0.95, "order"),
                (r"^request\s+spares?", 0.93, "request"),
                (r"^purchase\s+parts?", 0.90, "purchase"),
            ],

            # Document actions - EXPLICIT VERBS ONLY
            "upload_document": [
                (r"^upload\s+(a\s+)?(document|manual|file|pdf)", 0.95, "upload"),
                (r"^add\s+(a\s+)?(document|manual)", 0.90, "add"),
                (r"^attach\s+(a\s+)?(document|manual)", 0.88, "attach"),
            ],

            "search_documents": [
                (r"^search\s+(for\s+)?(documents?|manuals?|procedures?)", 0.93, "search"),
                (r"^find\s+(documents?|manuals?|procedures?)", 0.90, "find"),
            ],

            # Purchasing actions - EXPLICIT VERBS ONLY
            "create_purchase_request": [
                (r"^create\s+(a\s+)?purchase\s+request", 0.95, "create"),
                (r"^raise\s+(a\s+)?purchase\s+request", 0.90, "raise"),
            ],

            "approve_purchase_order": [
                (r"^approve\s+(the\s+)?purchase\s+order", 0.95, "approve"),
                (r"^authorize\s+(the\s+)?purchase", 0.90, "authorize"),
            ],

            # Hours of Rest - EXPLICIT VERBS ONLY
            "log_hours_of_rest": [
                (r"^log\s+(my\s+)?hours\s+of\s+rest", 0.95, "log"),
                (r"^record\s+(my\s+)?hours\s+of\s+rest", 0.93, "record"),
                (r"^enter\s+hours\s+of\s+rest", 0.90, "enter"),
            ],
        }

        # Compile all patterns
        self.compiled_patterns = {}
        for action, patterns in self.action_patterns.items():
            self.compiled_patterns[action] = [
                (re.compile(pattern, re.IGNORECASE), confidence, verb)
                for pattern, confidence, verb in patterns
            ]

    def detect_actions(self, query: str) -> List[ActionDetection]:
        """
        Detect micro-actions in query using STRICT verb-based patterns.

        Returns list of ActionDetection objects with confidence scores.
        """
        if not query or not query.strip():
            return []

        query = query.strip().lower()
        detections = []

        for action_name, patterns in self.compiled_patterns.items():
            for pattern, base_confidence, verb in patterns:
                match = pattern.search(query)
                if match:
                    # Calculate confidence
                    confidence = base_confidence

                    # Boost confidence if match is at start of query
                    if match.start() == 0:
                        confidence = min(confidence * 1.05, 1.0)

                    # Boost confidence for longer, more specific matches
                    match_length = len(match.group(0))
                    if match_length > 20:
                        confidence = min(confidence * 1.03, 1.0)

                    detections.append(ActionDetection(
                        action=action_name,
                        confidence=confidence,
                        matched_text=match.group(0),
                        verb=verb
                    ))

        return detections

    def get_best_action(self, query: str, min_confidence: float = 0.4) -> Optional[ActionDetection]:
        """
        Get the single best action detection above confidence threshold.

        Returns None if no action detected or confidence too low.
        """
        detections = self.detect_actions(query)

        if not detections:
            return None

        # Sort by confidence descending
        detections.sort(key=lambda x: x.confidence, reverse=True)
        best = detections[0]

        # Check confidence threshold
        if best.confidence < min_confidence:
            return None

        return best

    def detect_intent(self, query: str) -> Optional[str]:
        """
        Detect high-level intent from query.

        Intent categories:
        - create: User wants to create something
        - update: User wants to modify something
        - view: User wants to see information
        - action: User wants to perform an action
        - search: User wants to find something
        """
        best_action = self.get_best_action(query)

        if not best_action:
            return None

        # Map actions to intents
        intent_map = {
            "create": ["create_work_order", "create_purchase_request"],
            "update": ["update_work_order", "edit_work_order"],
            "view": ["list_work_orders", "view_handover", "check_stock"],
            "action": ["close_work_order", "approve_purchase_order", "diagnose_fault"],
            "search": ["search_documents", "find_manual"],
        }

        for intent, actions in intent_map.items():
            if best_action.action in actions:
                return intent

        return "action"  # Default intent


# Singleton instance
_detector_instance = None

def get_detector() -> StrictMicroActionDetector:
    """Get or create singleton detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = StrictMicroActionDetector()
    return _detector_instance


if __name__ == "__main__":
    # Quick tests
    detector = StrictMicroActionDetector()

    test_cases = [
        ("create work order for bilge pump", True),  # Should detect
        ("bilge manifold", False),  # Should NOT detect
        ("sea water pump", False),  # Should NOT detect
        ("diagnose E047 on ME1", True),  # Should detect
        ("tell me bilge pump", False),  # Should NOT detect (no verb)
        ("find coolant temp", False),  # Ambiguous, should NOT detect unless "find document"
        ("open work order", True),  # Should detect
    ]

    print("Module A: Strict Micro-Action Detector - Quick Tests")
    print("=" * 60)

    for query, should_detect in test_cases:
        detection = detector.get_best_action(query)
        detected = detection is not None
        status = "✅" if detected == should_detect else "❌"

        if detection:
            print(f"{status} '{query}'")
            print(f"   → Action: {detection.action}, Confidence: {detection.confidence:.2f}, Verb: {detection.verb}")
        else:
            print(f"{status} '{query}'")
            print(f"   → No action detected")
        print()
