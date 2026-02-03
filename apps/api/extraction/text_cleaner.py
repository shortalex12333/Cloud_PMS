#!/usr/bin/env python3
"""
Stage 0: Text Cleaning and Tokenization
Normalizes text, handles Unicode, tokenizes for coverage calculation
"""

import unicodedata
import re
from typing import Dict, List, Set, Tuple


class TextCleaner:
    """Cleans and tokenizes maritime text for entity extraction."""

    # Common stopwords to ignore in coverage calculation
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'it', 'its', 'this', 'that', 'these', 'those', 'there', 'their'
    }

    def clean(self, text: str) -> Dict:
        """
        Clean and normalize text for extraction.

        Returns:
            {
                'original': str,          # Original input
                'normalized': str,        # Cleaned text
                'tokens': List[str],      # Meaningful tokens (for coverage)
                'token_spans': List[Tuple[int, int]]  # Token positions
            }
        """
        if not text:
            return {
                'original': '',
                'normalized': '',
                'tokens': [],
                'token_spans': []
            }

        # Store original
        original = text

        # Unicode normalization (NFKC)
        normalized = unicodedata.normalize('NFKC', text)

        # Normalize degree symbols and special chars
        normalized = self._normalize_special_chars(normalized)

        # Split CamelCase words (Fix 2026-02-02: "activewarnings" → "active warnings")
        # This helps extract entities from concatenated words
        normalized = self._split_camelcase(normalized)

        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # Tokenize for coverage calculation
        tokens, token_spans = self._tokenize_for_coverage(normalized)

        return {
            'original': original,
            'normalized': normalized,
            'tokens': tokens,
            'token_spans': token_spans
        }

    def _normalize_special_chars(self, text: str) -> str:
        """Normalize special characters and symbols - Enhanced Sanitization v2."""
        # ===== ENHANCED SANITIZATION V2 =====

        # Unicode symbol normalization
        text = text.replace('µ', 'u')  # micro → u (µA → uA, µF → uF)
        text = text.replace('Ω', 'Ohm')  # Omega → Ohm
        text = text.replace('Ω', 'Ohm')  # Alternative Omega
        text = text.replace('×', 'x')  # Multiplication sign
        text = text.replace('÷', '/')  # Division sign
        text = text.replace('±', '+/-')  # Plus-minus
        text = text.replace('≈', '~')  # Approximately
        text = text.replace('≤', '<=')  # Less than or equal
        text = text.replace('≥', '>=')  # Greater than or equal

        # Degree symbols
        text = re.sub(r'[°℃℉]', '°', text)
        text = re.sub(r'(\d)\s*°\s*C\b', r'\1°C', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d)\s*°\s*F\b', r'\1°F', text, flags=re.IGNORECASE)

        # Voltage patterns - normalize spacing
        text = re.sub(r'(\d+)\s*VDC\b', r'\1 VDC', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)\s*VAC\b', r'\1 VAC', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)\s*VCC\b', r'\1 VCC', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)\s*V\s+DC\b', r'\1 VDC', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)\s*V\s+AC\b', r'\1 VAC', text, flags=re.IGNORECASE)

        # Current patterns - normalize spacing
        text = re.sub(r'(\d+)\s*mA\b', r'\1 mA', text)
        text = re.sub(r'(\d+)\s*A\b', r'\1 A', text)
        text = re.sub(r'(\d+)\s*Amp(?:s|ere|eres)?\b', r'\1 A', text, flags=re.IGNORECASE)

        # Power patterns - normalize units
        text = re.sub(r'(\d+)\s*kVA\b', r'\1 kVA', text)
        text = re.sub(r'(\d+)\s*kW\b', r'\1 kW', text)
        text = re.sub(r'(\d+)\s*HP\b', r'\1 HP', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)\s*BHP\b', r'\1 BHP', text, flags=re.IGNORECASE)

        # Frequency patterns - normalize
        text = re.sub(r'(\d+)\s*Hz\b', r'\1 Hz', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+)\s*kHz\b', r'\1 kHz', text, flags=re.IGNORECASE)

        # Remove stray private-use glyphs (PUA range)
        text = re.sub(r'[\uE000-\uF8FF]', '', text)

        # Standardize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"[''']", "'", text)

        # Normalize dashes
        text = re.sub(r'[–—]', '-', text)

        # Normalize number formats
        text = re.sub(r'(\d+)\s*-\s*(\d+)\s*([VvAa])', r'\1-\2 \3', text)  # 230-240V → 230-240 V
        text = re.sub(r'(\d+)/(\d+)\s*([VvAa])', r'\1/\2 \3', text)  # 230/400V → 230/400 V

        return text

    def _tokenize_for_coverage(self, text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """
        Tokenize text for coverage calculation.
        Returns meaningful tokens (excluding stopwords and punctuation).
        """
        tokens = []
        spans = []

        # Pattern for meaningful tokens (words, numbers, codes)
        token_pattern = re.compile(r'\b[\w\-\.]+\b')

        for match in token_pattern.finditer(text):
            token = match.group().lower()
            span = (match.start(), match.end())

            # Skip if stopword or single punctuation
            if token in self.STOPWORDS:
                continue
            if len(token) == 1 and not token.isalnum():
                continue

            tokens.append(token)
            spans.append(span)

        return tokens, spans

    def compute_coverage(self, normalized_text: str, extracted_spans: List[Tuple[int, int]],
                        tokens: List[str]) -> float:
        """
        Compute extraction coverage ratio.
        Coverage = (tokens covered by extraction) / (total meaningful tokens)
        """
        if not tokens:
            return 1.0  # Empty text is fully covered

        # Create coverage mask
        text_len = len(normalized_text)
        covered = [False] * text_len

        # Mark extracted spans as covered
        for start, end in extracted_spans:
            for i in range(max(0, start), min(text_len, end)):
                covered[i] = True

        # Count covered tokens
        covered_tokens = 0
        for token, (start, end) in zip(tokens, self._tokenize_for_coverage(normalized_text)[1]):
            # Check if token is mostly covered (>50%)
            token_covered = sum(covered[start:end]) > (end - start) / 2
            if token_covered:
                covered_tokens += 1

        return covered_tokens / len(tokens) if tokens else 1.0

    def find_uncovered_spans(self, text: str, extracted_spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Find text spans not covered by extraction.
        Returns list of (start, end) tuples for uncovered regions.
        """
        if not text:
            return []

        text_len = len(text)
        covered = [False] * text_len

        # Mark extracted spans
        for start, end in extracted_spans:
            for i in range(max(0, start), min(text_len, end)):
                covered[i] = True

        # Find uncovered spans
        uncovered_spans = []
        span_start = None

        for i, is_covered in enumerate(covered):
            if not is_covered and span_start is None:
                span_start = i
            elif is_covered and span_start is not None:
                # Skip tiny gaps (< 3 chars)
                if i - span_start >= 3:
                    uncovered_spans.append((span_start, i))
                span_start = None

        # Handle trailing uncovered
        if span_start is not None and text_len - span_start >= 3:
            uncovered_spans.append((span_start, text_len))

        # Merge adjacent spans with small gaps
        merged = []
        for start, end in uncovered_spans:
            if merged and start - merged[-1][1] <= 5:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))

        return merged

    def _split_camelcase(self, text: str) -> str:
        """
        Split CamelCase and concatenated words for better entity extraction.

        Examples:
            'activewarnings' → 'active warnings'
            'CriticalWarnings' → 'Critical Warnings'
            'lowStock' → 'low Stock'
            'RESTCompliance' → 'REST Compliance'

        This helps extract entities from concatenated user input.
        """
        # Known brand names that should NOT be split (preserve weird casing)
        # Handle "RaCoR", "CaTerPillar", "YaNMar" etc.
        known_brands_lower = {
            'racor', 'caterpillar', 'cat', 'yanmar', 'volvo', 'cummins', 'mtu',
            'man', 'kohler', 'onan', 'perkins', 'deutz', 'kubota', 'honda',
            'suzuki', 'yamaha', 'mercury', 'furuno', 'garmin', 'raymarine',
            'simrad', 'lowrance', 'flir', 'lewmar', 'maxwell', 'vetus',
            'webasto', 'dometic', 'grundfos', 'jabsco', 'groco', 'parker',
            'bosch', 'danfoss', 'siemens', 'abb', 'westinghouse', 'alfa',
        }

        # Split text into words and process each
        words = text.split()
        processed_words = []

        for word in words:
            # If word (lowercased) is a known brand, don't split it
            if word.lower() in known_brands_lower:
                processed_words.append(word.lower())  # Normalize to lowercase
                continue

            # Pattern 1: Insert space before uppercase letters that follow lowercase
            # 'activeWarnings' → 'active Warnings'
            word = re.sub(r'([a-z])([A-Z])', r'\1 \2', word)

            # Pattern 2: Insert space between consecutive uppercase and following lowercase
            # 'RESTCompliance' → 'REST Compliance'
            word = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', word)

            processed_words.append(word)

        text = ' '.join(processed_words)

        # Pattern 3: Handle all-lowercase concatenated words (common typos)
        # 'activewarnings' → 'active warnings'
        # Use a dictionary of known word boundaries
        known_splits = {
            'activewarnings': 'active warnings',
            'criticalwarnings': 'critical warnings',
            'activewarning': 'active warning',
            'criticalwarning': 'critical warning',
            'lowstock': 'low stock',
            'outofstock': 'out of stock',
            'instock': 'in stock',
            'restcompliance': 'rest compliance',
            'hourcompliance': 'hour compliance',
            'restviolation': 'rest violation',
            'restviolations': 'rest violations',
            'engineroom': 'engine room',
            'mainengine': 'main engine',
            'bowthruster': 'bow thruster',
            'sternthruster': 'stern thruster',
            'fuelfilter': 'fuel filter',
            'oilfilter': 'oil filter',
            'airfilter': 'air filter',
            'shoppinglist': 'shopping list',
            'buylist': 'buy list',
            'workorder': 'work order',
            'workorders': 'work orders',
            'partslist': 'parts list',
            'spareslist': 'spares list',
        }

        # Apply known splits (case-insensitive)
        text_lower = text.lower()
        for concat, split in known_splits.items():
            if concat in text_lower:
                # Preserve original case for first character
                pattern = re.compile(re.escape(concat), re.IGNORECASE)
                text = pattern.sub(split, text)

        return text