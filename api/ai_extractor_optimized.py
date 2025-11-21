#!/usr/bin/env python3
"""
Stage 3: AI Residual Extraction - OPTIMIZED FOR 3B MODEL
Balanced prompt that works with 3B model while maintaining accuracy
"""

import json
import requests
import logging
import re
from typing import Dict, List, Tuple, Optional
from regex_extractor import Entity

logger = logging.getLogger(__name__)


class AIExtractor:
    """AI-based extraction optimized for accuracy and 3B compatibility."""

    def __init__(self, model_url: str = "http://localhost:11434/api/generate",
                 model_name: str = "qwen2.5:3b-instruct-q5_K_M"):
        self.model_url = model_url
        self.model_name = model_name
        self.timeout = 10

    def extract(self, full_text: str, uncovered_spans: List[Tuple[int, int]] = None) -> Dict:
        """
        Extract entities using optimized AI prompt.

        Args:
            full_text: Complete normalized text
            uncovered_spans: Optional spans to focus on

        Returns:
            Dict with entities following schema v0.2.2
        """
        if not full_text or not full_text.strip():
            return self._empty_response()

        try:
            # Use optimized prompt
            prompt = self._build_optimized_prompt(full_text)
            response = self._call_model(prompt)
            result = self._parse_response(response)

            if result and 'entities' in result:
                return result
            else:
                logger.warning("AI returned incomplete result, using fallback")
                return self._fallback_extraction(full_text)

        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return self._fallback_extraction(full_text)

    def _build_optimized_prompt(self, text: str) -> str:
        """Build optimized prompt with examples for 3B model - ONLY extract what exists in text."""
        prompt = f"""Extract maritime entities from text. CRITICAL: Only extract entities that are EXPLICITLY mentioned in the text.

STRICT RULES:
1. ONLY extract organizations/brands if EXPLICITLY NAMED in the text
   - WRONG: "main engine" → {{"org": ["Caterpillar"]}}  (NOT mentioned!)
   - RIGHT: "main engine" → {{"org": []}}  (no brand mentioned)
   - RIGHT: "Caterpillar main engine" → {{"org": ["Caterpillar"], "equipment": ["main engine"]}}

2. ONLY extract locations if EXPLICITLY STATED in the text
   - WRONG: "engine temperature" → {{"location_on_board": ["engine room"]}}  (NOT mentioned!)
   - RIGHT: "engine temperature" → {{"location_on_board": []}}  (no location mentioned)
   - RIGHT: "engine room temperature" → {{"location_on_board": ["engine room"]}}

3. Extract each equipment item separately UNLESS they form a recognized compound term
   - Compound terms: "battery bank", "main engine", "bow thruster"
   - Separate items: extract BOTH if adjacent

4. Normalize measurements: 27,6V → "27.6 V", 95℃ → "95 °C"
5. Preserve negations as phrases: "do not start", "avoid resetting"
6. Uppercase fault codes: warn-335 → "WARN-335"

Example (NO brand mentioned):
Input: "main engine overheating troubleshooting"
Output: {{"entities": {{"equipment": ["main engine"], "symptom": ["overheating"], "action": ["troubleshooting"], "org": [], "location_on_board": []}}}}

Example (NO location mentioned):
Input: "battery voltage 27.6V low"
Output: {{"entities": {{"equipment": ["battery"], "measurement": ["27.6 V"], "symptom": ["low"], "location_on_board": []}}}}

Example (brand IS mentioned):
Input: "Yanmar 3JH5E engine maintenance"
Output: {{"entities": {{"org": ["Yanmar"], "model": ["3JH5E"], "equipment": ["engine"], "action": ["maintenance"]}}}}

Example (location IS mentioned):
Input: "Battery bank voltage in engine room"
Output: {{"entities": {{"equipment": ["battery bank"], "measurement": ["voltage"], "location_on_board": ["engine room"]}}}}

Example (fault with negation):
Input: "Do not start main engine, alarm WARN-335"
Output: {{"entities": {{"action": ["do not start"], "equipment": ["main engine"], "status": ["alarm"], "fault_code": ["WARN-335"]}}}}

Example (brand and model mentioned):
Input: "What voltage does Northern Lights M843W require"
Output: {{"entities": {{"org": ["Northern Lights"], "model": ["M843W"], "measurement": ["voltage"]}}}}

Now extract from: "{text}"

REMEMBER: If a brand/manufacturer is NOT explicitly mentioned in the text, the org array MUST be empty.
If a location is NOT explicitly mentioned in the text, the location_on_board array MUST be empty.

Return JSON with ALL these entity types (use empty array if none found):
- equipment (engine, pump, generator, compressor)
- subcomponent (filter, belt, seal, bearing)
- system (hydraulic system, cooling system, electrical system)
- location_on_board (ONLY if explicitly mentioned: engine room, bridge, galley)
- action (check, inspect, repair, replace, troubleshoot)
- status (running, failed, scheduled, completed)
- symptom (noise, vibration, leak, overheating, not starting)
- measurement (voltage, current, temperature, pressure with units)
- fault_code (error codes like WARN-335, SPN-1234)
- time, date (preserve format)
- person (role titles: captain, engineer, crew)
- document_type (manual, logbook, certificate)
- document_id (WO-2024-001, SR-12345)
- model (3512C, QSM11, C32 - ONLY if mentioned)
- org (manufacturer/brand name - ONLY if explicitly mentioned!)
- network_id (IP addresses, MAC addresses)
- identifier (serial numbers, part numbers)

Output JSON:"""

        return prompt

    def _call_model(self, prompt: str) -> str:
        """Call the AI model with optimized settings."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 600,  # Balanced for accuracy
                "seed": 42,
                "stop": ["\n\n\n", "```", "### END ###"]
            }
        }

        response = requests.post(
            self.model_url,
            json=payload,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise Exception(f"Model returned status {response.status_code}")

        result = response.json()
        return result.get('response', '{}')

    def _parse_response(self, response: str) -> Dict:
        """Parse and validate AI response."""
        try:
            # Clean response
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

            # Try to extract JSON from response
            # Sometimes model adds text before/after JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                response = response[json_start:json_end]

            # Parse JSON
            data = json.loads(response)

            if not isinstance(data, dict):
                logger.error("Response is not a dict")
                return self._empty_response()

            # Extract entities
            if 'entities' in data:
                entities = data['entities']
            else:
                entities = data

            # Normalize entities
            normalized = self._normalize_entities(entities)

            return {
                'schema_version': '0.2.2',
                'entities': normalized,
                'metadata': {
                    'needs_ai': True,
                    'coverage': 0.0,
                    'source_mix': {'regex': 0, 'gazetteer': 0, 'ai': 1}
                }
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}, response: {response[:200]}")
            return self._empty_response()
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return self._empty_response()

    def _normalize_entities(self, entities: Dict) -> Dict:
        """Normalize and validate entity values."""
        VALID_TYPES = {
            'equipment', 'subcomponent', 'system', 'location_on_board',
            'action', 'status', 'symptom', 'measurement', 'fault_code',
            'time', 'date', 'person', 'document_id', 'document_type',
            'model', 'org', 'network_id', 'identifier'
        }

        normalized = {}

        for entity_type in VALID_TYPES:
            if entity_type in entities:
                values = entities[entity_type]
                if isinstance(values, list):
                    cleaned = []
                    for v in values:
                        if v and isinstance(v, str):
                            val = v.strip()

                            # Type-specific normalization
                            if entity_type == 'measurement':
                                val = self._normalize_measurement(val)
                            elif entity_type == 'location_on_board':
                                val = val.lower()
                            elif entity_type == 'fault_code':
                                val = val.upper()
                            elif entity_type == 'equipment':
                                # Ensure compound terms stay together
                                val = self._normalize_equipment(val)

                            if val:
                                cleaned.append(val)
                    normalized[entity_type] = cleaned
                else:
                    normalized[entity_type] = []
            else:
                normalized[entity_type] = []

        return normalized

    def _normalize_equipment(self, value: str) -> str:
        """Normalize equipment names, preserving compound terms."""
        # Common compound terms to preserve
        compound_terms = {
            'battery bank': 'battery bank',
            'batteries': 'battery bank',  # Map variations
            'battery': 'battery',  # Keep single battery
            'main engine': 'main engine',
            'bow thruster': 'bow thruster',
            'fire pump': 'fire pump',
            'steering gear': 'steering gear',
            'galley equipment': 'galley equipment'
        }

        value_lower = value.lower().strip()

        # Check for known compound terms
        for key, normalized in compound_terms.items():
            if key in value_lower:
                return normalized

        return value.strip()

    def _normalize_measurement(self, value: str) -> str:
        """Comprehensive measurement normalization."""
        # Handle European decimal notation
        if ',' in value and not '.' in value:
            if re.match(r'^\d+,\d+\s*\w*', value):
                value = value.replace(',', '.')
        elif ',' in value and '.' in value:
            # Handle thousands separator (1.200,5 → 1200.5)
            if re.match(r'^\d+\.\d{3},\d+', value):
                value = value.replace('.', '').replace(',', '.')

        # Temperature normalization
        value = value.replace('℃', ' °C').replace('℉', ' °F')
        value = re.sub(r'(\d+)\s*°?\s*[cC](?!\w)', r'\1 °C', value)
        value = re.sub(r'(\d+)\s*°?\s*[fF](?!\w)', r'\1 °F', value)

        # Voltage normalization
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[vV](?:[dD][cC])?', r'\1 V DC', value)
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[vV](?:[aA][cC])?', r'\1 V AC', value)
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[vV](?!\s)', r'\1 V', value)

        # Handle patterns like "24/12V"
        value = re.sub(r'(\d+/\d+)\s*[vV]', r'\1 V', value)

        # Current normalization
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[aA](?!\w)', r'\1 A', value)
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[mM][aA](?!\w)', r'\1 mA', value)

        # Pressure normalization
        value = re.sub(r'(\d+(?:\.\d+)?)\s*bar\b', r'\1 bar', value, flags=re.IGNORECASE)
        value = re.sub(r'(\d+(?:\.\d+)?)\s*psi\b', r'\1 PSI', value, flags=re.IGNORECASE)

        # Frequency normalization
        value = re.sub(r'(\d+)\s*[hH][zZ]', r'\1 Hz', value)

        # RPM normalization
        value = re.sub(r'(\d+)\s*rpm', r'\1 RPM', value, flags=re.IGNORECASE)

        # Clean up spacing
        value = re.sub(r'\s+', ' ', value).strip()

        return value

    def _fallback_extraction(self, text: str) -> Dict:
        """Simple fallback for difficult cases."""
        try:
            prompt = f"""Extract: "{text[:100]}"
Output: {{"entities": {{"equipment": [], "measurement": [], "status": []}}}}"""

            response = self._call_model(prompt)

            # Try to extract JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                response = response[json_start:json_end]

            data = json.loads(response)

            if isinstance(data, dict):
                return {
                    'schema_version': '0.2.2',
                    'entities': self._normalize_entities(data.get('entities', data)),
                    'metadata': {
                        'needs_ai': True,
                        'coverage': 0.0,
                        'source_mix': {'regex': 0, 'gazetteer': 0, 'ai': 1}
                    }
                }
        except Exception as e:
            logger.error(f"Fallback failed: {e}")

        return self._empty_response()

    def _empty_response(self) -> Dict:
        """Return empty response structure."""
        return {
            'schema_version': '0.2.2',
            'entities': {
                'equipment': [],
                'subcomponent': [],
                'system': [],
                'location_on_board': [],
                'action': [],
                'status': [],
                'symptom': [],
                'measurement': [],
                'fault_code': [],
                'time': [],
                'date': [],
                'person': [],
                'document_id': [],
                'document_type': [],
                'model': [],
                'org': [],
                'network_id': [],
                'identifier': []
            },
            'metadata': {
                'needs_ai': True,
                'coverage': 0.0,
                'source_mix': {'regex': 0, 'gazetteer': 0, 'ai': 0}
            }
        }

    def is_available(self) -> bool:
        """Check if AI model is available."""
        try:
            response = requests.get(
                self.model_url.replace('/api/generate', '/api/tags'),
                timeout=1
            )
            return response.status_code == 200
        except:
            return False