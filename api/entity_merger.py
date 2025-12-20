#!/usr/bin/env python3
"""
Stage 4: Entity Merger v2.0
Merges regex and AI entities, handles deduplication and validation
Features: score-based overlap resolution, centralized config, reason codes
"""

import re
from typing import Dict, List, Set, Tuple
try:
    from api.regex_extractor import Entity
    from api.extraction_config import config as extraction_config
except ImportError:
    from regex_extractor import Entity
    from extraction_config import config as extraction_config


class EntityMerger:
    """Merges and validates entities from multiple sources with configurable thresholds."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # Use centralized configuration (with backward compatibility)
        self.confidence_thresholds = extraction_config.confidence_thresholds
        self.source_multipliers = extraction_config.source_multipliers
        self.overlap_weights = extraction_config.overlap_weights
        self.type_precedence = extraction_config.type_precedence

        # Metrics tracking
        self.metrics = {
            'entities_filtered': 0,
            'entities_kept': 0,
            'overlaps_resolved': 0,
            'reason_codes': {}
        }

    def merge_and_validate(self, regex_entities: List[Entity],
                          ai_entities: List[Entity],
                          full_text: str) -> Dict:
        """
        Merge entities from regex and AI extraction.

        Returns:
            {
                'entities': List[Entity],  # Merged and validated
                'source_mix': Dict  # Count by source
            }
        """
        # Combine all entities
        all_entities = regex_entities + ai_entities

        # Remove duplicates and overlaps
        deduplicated = self._deduplicate(all_entities)

        # Apply confidence thresholds
        filtered = self._filter_by_confidence(deduplicated)

        # Apply domain validation rules
        validated = self._apply_domain_rules(filtered, full_text)

        # Normalize entities
        normalized = self._normalize_entities(validated)

        # Deduplicate AGAIN after normalization (to catch canonicalized duplicates like SPN-1234-FMI-5 → SPN 1234 FMI 5)
        final_deduplicated = self._deduplicate_normalized(normalized)

        # Count by source
        source_mix = self._count_by_source(final_deduplicated)

        return {
            'entities': final_deduplicated,
            'source_mix': source_mix
        }

    def _deduplicate_normalized(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate after normalization to remove canonicalized duplicates.

        Example: "SPN-1234-FMI-5" and "SPN1234/FMI5" both normalize to "SPN 1234 FMI 5"
        so only keep the first occurrence.
        """
        if not entities:
            return []

        seen_texts = set()
        deduplicated = []

        for entity in entities:
            # Check for exact text duplicate (case-insensitive, after normalization)
            text_key = (entity.text.lower(), entity.type)
            if text_key in seen_texts:
                continue

            deduplicated.append(entity)
            seen_texts.add(text_key)

        return deduplicated

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """
        Remove duplicate and overlapping entities using score-based resolution.

        KEEP: Sorts by confidence/length first (CRITICAL FIX from baseline)
        NEW: Uses configurable scoring to resolve overlaps intelligently
        """
        if not entities:
            return []

        # Calculate scores for all entities
        for entity in entities:
            entity.overlap_score = extraction_config.calculate_overlap_score(entity)

        # Sort by score (higher first) - this prioritizes:
        # 1. High adjusted confidence
        # 2. Longer spans (compounds like "power supply" over "power")
        # 3. Higher-priority types (fault_code > model > equipment > etc.)
        sorted_entities = sorted(
            entities,
            key=lambda e: -e.overlap_score
        )

        deduplicated = []
        seen_texts = set()
        covered_spans = []
        overlap_losers = []

        for entity in sorted_entities:
            # Check for exact text duplicate (case-insensitive)
            text_key = (entity.text.lower(), entity.type)
            if text_key in seen_texts:
                self._track_reason('entity_drop', 'duplicate_text')
                continue

            # Check for span overlap
            if entity.span:
                has_overlap = False
                overlap_winner = None

                for i, (start, end, winner_entity) in enumerate(covered_spans):
                    if entity.span[0] < end and start < entity.span[1]:
                        # Overlapping found
                        has_overlap = True
                        overlap_winner = winner_entity
                        break

                if has_overlap:
                    # Track loser for metrics
                    self.metrics['overlaps_resolved'] += 1
                    self._track_reason('entity_drop', 'overlap_loser')

                    if extraction_config.debug_mode:
                        print(f"[OVERLAP] Dropped '{entity.text}' (score={entity.overlap_score:.3f}) "
                              f"in favor of '{overlap_winner}' (better score)")

                    continue

                # Add to covered spans with entity reference
                covered_spans.append((entity.span[0], entity.span[1], entity.text))

            deduplicated.append(entity)
            seen_texts.add(text_key)
            self._track_reason('entity_kept', 'passed_dedup')

        return deduplicated

    def _track_reason(self, category: str, reason: str):
        """Track reason code for metrics"""
        if not extraction_config.enable_reason_codes:
            return

        if category not in self.metrics['reason_codes']:
            self.metrics['reason_codes'][category] = {}

        if reason not in self.metrics['reason_codes'][category]:
            self.metrics['reason_codes'][category][reason] = 0

        self.metrics['reason_codes'][category][reason] += 1

    def _filter_by_confidence(self, entities: List[Entity]) -> List[Entity]:
        """
        Filter entities below confidence thresholds with source-based adjustments.
        Uses centralized config for thresholds and multipliers.
        Emits reason codes for all decisions.
        """
        filtered = []

        for entity in entities:
            # Apply source multiplier to confidence
            source_multiplier = extraction_config.get_source_multiplier(entity.source)
            adjusted_confidence = entity.confidence * source_multiplier

            # Get threshold for this entity type and source
            threshold = extraction_config.get_threshold(entity.type, entity.source)

            # Store adjusted confidence for downstream use
            entity.adjusted_confidence = adjusted_confidence

            # Filter based on adjusted confidence
            if adjusted_confidence >= threshold:
                filtered.append(entity)
                self.metrics['entities_kept'] += 1
                self._track_reason('entity_kept', f'confidence_pass_{entity.type}')

                if extraction_config.debug_mode:
                    print(f"[FILTER] KEPT {entity.type} '{entity.text}': "
                          f"adjusted_conf={adjusted_confidence:.3f} >= threshold={threshold:.3f} "
                          f"(source={entity.source}, multiplier={source_multiplier})")
            else:
                self.metrics['entities_filtered'] += 1
                self._track_reason('entity_drop', f'confidence_fail_{entity.type}')

                if extraction_config.debug_mode:
                    print(f"[FILTER] DROPPED {entity.type} '{entity.text}': "
                          f"adjusted_conf={adjusted_confidence:.3f} < threshold={threshold:.3f} "
                          f"(source={entity.source}, multiplier={source_multiplier})")

        return filtered

    def _apply_domain_rules(self, entities: List[Entity], full_text: str) -> List[Entity]:
        """Apply maritime domain-specific validation rules."""
        validated = []

        # CANONICAL TERM BLACKLIST: Patterns with inappropriate canonicalization
        # These canonical terms group semantically distinct words under one label (canonicalization misuse)
        # See /tmp/UNIVERSAL_PRINCIPLES_DISCOVERED.md for architectural analysis
        CANONICAL_BLACKLIST = {
            '`power_output_reading`',  # 314x FP, 0% Gospel support - groups "power", "wattage", "kw" inappropriately
            'power_output_reading',    # Also check without backticks
            'POWER_OUTPUT_READING'     # And uppercase version
        }

        # Question syntax keywords that should not be extracted as entities
        question_keywords = ['number', 'name', 'date', 'time', 'location', 'person', 'reason', 'way', 'method']

        # Equipment terms that should never be classified as ORG
        equipment_terms = {
            'automatic', 'float', 'switch', 'reverse', 'osmosis', 'membrane',
            'hydraulic', 'electric', 'manual', 'system', 'monitoring', 'control'
        }

        # STOPWORD FILTER: Entities ending with common words that indicate over-capture
        # Fixes regex patterns like "GPS and" from greedy matching
        # KEEP THIS - prevents obvious garbage
        GARBAGE_SUFFIXES = {
            'and', 'or', 'of', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
            'with', 'from', 'by', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall',
            'if', 'then', 'else', 'when', 'where', 'why', 'how', 'what', 'which'
        }

        # NOTE: GENERIC_TERM_BLACKLIST removed - it killed recall (-6.4%)
        # Gospel WANTS terms like "cable", "voltage", "current" in many contexts
        # (e.g., "power cable", "voltage regulator", "current sensor")
        # Universal blocking was too aggressive - trust confidence filtering instead

        for entity in entities:
            # ARCHITECTURAL FIX: Filter blacklisted canonical terms
            # Check if entity has a canonical term that's blacklisted
            entity_canonical = getattr(entity, 'canonical', None)
            if entity_canonical and entity_canonical in CANONICAL_BLACKLIST:
                # Skip this entity - it's from a pattern with inappropriate canonicalization
                self._track_reason('entity_drop', 'canonical_blacklist')
                continue

            # Also check text field in case it's the canonical term
            if entity.text in CANONICAL_BLACKLIST:
                self._track_reason('entity_drop', 'canonical_blacklist')
                continue

            # STOPWORD FILTER: Reject entities ending with common words
            # This catches garbage from greedy regex patterns like "GPS and"
            entity_words = entity.text.lower().split()
            if entity_words and entity_words[-1] in GARBAGE_SUFFIXES:
                # Entity ends with stopword - likely over-captured
                self._track_reason('entity_drop', 'garbage_suffix')
                continue

            # CRITICAL RULE 0: Text Grounding - entity MUST exist in source text
            # This prevents hallucinated entities from AI from passing through
            if entity.source == 'ai':
                # For AI-extracted entities, verify they exist in source
                entity_text_lower = entity.text.lower()
                full_text_lower = full_text.lower()

                # Check if entity text appears in source (case-insensitive)
                if entity_text_lower not in full_text_lower:
                    # Entity is hallucinated - not in source text
                    # Check for common abbreviations/expansions using centralized config
                    is_valid_expansion = False

                    if entity.type == 'org':
                        # Use centralized brand expansions from extraction_config
                        # (avoids duplicate logic that drifts between JS and Python)
                        brand_expansions = extraction_config.brand_expansions if hasattr(extraction_config, 'brand_expansions') else {}
                        for brand_full, abbreviations in brand_expansions.items():
                            if entity_text_lower == brand_full:
                                # Check if any abbreviation appears in source
                                if any(abbr in full_text_lower for abbr in abbreviations):
                                    is_valid_expansion = True
                                    break

                    if not is_valid_expansion:
                        # Skip hallucinated entity
                        self._track_reason('entity_drop', 'ai_hallucination_not_in_text')
                        continue

            # RULE 1: Equipment terms misclassified as ORG
            if entity.type == 'org':
                entity_words = set(entity.text.lower().split())
                if entity_words & equipment_terms:
                    # This is equipment, not an organization
                    continue

            # RULE 2: Part number misclassification - move to equipment
            if entity.type == 'part_number' or entity.type == 'identifier':
                entity_lower = entity.text.lower()

                # Common equipment terms wrongly classified as part numbers
                equipment_keywords = [
                    'filter', 'pump', 'compressor', 'generator', 'engine',
                    'valve', 'sensor', 'switch', 'battery', 'charger',
                    'fuel', 'oil', 'coolant', 'belt', 'hose'
                ]

                # If it's a simple equipment term (not a code), skip it
                # Real part numbers have format: ABC-1234, 123-456-78, P/N12345
                is_equipment_term = any(kw in entity_lower for kw in equipment_keywords)
                has_part_format = bool(re.match(r'^[A-Z0-9]{2,}-\d|^\d{2,}-\d|^P/?N', entity.text, re.I))

                if is_equipment_term and not has_part_format:
                    # Skip - this is equipment misclassified as part number
                    continue

                # Filter nonsensical extractions like "pump not", "pressure specifications"
                if ' not' in entity_lower or ' spec' in entity_lower:
                    continue
            # Rule 0: Filter question syntax (e.g., "What is the PO number" → skip "PO number")
            if entity.span and full_text:
                text_before = full_text[:entity.span[0]].lower()
                # Check if entity follows question pattern
                if any(text_before.endswith(pattern) for pattern in ['what is ', 'what are ', 'where is ', 'when is ', 'who is ', 'which is ', 'how is ']):
                    # Check if entity text contains question keywords
                    entity_lower = entity.text.lower()
                    if any(keyword in entity_lower for keyword in question_keywords):
                        continue  # Skip - this is request syntax, not an entity

            # Rule 1: Battery context check for RPM
            if entity.type == 'measurement' and 'RPM' in entity.text:
                # Check if "battery" appears near this measurement
                if entity.span:
                    context_start = max(0, entity.span[0] - 50)
                    context_end = min(len(full_text), entity.span[1] + 50)
                    context = full_text[context_start:context_end].lower()

                    if 'battery' in context or 'batteries' in context:
                        # Skip RPM measurement in battery context
                        continue

            # Rule 2: Validate measurement ranges
            if entity.type == 'measurement':
                if not self._is_valid_measurement(entity.text):
                    continue

            # Rule 3: Validate fault codes
            if entity.type == 'fault_code':
                # Must have letters (case-insensitive)
                if not re.search(r'[A-Za-z]', entity.text):
                    continue

                # Must have numbers UNLESS it has typical fault code structure:
                # - Multiple uppercase words (e.g., "SHUTDOWN ALARM")
                # - Hyphen/underscore separated terms (e.g., "OVERLOAD-PROTECTION")
                # - Contains common fault indicators (ERR, WARN, FAIL, ALARM, FAULT, TRIP, PROTECT, etc.)
                has_digits = bool(re.search(r'\d', entity.text))
                if not has_digits:
                    # Allow if it has fault code structure patterns
                    has_fault_structure = (
                        bool(re.search(r'[A-Z]{2,}[-_\s][A-Z]{2,}', entity.text)) or  # Multi-word uppercase (BMS OV, CELL UV)
                        bool(re.search(r'\b(ERR|WARN|FAIL|ALARM|FAULT|TRIP|PROTECT|SHUTDOWN|OVERLOAD|OVER|UNDER|HIGH|LOW)\b', entity.text, re.I))  # Common fault indicators
                    )
                    if not has_fault_structure:
                        continue

            # Rule 5: Equipment proximity to symptoms
            if entity.type == 'symptom':
                # Symptoms should be near equipment mentions
                has_nearby_equipment = False
                if entity.span:
                    for other in entities:
                        if other.type == 'equipment' and other.span:
                            distance = abs(other.span[0] - entity.span[0])
                            if distance < 100:  # Within ~100 chars
                                has_nearby_equipment = True
                                break

                    if not has_nearby_equipment and entity.confidence < 0.9:
                        # Lower confidence symptoms need equipment context
                        continue

            validated.append(entity)

        return validated

    def _is_valid_measurement(self, text: str) -> bool:
        """Validate measurement values are within reasonable ranges."""
        # Extract number and unit
        match = re.match(r'([\d.,]+)\s*(.+)', text)
        if not match:
            return True  # Can't validate, assume OK

        try:
            # Handle EU format numbers
            value_str = match.group(1).replace(',', '.')
            value = float(value_str)
            unit = match.group(2).lower()

            # Check reasonable ranges
            if '°c' in unit or 'celsius' in unit:
                return -50 <= value <= 200  # Reasonable temperature range
            elif '°f' in unit or 'fahrenheit' in unit:
                return -50 <= value <= 400
            elif 'v' in unit and not 'kv' in unit:
                return 0 <= value <= 1000  # Voltage up to 1000V
            elif 'kv' in unit:
                return 0 <= value <= 50  # Up to 50kV
            elif 'bar' in unit:
                return 0 <= value <= 500  # Pressure up to 500 bar
            elif 'rpm' in unit:
                return 0 <= value <= 10000  # RPM up to 10000
            elif 'hz' in unit and not 'khz' in unit and not 'mhz' in unit:
                return 0 <= value <= 1000  # Frequency up to 1000 Hz

        except ValueError:
            pass  # Can't parse, assume OK

        return True

    def _normalize_entities(self, entities: List[Entity]) -> List[Entity]:
        """Normalize entity text for consistency."""
        normalized = []

        for entity in entities:
            text = entity.text

            # Normalize by type
            if entity.type in ['equipment', 'system', 'org', 'model']:
                # Capitalize proper nouns
                text = self._capitalize_terms(text)

            elif entity.type == 'measurement':
                # Ensure proper spacing between value and unit
                text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
                # Standardize degree symbol
                text = text.replace('°c', '°C').replace('°f', '°F')

            elif entity.type in ['fault_code', 'document_id', 'identifier', 'network_id']:
                # Canonicalize fault codes to standard format (SPN 1234 FMI 5)
                text = self._canonicalize_fault_code(text) if entity.type == 'fault_code' else text

            elif entity.type in ['status', 'symptom', 'action']:
                # Lowercase for consistency
                text = text.lower()

            elif entity.type == 'location_on_board':
                # Capitalize location terms
                text = self._capitalize_terms(text)

            # Create normalized entity (preserve new attributes)
            normalized.append(Entity(
                text=text,
                entity_type=entity.type,
                confidence=entity.confidence,
                source=entity.source,
                span=entity.span,
                negated=getattr(entity, 'negated', False),
                qualifier=getattr(entity, 'qualifier', None),
                tolerance=getattr(entity, 'tolerance', None),
                approx=getattr(entity, 'approx', False)
            ))

        return normalized

    def _capitalize_terms(self, text: str) -> str:
        """Properly capitalize multi-word terms."""
        # List of words that should stay lowercase
        lowercase_words = {'of', 'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for'}

        words = text.split()
        capitalized = []

        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                # Capitalize first word and important words
                capitalized.append(word.capitalize())
            else:
                capitalized.append(word.lower())

        return ' '.join(capitalized)

    def _canonicalize_fault_code(self, text: str) -> str:
        """
        Normalize fault code format to canonical representation.

        This ensures all variations of the same fault code are stored in a single
        standardized format, enabling proper deduplication and RAG retrieval.

        Examples:
          - "SPN-1234-FMI-5" → "SPN 1234 FMI 5"
          - "SPN1234/FMI5" → "SPN 1234 FMI 5"
          - "spn 1234 fmi 5" → "SPN 1234 FMI 5"
          - "MID128 PSID230 FMI9" → "MID 128 PSID 230 FMI 9"

        Args:
            text: Raw fault code text from extraction

        Returns:
            Canonicalized fault code with standardized spacing and uppercase
        """
        # 1. Uppercase everything
        text = text.upper()

        # 2. Normalize all separators (dash, underscore, slash, colon) to space
        text = re.sub(r'[-_/:]', ' ', text)

        # 3. Add space between letters and numbers (SPN1234 → SPN 1234)
        text = re.sub(r'([A-Z]+)(\d+)', r'\1 \2', text)

        # 4. Add space between numbers and letters (1234FMI → 1234 FMI)
        text = re.sub(r'(\d+)([A-Z]+)', r'\1 \2', text)

        # 5. Collapse multiple spaces to single space
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _count_by_source(self, entities: List[Entity]) -> Dict[str, int]:
        """Count entities by extraction source."""
        counts = {'regex': 0, 'gazetteer': 0, 'ai': 0}

        for entity in entities:
            if entity.source in counts:
                counts[entity.source] += 1

        return counts

    def group_by_type(self, entities: List[Entity]) -> Dict[str, List[str]]:
        """
        Group entities by type, returning string arrays only per v0.2.2 schema.
        For negated actions, preserve the negation phrase (e.g., "do not start").
        Applies smart deduplication to remove substrings when compound terms exist.
        """
        grouped = {}

        # First pass: collect all entities by type
        for entity in entities:
            if entity.type not in grouped:
                grouped[entity.type] = []

            # For negated actions/status, prepend "do not" or similar
            text = entity.text
            if getattr(entity, 'negated', False) and entity.type in ['action', 'status']:
                # Check if negation phrase is already part of the text
                if not any(neg in text.lower() for neg in ['do not', "don't", 'avoid', 'no', 'never']):
                    # Add "do not" prefix for negated actions
                    if entity.type == 'action':
                        text = f"do not {text}"
                    elif entity.type == 'status':
                        text = f"no {text}"

            grouped[entity.type].append(text)

        # Second pass: smart deduplication
        deduped = {}
        for entity_type, terms in grouped.items():
            deduped[entity_type] = self._smart_deduplicate(terms)

        return deduped

    def _smart_deduplicate(self, terms: List[str]) -> List[str]:
        """
        Smart deduplication that:
        - Removes substrings when compound terms exist
        - Handles case-insensitive comparison
        - Prefers compound terms over individual words
        """
        if not terms:
            return []

        # Normalize and sort by length (longest first - compounds before singles)
        normalized_terms = []
        for term in terms:
            normalized = term.strip()
            if normalized:
                normalized_terms.append((normalized.lower(), normalized))

        # Remove exact duplicates first
        unique_map = {}
        for norm, orig in normalized_terms:
            if norm not in unique_map:
                unique_map[norm] = orig
            # Keep the version with better capitalization
            elif orig[0].isupper() and unique_map[norm][0].islower():
                unique_map[norm] = orig

        # Sort by length (longest first) to prioritize compounds
        sorted_terms = sorted(unique_map.items(), key=lambda x: len(x[0]), reverse=True)

        # Remove substrings
        final_terms = []
        final_terms_lower = []

        for norm_term, orig_term in sorted_terms:
            # Check if this term is a substring of any already accepted term
            is_substring = False
            for accepted_lower in final_terms_lower:
                if norm_term in accepted_lower and norm_term != accepted_lower:
                    # Special case: single word that's part of compound
                    # e.g., "battery" is substring of "battery bank"
                    is_substring = True
                    break

            if not is_substring:
                # Also check if any accepted term is a substring of this one
                # Remove shorter terms that are substrings
                to_remove = []
                for i, accepted_lower in enumerate(final_terms_lower):
                    if accepted_lower in norm_term and accepted_lower != norm_term:
                        to_remove.append(i)

                # Remove in reverse order to maintain indices
                for i in reversed(to_remove):
                    del final_terms[i]
                    del final_terms_lower[i]

                final_terms.append(orig_term)
                final_terms_lower.append(norm_term)

        # Sort for consistency
        final_terms.sort(key=lambda x: x.lower())

        return final_terms