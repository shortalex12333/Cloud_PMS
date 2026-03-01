#!/usr/bin/env python3
"""
Email Search Query Parser (M2)

Deterministic, explainable query parsing for hybrid email search.

Responsibilities:
- Tokenize query string into operators and free text
- Build AST representing structured filters + unstructured query
- Sanitize filter values to prevent injection
- Preserve free text for embedding generation and entity extraction

Supported Operators (v1):
- from:<email|name>      Filter by sender
- to:<email|name>        Filter by recipient
- subject:<text>         Filter by subject contains
- has:attachment         Filter messages with attachments
- before:<date>          Filter by date (received_at < date)
- after:<date>           Filter by date (received_at > date)
- in:work_order:<id>     Filter by linked work order
- thread:<id>            Filter by thread ID

Query Examples:
- "watermaker PO-2024 from:supplier@marine.com"
- "subject:invoice after:2024-01-01 has:attachment"
- "engine parts before:2024-03-15"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OperatorType(Enum):
    """Supported search operators."""
    FROM = "from"
    TO = "to"
    SUBJECT = "subject"
    HAS_ATTACHMENT = "has:attachment"
    BEFORE = "before"
    AFTER = "after"
    IN_WORK_ORDER = "in:work_order"
    THREAD = "thread"


@dataclass
class ParsedOperator:
    """A single parsed operator with its value."""
    operator: OperatorType
    value: str
    raw: str  # Original text matched


@dataclass
class ParsedQuery:
    """
    Result of parsing a search query.

    Contains structured filters (operators) and free text for semantic search.
    """
    # Free text for embedding + entity extraction
    free_text: str

    # Structured filters
    from_filter: Optional[str] = None
    to_filter: Optional[str] = None
    subject_filter: Optional[str] = None
    has_attachment: Optional[bool] = None
    date_before: Optional[date] = None
    date_after: Optional[date] = None
    work_order_id: Optional[str] = None
    thread_id: Optional[str] = None

    # Parse metadata
    operators_found: List[ParsedOperator] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)

    def to_rpc_params(self) -> Dict[str, Any]:
        """Convert to params for search_email_hybrid RPC."""
        params = {}

        if self.from_filter:
            params['p_from'] = self.from_filter
        if self.to_filter:
            params['p_to'] = self.to_filter
        if self.subject_filter:
            params['p_subject'] = self.subject_filter
        if self.has_attachment is not None:
            params['p_has_attachment'] = self.has_attachment
        if self.date_before:
            params['p_date_before'] = self.date_before.isoformat()
        if self.date_after:
            params['p_date_after'] = self.date_after.isoformat()
        if self.work_order_id:
            params['p_work_order_id'] = self.work_order_id
        if self.thread_id:
            params['p_thread_id'] = self.thread_id

        return params

    def get_match_reasons(self) -> List[str]:
        """Get human-readable list of filters applied."""
        reasons = []

        if self.from_filter:
            reasons.append(f"from: {self.from_filter}")
        if self.to_filter:
            reasons.append(f"to: {self.to_filter}")
        if self.subject_filter:
            reasons.append(f"subject contains: {self.subject_filter}")
        if self.has_attachment:
            reasons.append("has attachment")
        if self.date_before:
            reasons.append(f"before: {self.date_before}")
        if self.date_after:
            reasons.append(f"after: {self.date_after}")
        if self.work_order_id:
            reasons.append(f"work order: {self.work_order_id}")
        if self.thread_id:
            reasons.append(f"thread: {self.thread_id[:8]}...")

        return reasons


class QueryParser:
    """
    Deterministic query parser for email search.

    Tokenizes input, extracts operators, preserves free text.
    """

    # Regex patterns for operators
    # Order matters - more specific patterns first
    OPERATOR_PATTERNS = [
        # has:attachment (boolean, no value)
        (r'\bhas:attachment\b', OperatorType.HAS_ATTACHMENT, None),

        # in:work_order:<id>
        (r'\bin:work_order:([^\s]+)', OperatorType.IN_WORK_ORDER, 1),

        # from:<value> - supports quoted values
        (r'\bfrom:(?:"([^"]+)"|([^\s]+))', OperatorType.FROM, (1, 2)),

        # to:<value>
        (r'\bto:(?:"([^"]+)"|([^\s]+))', OperatorType.TO, (1, 2)),

        # subject:<value>
        (r'\bsubject:(?:"([^"]+)"|([^\s]+))', OperatorType.SUBJECT, (1, 2)),

        # before:<date>
        (r'\bbefore:([^\s]+)', OperatorType.BEFORE, 1),

        # after:<date>
        (r'\bafter:([^\s]+)', OperatorType.AFTER, 1),

        # thread:<id>
        (r'\bthread:([^\s]+)', OperatorType.THREAD, 1),
    ]

    # Date formats to try
    DATE_FORMATS = [
        '%Y-%m-%d',      # 2024-03-15
        '%Y/%m/%d',      # 2024/03/15
        '%d-%m-%Y',      # 15-03-2024
        '%d/%m/%Y',      # 15/03/2024
        '%Y%m%d',        # 20240315
    ]

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a search query into structured filters and free text.

        Args:
            query: Raw search query string

        Returns:
            ParsedQuery with operators extracted and free text preserved
        """
        if not query or not query.strip():
            return ParsedQuery(free_text="")

        query = query.strip()
        result = ParsedQuery(free_text="")
        remaining = query

        # Extract operators
        for pattern, op_type, value_group in self.OPERATOR_PATTERNS:
            remaining, ops = self._extract_operator(remaining, pattern, op_type, value_group)

            for op in ops:
                result.operators_found.append(op)
                self._apply_operator(result, op)

        # Remaining text is free text for semantic search
        result.free_text = self._clean_free_text(remaining)

        # Enforce max operators to prevent pathological cases
        if len(result.operators_found) > self.MAX_OPERATORS:
            result.parse_warnings.append(
                f"Too many operators ({len(result.operators_found)}), limit is {self.MAX_OPERATORS}"
            )
            # Keep only first MAX_OPERATORS
            result.operators_found = result.operators_found[:self.MAX_OPERATORS]

        logger.debug(f"[parser] Parsed query: operators={len(result.operators_found)}, free_text='{result.free_text[:50]}...'")

        return result

    def _extract_operator(
        self,
        text: str,
        pattern: str,
        op_type: OperatorType,
        value_group: Optional[int | Tuple[int, int]]
    ) -> Tuple[str, List[ParsedOperator]]:
        """Extract all occurrences of an operator from text."""
        operators = []

        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw = match.group(0)

            # Extract value based on group specification
            if value_group is None:
                # Boolean operator (has:attachment)
                value = "true"
            elif isinstance(value_group, tuple):
                # Multiple possible groups (quoted vs unquoted)
                value = match.group(value_group[0]) or match.group(value_group[1])
            else:
                value = match.group(value_group)

            if value:
                operators.append(ParsedOperator(
                    operator=op_type,
                    value=self._sanitize_value(value),
                    raw=raw
                ))

        # Remove matched operators from text
        cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return cleaned, operators

    def _apply_operator(self, result: ParsedQuery, op: ParsedOperator):
        """Apply a parsed operator to the result."""
        if op.operator == OperatorType.FROM:
            result.from_filter = self._sanitize_email(op.value)

        elif op.operator == OperatorType.TO:
            result.to_filter = self._sanitize_email(op.value)

        elif op.operator == OperatorType.SUBJECT:
            result.subject_filter = self._sanitize_subject(op.value)

        elif op.operator == OperatorType.HAS_ATTACHMENT:
            result.has_attachment = True

        elif op.operator == OperatorType.BEFORE:
            parsed_date = self._parse_date(op.value)
            if parsed_date:
                result.date_before = parsed_date
            else:
                result.parse_warnings.append(f"Invalid date format: {op.value}")

        elif op.operator == OperatorType.AFTER:
            parsed_date = self._parse_date(op.value)
            if parsed_date:
                result.date_after = parsed_date
            else:
                result.parse_warnings.append(f"Invalid date format: {op.value}")

        elif op.operator == OperatorType.IN_WORK_ORDER:
            result.work_order_id = op.value

        elif op.operator == OperatorType.THREAD:
            result.thread_id = op.value

    def _parse_date(self, value: str) -> Optional[date]:
        """Parse a date string, trying multiple formats."""
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    # Safety limits
    MAX_OPERATORS = 10  # Prevent pathological query parsing
    MAX_VALUE_LENGTH = 200
    MAX_SUBJECT_LENGTH = 100

    def _sanitize_value(self, value: str, for_like: bool = True) -> str:
        """
        Sanitize operator value to prevent injection.

        - Strip whitespace
        - Remove SQL-dangerous characters
        - Escape LIKE/ILIKE wildcards (%, _)
        - Normalize (lowercase for emails)
        - Limit length
        """
        if not value:
            return ""

        # Strip whitespace
        value = value.strip()

        # Limit length
        value = value[:self.MAX_VALUE_LENGTH]

        # Remove characters that could be used for SQL injection
        # Keep alphanumeric, @, ., -, _, space, and common punctuation
        value = re.sub(r"[;'\"\\`\x00]", '', value)

        # Escape LIKE/ILIKE wildcards to prevent pattern injection
        if for_like:
            value = value.replace('%', r'\%').replace('_', r'\_')

        return value

    def _sanitize_email(self, value: str) -> str:
        """Normalize and sanitize email/name for from:/to: filters."""
        value = self._sanitize_value(value, for_like=True)
        # Lowercase for case-insensitive matching
        return value.lower()

    def _sanitize_subject(self, value: str) -> str:
        """Sanitize subject filter with stricter length limit."""
        value = self._sanitize_value(value, for_like=True)
        return value[:self.MAX_SUBJECT_LENGTH]

    def _clean_free_text(self, text: str) -> str:
        """Clean up free text after operator extraction."""
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def parse_search_query(query: str) -> ParsedQuery:
    """
    Convenience function to parse a search query.

    Args:
        query: Raw search query string

    Returns:
        ParsedQuery with operators and free text
    """
    parser = QueryParser()
    return parser.parse(query)


def prepare_query_for_search(query: str) -> Dict[str, Any]:
    """
    Prepare a query for hybrid search.

    Returns dict with:
    - free_text: For embedding generation
    - filters: For RPC params
    - keywords: Entity keywords from free text
    - match_reasons: Human-readable filter descriptions
    """
    from extraction.entity_extractor import extract_keywords_for_search

    parsed = parse_search_query(query)

    # Extract entity keywords from free text
    keywords = extract_keywords_for_search(parsed.free_text) if parsed.free_text else []

    return {
        'free_text': parsed.free_text,
        'filters': parsed.to_rpc_params(),
        'keywords': keywords,
        'match_reasons': parsed.get_match_reasons(),
        'warnings': parsed.parse_warnings,
        'operators_count': len(parsed.operators_found),
    }


if __name__ == '__main__':
    # Test examples
    test_queries = [
        "watermaker PO-2024 from:supplier@marine.com",
        "subject:invoice after:2024-01-01 has:attachment",
        "engine parts before:2024-03-15",
        "from:\"John Smith\" to:captain@yacht.com urgent",
        "in:work_order:WO-2024-0547 status update",
        "thread:abc123 reply",
    ]

    parser = QueryParser()

    for q in test_queries:
        print(f"\nQuery: {q}")
        result = parser.parse(q)
        print(f"  Free text: '{result.free_text}'")
        print(f"  Operators: {len(result.operators_found)}")
        for op in result.operators_found:
            print(f"    - {op.operator.value}: {op.value}")
        print(f"  Filters: {result.to_rpc_params()}")
        print(f"  Match reasons: {result.get_match_reasons()}")
