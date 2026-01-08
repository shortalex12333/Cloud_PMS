#!/usr/bin/env python3
"""
AI Residual Extraction - OpenAI GPT-4 Turbo
Cloud-optimized replacement for local Ollama qwen2.5:3b
"""

import json
import os
import logging
from typing import Dict, List, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIExtractor:
    """AI-based extraction using OpenAI GPT-4 Turbo."""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-4-turbo-preview"
        self.timeout = 30

    def extract(self, full_text: str, uncovered_spans: List[Tuple[int, int]] = None) -> Dict:
        """
        Extract entities using OpenAI GPT-4.

        Args:
            full_text: Complete normalized text
            uncovered_spans: Optional spans to focus on

        Returns:
            Dict with entities following schema v0.2.2
        """
        if not full_text or not full_text.strip():
            return self._empty_response()

        try:
            prompt = self._build_prompt(full_text)
            response = self._call_openai(prompt)
            result = self._parse_response(response)

            if result and 'entities' in result:
                return result
            else:
                logger.warning("OpenAI returned incomplete result")
                return self._empty_response()

        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            return self._empty_response()

    def _build_prompt(self, text: str) -> str:
        """Build prompt for OpenAI - optimized for maritime domain."""
        return f"""Extract maritime entities from the text. CRITICAL RULES:

1. ONLY extract entities that are EXPLICITLY mentioned in the text
   - WRONG: "main engine" → {{"org": ["Caterpillar"]}} (NOT mentioned!)
   - RIGHT: "main engine" → {{"org": []}} (no brand mentioned)
   - RIGHT: "Caterpillar main engine" → {{"org": ["Caterpillar"], "equipment": ["main engine"]}}

2. ONLY extract locations if EXPLICITLY STATED
   - WRONG: "engine temperature" → {{"location_on_board": ["engine room"]}} (NOT mentioned!)
   - RIGHT: "engine temperature" → {{"location_on_board": []}}
   - RIGHT: "engine room temperature" → {{"location_on_board": ["engine room"]}}

3. Extract compound terms correctly
   - Compound: "battery bank", "main engine", "bow thruster"
   - Separate: extract BOTH if adjacent but not forming compound

4. Normalize measurements: 27,6V → "27.6 V", 95℃ → "95 °C"

5. Preserve negations: "do not start", "avoid resetting"

6. Uppercase fault codes: "warn-335" → "WARN-335"

EXAMPLES:

Input: "main engine overheating troubleshooting"
Output: {{"equipment": ["main engine"], "symptom": ["overheating"], "action": ["troubleshooting"], "org": [], "location_on_board": []}}

Input: "battery voltage 27.6V low"
Output: {{"equipment": ["battery"], "measurement": ["27.6 V"], "symptom": ["low"], "location_on_board": []}}

Input: "Yanmar 3JH5E engine maintenance"
Output: {{"org": ["Yanmar"], "model": ["3JH5E"], "equipment": ["engine"], "action": ["maintenance"]}}

Input: "Battery bank voltage in engine room"
Output: {{"equipment": ["battery bank"], "measurement": ["voltage"], "location_on_board": ["engine room"]}}

Input: "Do not start main engine, alarm WARN-335"
Output: {{"action": ["do not start"], "equipment": ["main engine"], "status": ["alarm"], "fault_code": ["WARN-335"]}}

Input: "What voltage does Northern Lights M843W require"
Output: {{"org": ["Northern Lights"], "model": ["M843W"], "measurement": ["voltage"]}}

TEXT TO EXTRACT FROM:
"{text}"

Return JSON with these entity types (use empty array if none found):
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
- org (manufacturer/brand - ONLY if explicitly mentioned!)
- network_id (IP addresses, MAC addresses)
- identifier (serial numbers, part numbers)

Output ONLY valid JSON, no explanation."""

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API with structured output."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a maritime equipment entity extractor. Extract only entities explicitly mentioned in the text. Return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=800,
                timeout=self.timeout
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    def _parse_response(self, response: str) -> Dict:
        """Parse and validate OpenAI response."""
        try:
            data = json.loads(response)

            if not isinstance(data, dict):
                logger.error("Response is not a dict")
                return self._empty_response()

            # Extract entities
            entities = data.get('entities', data)

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
        import re

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

                            if val:
                                cleaned.append(val)
                    normalized[entity_type] = cleaned
                else:
                    normalized[entity_type] = []
            else:
                normalized[entity_type] = []

        return normalized

    def _normalize_measurement(self, value: str) -> str:
        """Comprehensive measurement normalization."""
        import re

        # Handle European decimal notation
        if ',' in value and '.' not in value:
            if re.match(r'^\d+,\d+\s*\w*', value):
                value = value.replace(',', '.')

        # Temperature normalization
        value = value.replace('℃', ' °C').replace('℉', ' °F')
        value = re.sub(r'(\d+)\s*°?\s*[cC](?!\w)', r'\1 °C', value)
        value = re.sub(r'(\d+)\s*°?\s*[fF](?!\w)', r'\1 °F', value)

        # Voltage normalization
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[vV](?!\s)', r'\1 V', value)

        # Current normalization
        value = re.sub(r'(\d+(?:\.\d+)?)\s*[aA](?!\w)', r'\1 A', value)

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
        """Check if OpenAI API is available."""
        try:
            # Quick test - list models
            self.client.models.list()
            return True
        except:
            return False
