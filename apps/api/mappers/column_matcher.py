"""
Column Matcher
==============
Maps source column names to CelesteOS field names using:
1. Known source profiles (deterministic, highest confidence)
2. Fuzzy matching via rapidfuzz (for unknown sources or unmatched columns)

Returns a list of ColumnMapping with suggested_target and confidence score.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("import.column_matcher")

# Try rapidfuzz, fall back to basic matching
try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed — using basic string matching only")

from mappers.source_profiles import get_profile_mapping, FILE_REF_COLUMN_HINTS
from parsers.base_parser import looks_like_file_ref


@dataclass
class ColumnMapping:
    """A suggested column mapping with confidence score."""
    source_name: str
    suggested_target: Optional[str]
    confidence: float  # 0.0 to 1.0
    action: str = "map"  # map, skip, link_as_document
    inferred_type: Optional[str] = None  # None, "file_ref"


# Confidence thresholds (matching the brief)
CONFIDENCE_GREEN = 0.90   # auto-suggest, shown in green
CONFIDENCE_AMBER = 0.60   # suggest but warn, shown in amber
# Below 0.60 = red, user must manually assign or skip


def normalize_column_name(name: str) -> str:
    """Normalize a column name for fuzzy matching."""
    # Lowercase
    s = name.lower().strip()
    # Replace common separators with underscore
    s = re.sub(r"[\s\-\.]+", "_", s)
    # Remove parentheses and their content
    s = re.sub(r"\([^)]*\)", "", s)
    # Remove trailing underscores
    s = s.strip("_")
    return s


def _is_file_ref_column_name(col_name: str) -> bool:
    """Check if a column name looks like a file reference column."""
    normalized = col_name.strip()
    # Check against known hints (case-insensitive)
    return normalized in FILE_REF_COLUMN_HINTS or normalized.lower() in {
        h.lower() for h in FILE_REF_COLUMN_HINTS
    }


def match_columns(
    source_columns: list[str],
    domain: str,
    source: str = "generic",
    vocabulary: Optional[list[str]] = None,
    column_samples: Optional[dict[str, list[str]]] = None,
) -> list[ColumnMapping]:
    """
    Match source column names to CelesteOS fields.

    Args:
        source_columns: Column names from the parsed file
        domain: CelesteOS domain (equipment, work_orders, faults, parts, certificates)
        source: PMS source (idea_yacht, seahub, sealogical, generic)
        vocabulary: List of valid CelesteOS field names for this domain
        column_samples: Optional dict of {column_name: [sample_values]} for file ref detection

    Returns:
        List of ColumnMapping with suggested_target and confidence
    """
    if vocabulary is None:
        vocabulary = []
    if column_samples is None:
        column_samples = {}

    # 1. Try known profile first (deterministic)
    profile = get_profile_mapping(source, domain)
    results = []

    for col_name in source_columns:
        # Check known profile (case-insensitive)
        if profile:
            # Try exact match first
            profile_match = profile.get(col_name)
            if profile_match is None:
                # Try case-insensitive
                for pkey, pval in profile.items():
                    if pkey.lower() == col_name.lower():
                        profile_match = pval
                        break

            if profile_match is not None:
                target, confidence = profile_match
                # Check if profile routes to _file_ref: sentinel
                if target and target.startswith("_file_ref:"):
                    results.append(ColumnMapping(
                        source_name=col_name,
                        suggested_target="file_ref",
                        confidence=0.90,
                        action="link_as_document",
                        inferred_type="file_ref",
                    ))
                elif target is None:
                    results.append(ColumnMapping(
                        source_name=col_name,
                        suggested_target=None,
                        confidence=0.0,
                        action="skip",
                    ))
                else:
                    results.append(ColumnMapping(
                        source_name=col_name,
                        suggested_target=target,
                        confidence=confidence,
                        action="map",
                    ))
                continue

        # 1b. Check if column name matches file reference hints
        samples = column_samples.get(col_name, [])
        name_is_file_ref = _is_file_ref_column_name(col_name)
        value_file_ref_score = looks_like_file_ref(samples) if samples else 0.0

        if name_is_file_ref and value_file_ref_score >= 0.3:
            # Both name AND values suggest file ref — high confidence
            results.append(ColumnMapping(
                source_name=col_name,
                suggested_target="file_ref",
                confidence=0.90,
                action="link_as_document",
                inferred_type="file_ref",
            ))
            continue
        elif name_is_file_ref:
            # Name matches but no samples or low value match — still flag at lower confidence
            results.append(ColumnMapping(
                source_name=col_name,
                suggested_target="file_ref",
                confidence=0.75,
                action="link_as_document",
                inferred_type="file_ref",
            ))
            continue
        elif value_file_ref_score >= 0.5:
            # Values strongly suggest file refs even though name doesn't match hints
            results.append(ColumnMapping(
                source_name=col_name,
                suggested_target="file_ref",
                confidence=0.75,
                action="link_as_document",
                inferred_type="file_ref",
            ))
            continue

        # 2. Fuzzy match against vocabulary
        if vocabulary and RAPIDFUZZ_AVAILABLE:
            normalized = normalize_column_name(col_name)
            match = process.extractOne(
                normalized,
                [normalize_column_name(v) for v in vocabulary],
                scorer=fuzz.WRatio,
                score_cutoff=50,  # minimum 50% to consider
            )
            if match:
                matched_normalized, score, idx = match
                target = vocabulary[idx]
                confidence = score / 100.0  # rapidfuzz returns 0-100

                results.append(ColumnMapping(
                    source_name=col_name,
                    suggested_target=target,
                    confidence=confidence,
                    action="map" if confidence >= CONFIDENCE_AMBER else "skip",
                ))
                continue

        # 3. No match found
        results.append(ColumnMapping(
            source_name=col_name,
            suggested_target=None,
            confidence=0.0,
            action="skip",
        ))

    # Log summary
    mapped = sum(1 for r in results if r.action == "map")
    skipped = sum(1 for r in results if r.action == "skip")
    file_refs = sum(1 for r in results if r.action == "link_as_document")
    green = sum(1 for r in results if r.confidence >= CONFIDENCE_GREEN)
    amber = sum(1 for r in results if CONFIDENCE_AMBER <= r.confidence < CONFIDENCE_GREEN)
    red = sum(1 for r in results if r.action == "map" and r.confidence < CONFIDENCE_AMBER)
    logger.info(
        f"[ColumnMatcher] {source}/{domain}: {mapped} mapped, {skipped} skipped, "
        f"{file_refs} file_refs (green={green}, amber={amber}, red={red})"
    )

    return results
