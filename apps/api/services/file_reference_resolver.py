"""
File Reference Resolver
=======================
Resolves file/document references found in PMS CSV exports (e.g., DRAWING_REF)
against the yacht's existing document library.

Three-tier search strategy:
1. Exact path match (storage_path ends with reference)
2. Exact filename match (case-insensitive)
3. Fuzzy filename match (pg_trgm similarity > 0.3)

Used during the import pipeline's resolve stage, between transform and dry-run.
"""

import os
import logging
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger("import.file_resolver")

# Minimum similarity score for fuzzy matches to be considered
FUZZY_THRESHOLD = 0.3


@dataclass
class FileResolutionResult:
    """Result of attempting to resolve a file reference."""
    raw_reference: str
    resolved: bool
    document_id: Optional[str]
    filename: Optional[str]
    storage_path: Optional[str]
    match_type: str  # "exact_path" | "exact_filename" | "fuzzy" | "unresolved"
    confidence: float
    csv_row: Optional[int] = None
    column: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class FileReferenceResolver:
    """
    Resolves file references from PMS exports against a yacht's document library.

    Usage:
        resolver = FileReferenceResolver(supabase_client, yacht_id)
        result = resolver.resolve("pump_manual.pdf", document_type_hint="drawing")
    """

    def __init__(self, supabase_client, yacht_id: str):
        self._supabase = supabase_client
        self._yacht_id = yacht_id
        self._doc_cache = None  # lazy-loaded for batch operations

    def _load_doc_cache(self):
        """Pre-fetch all documents for the yacht into memory for batch matching."""
        if self._doc_cache is not None:
            return

        try:
            response = (
                self._supabase.table("documents")
                .select("id, filename, storage_path, document_type")
                .eq("yacht_id", self._yacht_id)
                .is_("deleted_at", "null")
                .execute()
            )
            self._doc_cache = response.data or []
            logger.info(
                "Loaded %d documents for yacht %s into resolver cache",
                len(self._doc_cache), self._yacht_id
            )
        except Exception as e:
            logger.error("Failed to load document cache: %s", e)
            self._doc_cache = []

    @staticmethod
    def _extract_filename(reference: str) -> str:
        """Extract the filename portion from a path or reference string."""
        # Handle both forward and backslash paths
        normalized = reference.replace("\\", "/")
        return os.path.basename(normalized).strip()

    @staticmethod
    def _normalize_for_comparison(name: str) -> str:
        """Normalize a filename for comparison: lowercase, strip whitespace."""
        return name.lower().strip()

    @staticmethod
    def _simple_similarity(a: str, b: str) -> float:
        """
        Simple character-level similarity for in-memory fuzzy matching.
        Uses bigram overlap (Dice coefficient) as a lightweight pg_trgm approximation.
        """
        a = a.lower()
        b = b.lower()
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0

        def bigrams(s):
            return set(s[i:i+2] for i in range(len(s) - 1))

        a_bigrams = bigrams(a)
        b_bigrams = bigrams(b)
        if not a_bigrams or not b_bigrams:
            return 0.0

        overlap = len(a_bigrams & b_bigrams)
        return (2.0 * overlap) / (len(a_bigrams) + len(b_bigrams))

    def resolve(
        self,
        raw_reference: str,
        document_type_hint: Optional[str] = None,
    ) -> FileResolutionResult:
        """
        Resolve a single file reference against the yacht's documents.

        Args:
            raw_reference: The raw value from the CSV column (filename, path, or ref code)
            document_type_hint: Optional hint to prefer matching document types (e.g., "drawing")

        Returns:
            FileResolutionResult with match details
        """
        if not raw_reference or not raw_reference.strip():
            return FileResolutionResult(
                raw_reference=raw_reference or "",
                resolved=False,
                document_id=None,
                filename=None,
                storage_path=None,
                match_type="unresolved",
                confidence=0.0,
            )

        raw_reference = raw_reference.strip()
        self._load_doc_cache()

        # Tier 1: Exact path match
        result = self._match_exact_path(raw_reference)
        if result:
            return result

        # Tier 2: Exact filename match
        extracted_filename = self._extract_filename(raw_reference)
        result = self._match_exact_filename(raw_reference, extracted_filename, document_type_hint)
        if result:
            return result

        # Tier 3: Fuzzy filename match
        result = self._match_fuzzy(raw_reference, extracted_filename, document_type_hint)
        if result:
            return result

        # No match found
        logger.debug("No match for reference '%s' in yacht %s", raw_reference, self._yacht_id)
        return FileResolutionResult(
            raw_reference=raw_reference,
            resolved=False,
            document_id=None,
            filename=None,
            storage_path=None,
            match_type="unresolved",
            confidence=0.0,
        )

    def _match_exact_path(self, raw_reference: str) -> Optional[FileResolutionResult]:
        """Tier 1: Check if any document's storage_path ends with the reference."""
        normalized_ref = self._normalize_for_comparison(raw_reference)
        for doc in self._doc_cache:
            storage_path = doc.get("storage_path", "") or ""
            if storage_path and self._normalize_for_comparison(storage_path).endswith(normalized_ref):
                logger.info("Exact path match: '%s' → doc %s", raw_reference, doc["id"])
                return FileResolutionResult(
                    raw_reference=raw_reference,
                    resolved=True,
                    document_id=doc["id"],
                    filename=doc.get("filename"),
                    storage_path=storage_path,
                    match_type="exact_path",
                    confidence=1.0,
                )
        return None

    def _match_exact_filename(
        self,
        raw_reference: str,
        extracted_filename: str,
        document_type_hint: Optional[str],
    ) -> Optional[FileResolutionResult]:
        """Tier 2: Match by filename (case-insensitive). Prefer matching document_type."""
        normalized = self._normalize_for_comparison(extracted_filename)
        if not normalized:
            return None

        matches = []
        for doc in self._doc_cache:
            doc_filename = doc.get("filename", "") or ""
            if self._normalize_for_comparison(doc_filename) == normalized:
                matches.append(doc)

        if not matches:
            return None

        # If multiple matches and we have a type hint, prefer the matching type
        if len(matches) > 1 and document_type_hint:
            typed_matches = [
                d for d in matches
                if (d.get("document_type", "") or "").lower() == document_type_hint.lower()
            ]
            if typed_matches:
                matches = typed_matches

        # Pick the first (or only) match
        doc = matches[0]
        logger.info("Exact filename match: '%s' → doc %s", raw_reference, doc["id"])
        return FileResolutionResult(
            raw_reference=raw_reference,
            resolved=True,
            document_id=doc["id"],
            filename=doc.get("filename"),
            storage_path=doc.get("storage_path"),
            match_type="exact_filename",
            confidence=0.9,
        )

    def _match_fuzzy(
        self,
        raw_reference: str,
        extracted_filename: str,
        document_type_hint: Optional[str],
    ) -> Optional[FileResolutionResult]:
        """Tier 3: Fuzzy match using bigram similarity (Dice coefficient)."""
        if not extracted_filename:
            return None

        # Strip extension for comparison — "DWG-001.pdf" should match "dwg_001.pdf"
        ref_stem = os.path.splitext(extracted_filename)[0]

        candidates = []
        for doc in self._doc_cache:
            doc_filename = doc.get("filename", "") or ""
            if not doc_filename:
                continue

            doc_stem = os.path.splitext(doc_filename)[0]

            # Compare stems (without extension)
            sim = self._simple_similarity(ref_stem, doc_stem)
            if sim >= FUZZY_THRESHOLD:
                candidates.append((sim, doc))

        if not candidates:
            return None

        # Sort by similarity descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        # If we have a type hint, boost candidates that match
        if document_type_hint and len(candidates) > 1:
            typed = [
                (sim, doc) for sim, doc in candidates
                if (doc.get("document_type", "") or "").lower() == document_type_hint.lower()
            ]
            if typed and typed[0][0] >= candidates[0][0] * 0.9:
                candidates = typed

        best_sim, best_doc = candidates[0]
        logger.info(
            "Fuzzy match: '%s' → doc %s (similarity=%.2f)",
            raw_reference, best_doc["id"], best_sim
        )
        return FileResolutionResult(
            raw_reference=raw_reference,
            resolved=True,
            document_id=best_doc["id"],
            filename=best_doc.get("filename"),
            storage_path=best_doc.get("storage_path"),
            match_type="fuzzy",
            confidence=round(best_sim, 3),
        )

    def resolve_batch(
        self,
        references: list[dict],
    ) -> list[FileResolutionResult]:
        """
        Resolve a batch of file references.

        Args:
            references: List of dicts with keys:
                - raw_reference: str
                - document_type_hint: str | None
                - csv_row: int (optional)
                - column: str (optional)

        Returns:
            List of FileResolutionResult, one per input reference
        """
        self._load_doc_cache()

        results = []
        for ref in references:
            result = self.resolve(
                raw_reference=ref["raw_reference"],
                document_type_hint=ref.get("document_type_hint"),
            )
            result.csv_row = ref.get("csv_row")
            result.column = ref.get("column")
            results.append(result)

        resolved_count = sum(1 for r in results if r.resolved)
        logger.info(
            "Batch resolve: %d/%d references resolved for yacht %s",
            resolved_count, len(results), self._yacht_id
        )
        return results


def summarize_resolutions(results: list[FileResolutionResult]) -> dict:
    """
    Create a summary of resolution results for API responses.
    """
    by_type = {}
    for r in results:
        by_type[r.match_type] = by_type.get(r.match_type, 0) + 1

    return {
        "total": len(results),
        "resolved": sum(1 for r in results if r.resolved),
        "unresolved": sum(1 for r in results if not r.resolved),
        "by_match_type": by_type,
    }
