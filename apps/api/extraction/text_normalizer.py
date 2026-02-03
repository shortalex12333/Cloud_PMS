#!/usr/bin/env python3
"""
Text Normalization Engine for Entity Extraction
================================================

PURPOSE: Automatically normalize text variations without manual aliases.

NORMALIZATIONS:
1. Lemmatization: gaskets → gasket, filters → filter, running → run
2. Abbreviation expansion: gen → generator, ME → main engine, A/C → air conditioning
3. Compound normalization: water maker → watermaker, air con → aircon
4. Case normalization: MTU → mtu, VoLvO → volvo

This replaces manual alias dictionaries with algorithmic normalization.
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from functools import lru_cache

# Try to import inflect for pluralization handling
try:
    import inflect
    INFLECT_ENGINE = inflect.engine()
    INFLECT_AVAILABLE = True
except ImportError:
    INFLECT_ENGINE = None
    INFLECT_AVAILABLE = False
    print("⚠️  inflect not available - using rule-based singularization")


# =============================================================================
# ABBREVIATION RULES - Programmatic, not exhaustive lists
# =============================================================================
# These are RULES, not exhaustive mappings. The engine applies them dynamically.

ABBREVIATION_RULES = {
    # Equipment abbreviations (pattern-based)
    'gen': 'generator',
    'genset': 'generator',
    'genny': 'generator',
    'me': 'main engine',
    'aux': 'auxiliary',
    'a/c': 'air conditioning',
    'ac': 'air conditioning',
    'aircon': 'air conditioning',
    'hvac': 'heating ventilation air conditioning',
    'fwd': 'forward',
    'aft': 'aft',  # Already correct, but explicit
    'stbd': 'starboard',
    'pt': 'port',
    'hyd': 'hydraulic',
    'elec': 'electrical',
    'mech': 'mechanical',
    'nav': 'navigation',
    'comms': 'communications',
    'eng': 'engine',
    'equip': 'equipment',
    'maint': 'maintenance',
    'cert': 'certificate',
    'doc': 'document',
    'spec': 'specification',
    'tech': 'technical',
    'qty': 'quantity',
    'amt': 'amount',
    'approx': 'approximately',
    'req': 'required',
    'recv': 'received',
    'dlvr': 'delivered',
    'wo': 'work order',
    'po': 'purchase order',
    'pm': 'preventive maintenance',
    'cm': 'corrective maintenance',
}

# Numbered equipment patterns: "gen 1" → "generator 1"
NUMBERED_EQUIPMENT_PATTERN = re.compile(
    r'\b(gen|eng|aux|pump|tank|chiller|compressor)\s*(\d+)\b',
    re.IGNORECASE
)

# Compound words that should be joined
COMPOUND_JOINS = {
    'water maker': 'watermaker',
    'water-maker': 'watermaker',
    'sea water': 'seawater',
    'sea-water': 'seawater',
    'air conditioning': 'air_conditioning',
    'air-conditioning': 'air_conditioning',
    'bow thruster': 'bow_thruster',
    'stern thruster': 'stern_thruster',
    'main engine': 'main_engine',
    'fire extinguisher': 'fire_extinguisher',
    'life raft': 'life_raft',
    'life jacket': 'life_jacket',
    'engine room': 'engine_room',
    'chart plotter': 'chartplotter',
    'chart-plotter': 'chartplotter',
}

# Equipment synonyms (semantic equivalence)
EQUIPMENT_SYNONYMS = {
    'desalinator': 'watermaker',
    'ro unit': 'watermaker',
    'reverse osmosis': 'watermaker',
    'genset': 'generator',
    'diesel generator': 'generator',
    'dg': 'generator',
    'thruster': 'thruster',  # Keep as-is, context determines bow/stern
    'aircon': 'air_conditioning',
    'a/c': 'air_conditioning',
    'ac unit': 'air_conditioning',
    'fridge': 'refrigerator',
    'freezer': 'freezer',
    'ice box': 'refrigerator',
}


class TextNormalizer:
    """
    Normalizes text for better entity matching without manual aliases.
    """

    def __init__(self):
        self.inflect = INFLECT_ENGINE
        self._build_abbreviation_pattern()

    def _build_abbreviation_pattern(self):
        """Build regex pattern for abbreviation matching."""
        # Sort by length (longest first) to match longer abbreviations first
        abbrevs = sorted(ABBREVIATION_RULES.keys(), key=len, reverse=True)
        # Escape special chars and join with |
        escaped = [re.escape(a) for a in abbrevs]
        self.abbrev_pattern = re.compile(
            r'\b(' + '|'.join(escaped) + r')\b',
            re.IGNORECASE
        )

    @lru_cache(maxsize=10000)
    def singularize(self, word: str) -> str:
        """
        Convert plural to singular form.

        Uses inflect library if available, otherwise rule-based fallback.

        Examples:
            gaskets → gasket
            filters → filter
            pumps → pump
            batteries → battery
            indices → index
        """
        word_lower = word.lower()

        # Skip if already looks singular or is very short
        if len(word_lower) < 3:
            return word_lower

        # Use inflect if available
        if self.inflect:
            singular = self.inflect.singular_noun(word_lower)
            if singular:
                return singular
            return word_lower  # Already singular

        # Rule-based fallback
        return self._rule_based_singularize(word_lower)

    def _rule_based_singularize(self, word: str) -> str:
        """Rule-based singularization fallback."""
        # Common irregular plurals
        irregulars = {
            'indices': 'index',
            'vertices': 'vertex',
            'matrices': 'matrix',
            'analyses': 'analysis',
            'crises': 'crisis',
            'theses': 'thesis',
            'phenomena': 'phenomenon',
            'criteria': 'criterion',
            'data': 'datum',
            'media': 'medium',
        }
        if word in irregulars:
            return irregulars[word]

        # -ies → -y (batteries → battery)
        if word.endswith('ies') and len(word) > 4:
            return word[:-3] + 'y'

        # -es → (after s, x, z, ch, sh)
        if word.endswith('es') and len(word) > 3:
            if word.endswith(('sses', 'xes', 'zes', 'ches', 'shes')):
                return word[:-2]

        # -s → (standard plural)
        if word.endswith('s') and not word.endswith('ss') and len(word) > 2:
            return word[:-1]

        return word

    @lru_cache(maxsize=10000)
    def expand_abbreviation(self, text: str) -> str:
        """
        Expand common abbreviations to full forms.

        Examples:
            gen 1 → generator 1
            ME port → main engine port
            A/C unit → air conditioning unit
            fwd thruster → forward thruster
        """
        result = text.lower()

        # Handle numbered equipment first: "gen 1" → "generator 1"
        def expand_numbered(match):
            abbrev = match.group(1).lower()
            number = match.group(2)
            expanded = ABBREVIATION_RULES.get(abbrev, abbrev)
            return f"{expanded} {number}"

        result = NUMBERED_EQUIPMENT_PATTERN.sub(expand_numbered, result)

        # Expand remaining abbreviations
        def expand_match(match):
            abbrev = match.group(1).lower()
            return ABBREVIATION_RULES.get(abbrev, abbrev)

        result = self.abbrev_pattern.sub(expand_match, result)

        return result

    @lru_cache(maxsize=10000)
    def normalize_compounds(self, text: str) -> str:
        """
        Normalize compound words to canonical forms.

        Examples:
            water maker → watermaker
            main engine → main_engine
            air-conditioning → air_conditioning
        """
        result = text.lower()

        # Apply compound joins
        for compound, normalized in COMPOUND_JOINS.items():
            result = result.replace(compound, normalized)

        return result

    @lru_cache(maxsize=10000)
    def apply_synonyms(self, text: str) -> str:
        """
        Replace equipment synonyms with canonical terms.

        Examples:
            desalinator → watermaker
            genset → generator
        """
        result = text.lower()

        for synonym, canonical in EQUIPMENT_SYNONYMS.items():
            # Use word boundary matching
            pattern = r'\b' + re.escape(synonym) + r'\b'
            result = re.sub(pattern, canonical, result, flags=re.IGNORECASE)

        return result

    def normalize_for_matching(self, text: str) -> str:
        """
        Full normalization pipeline for entity matching.

        Order matters:
        1. Expand abbreviations (gen 1 → generator 1)
        2. Apply synonyms (desalinator → watermaker)
        3. Normalize compounds (water maker → watermaker)
        4. Singularize words (gaskets → gasket)
        """
        # Step 1: Expand abbreviations
        result = self.expand_abbreviation(text)

        # Step 2: Apply synonyms
        result = self.apply_synonyms(result)

        # Step 3: Normalize compounds
        result = self.normalize_compounds(result)

        # Step 4: Singularize each word
        words = result.split()
        singularized = [self.singularize(w) for w in words]
        result = ' '.join(singularized)

        return result

    def normalize_entity_value(self, value: str, entity_type: str) -> str:
        """
        Normalize an extracted entity value for comparison.

        Args:
            value: The extracted entity text
            entity_type: The entity type (brand, equipment, part, etc.)

        Returns:
            Normalized value for matching
        """
        normalized = value.lower().strip()

        # Type-specific normalization
        if entity_type in ('equipment', 'equipment_type', 'part', 'system'):
            normalized = self.normalize_for_matching(normalized)

        elif entity_type in ('brand', 'equipment_brand'):
            # For brands, just normalize case and spacing
            normalized = ' '.join(normalized.split())

        return normalized

    def get_variations(self, term: str) -> Set[str]:
        """
        Generate possible variations of a term for matching.

        Instead of pre-populating all variations, generate them on demand.

        Examples:
            "generator" → {"generator", "generators", "gen", "genset"}
            "filter" → {"filter", "filters"}
        """
        variations = {term.lower()}

        # Add plural form
        if self.inflect:
            plural = self.inflect.plural(term.lower())
            if plural:
                variations.add(plural)

        # Add common abbreviations (reverse lookup)
        for abbrev, expanded in ABBREVIATION_RULES.items():
            if expanded == term.lower():
                variations.add(abbrev)

        # Add synonyms (reverse lookup)
        for synonym, canonical in EQUIPMENT_SYNONYMS.items():
            if canonical == term.lower():
                variations.add(synonym)

        return variations


# Singleton instance
_normalizer = None

def get_normalizer() -> TextNormalizer:
    """Get singleton normalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = TextNormalizer()
    return _normalizer


# Convenience functions
def singularize(word: str) -> str:
    """Singularize a word."""
    return get_normalizer().singularize(word)


def expand_abbreviation(text: str) -> str:
    """Expand abbreviations in text."""
    return get_normalizer().expand_abbreviation(text)


def normalize_for_matching(text: str) -> str:
    """Full normalization for entity matching."""
    return get_normalizer().normalize_for_matching(text)


def get_variations(term: str) -> Set[str]:
    """Get all variations of a term."""
    return get_normalizer().get_variations(term)


# =============================================================================
# TESTING
# =============================================================================
if __name__ == '__main__':
    normalizer = TextNormalizer()

    print("=" * 60)
    print("TEXT NORMALIZER TESTS")
    print("=" * 60)

    # Test singularization
    print("\n1. SINGULARIZATION:")
    test_plurals = ['gaskets', 'filters', 'pumps', 'batteries', 'valves',
                    'seals', 'bearings', 'certificates', 'engines']
    for plural in test_plurals:
        singular = normalizer.singularize(plural)
        print(f"   {plural:15} → {singular}")

    # Test abbreviation expansion
    print("\n2. ABBREVIATION EXPANSION:")
    test_abbrevs = ['gen 1', 'ME port', 'fwd thruster', 'A/C unit',
                    'aux pump 2', 'hyd system', 'elec panel']
    for abbrev in test_abbrevs:
        expanded = normalizer.expand_abbreviation(abbrev)
        print(f"   {abbrev:15} → {expanded}")

    # Test compound normalization
    print("\n3. COMPOUND NORMALIZATION:")
    test_compounds = ['water maker', 'main engine', 'bow thruster',
                      'air conditioning', 'chart plotter']
    for compound in test_compounds:
        normalized = normalizer.normalize_compounds(compound)
        print(f"   {compound:20} → {normalized}")

    # Test synonym replacement
    print("\n4. SYNONYM REPLACEMENT:")
    test_synonyms = ['desalinator membrane', 'genset fuel filter',
                     'aircon compressor', 'ro unit maintenance']
    for text in test_synonyms:
        normalized = normalizer.apply_synonyms(text)
        print(f"   {text:25} → {normalized}")

    # Test full pipeline
    print("\n5. FULL NORMALIZATION PIPELINE:")
    test_queries = [
        'gen 1 running hours',
        'Volvo Penta gaskets',
        'water maker membranes',
        'desalinator filters',
        'fwd thruster hydraulic pumps',
        'ME port oil filters',
    ]
    for query in test_queries:
        normalized = normalizer.normalize_for_matching(query)
        print(f"   {query:30} → {normalized}")

    # Test variation generation
    print("\n6. VARIATION GENERATION:")
    test_terms = ['generator', 'filter', 'watermaker', 'pump']
    for term in test_terms:
        variations = normalizer.get_variations(term)
        print(f"   {term:15} → {variations}")
