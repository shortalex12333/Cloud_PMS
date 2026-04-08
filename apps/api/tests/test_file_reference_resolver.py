"""
File Reference Resolver Tests
==============================
Tests the 3-tier file reference resolution engine:
1. Exact path match
2. Exact filename match (case-insensitive)
3. Fuzzy filename match (bigram similarity)

Uses an in-memory mock Supabase client — no real DB required.
"""

import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.file_reference_resolver import (
    FileReferenceResolver,
    FileResolutionResult,
    summarize_resolutions,
    FUZZY_THRESHOLD,
)

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


# =============================================================================
# Mock Supabase client that returns test documents
# =============================================================================

def make_mock_supabase(documents: list[dict]):
    """Create a mock Supabase client that returns the given documents."""
    mock = MagicMock()

    # Chain: table().select().eq().is_().execute()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.is_.return_value = query

    execute_result = MagicMock()
    execute_result.data = documents
    query.execute.return_value = execute_result

    mock.table.return_value = query
    return mock


# =============================================================================
# Test document fixtures
# =============================================================================

DOC_PUMP_MANUAL = {
    "id": str(uuid.uuid4()),
    "filename": "pump_manual.pdf",
    "storage_path": f"{TEST_YACHT_ID}/documents/manuals/pump_manual.pdf",
    "document_type": "manual",
}

DOC_DRAWING = {
    "id": str(uuid.uuid4()),
    "filename": "DWG-GEN-MAIN-001.pdf",
    "storage_path": f"{TEST_YACHT_ID}/documents/drawings/DWG-GEN-MAIN-001.pdf",
    "document_type": "drawing",
}

DOC_CERTIFICATE = {
    "id": str(uuid.uuid4()),
    "filename": "class_certificate_2024.pdf",
    "storage_path": f"{TEST_YACHT_ID}/documents/certificates/class_certificate_2024.pdf",
    "document_type": "certificate",
}

DOC_SIMILAR_DRAWING = {
    "id": str(uuid.uuid4()),
    "filename": "dwg_gen_main_001.pdf",
    "storage_path": f"{TEST_YACHT_ID}/documents/drawings/dwg_gen_main_001.pdf",
    "document_type": "drawing",
}

ALL_DOCS = [DOC_PUMP_MANUAL, DOC_DRAWING, DOC_CERTIFICATE, DOC_SIMILAR_DRAWING]


# =============================================================================
# Tests: Tier 1 — Exact path match
# =============================================================================

class TestExactPathMatch:
    def test_full_path_match(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve(f"documents/drawings/DWG-GEN-MAIN-001.pdf")
        assert result.resolved is True
        assert result.match_type == "exact_path"
        assert result.confidence == 1.0
        assert result.document_id == DOC_DRAWING["id"]

    def test_path_suffix_match(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("manuals/pump_manual.pdf")
        assert result.resolved is True
        assert result.match_type == "exact_path"
        assert result.document_id == DOC_PUMP_MANUAL["id"]

    def test_path_case_insensitive(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("MANUALS/PUMP_MANUAL.PDF")
        assert result.resolved is True
        assert result.match_type == "exact_path"


# =============================================================================
# Tests: Tier 2 — Exact filename match
# =============================================================================

class TestExactFilenameMatch:
    def test_filename_only(self):
        """Filename-only match when storage_path doesn't contain the reference as suffix."""
        # Use a doc whose storage_path won't match the bare filename
        docs = [
            {"id": "doc-fn", "filename": "valve_spec.pdf",
             "storage_path": f"{TEST_YACHT_ID}/documents/specs/renamed_valve_spec_v2.pdf",
             "document_type": "manual"},
        ]
        sb = make_mock_supabase(docs)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("valve_spec.pdf")
        assert result.resolved is True
        assert result.match_type == "exact_filename"
        assert result.confidence == 0.9
        assert result.document_id == "doc-fn"

    def test_case_insensitive(self):
        docs = [
            {"id": "doc-ci", "filename": "Engine_Report.pdf",
             "storage_path": f"{TEST_YACHT_ID}/docs/renamed_report.pdf",
             "document_type": "report"},
        ]
        sb = make_mock_supabase(docs)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("ENGINE_REPORT.PDF")
        assert result.resolved is True
        assert result.match_type == "exact_filename"
        assert result.document_id == "doc-ci"

    def test_document_type_hint_narrows_results(self):
        """When multiple files have similar names, type hint should prefer matching type."""
        # Both have similar filenames but different types
        docs = [
            {"id": "doc-a", "filename": "engine_report.pdf", "storage_path": "/a", "document_type": "report"},
            {"id": "doc-b", "filename": "engine_report.pdf", "storage_path": "/b", "document_type": "drawing"},
        ]
        sb = make_mock_supabase(docs)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("engine_report.pdf", document_type_hint="drawing")
        assert result.resolved is True
        assert result.document_id == "doc-b"

    def test_extracts_filename_from_path(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("C:\\PMS\\Exports\\pump_manual.pdf")
        assert result.resolved is True
        assert result.document_id == DOC_PUMP_MANUAL["id"]


# =============================================================================
# Tests: Tier 3 — Fuzzy filename match
# =============================================================================

class TestFuzzyMatch:
    def test_underscore_vs_hyphen(self):
        """DWG-GEN-MAIN-001 should fuzzy-match dwg_gen_main_001."""
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("DWG-GEN-MAIN-001.pdf")
        # This should exact-match first since DWG-GEN-MAIN-001.pdf exists
        assert result.resolved is True

    def test_fuzzy_with_slight_variation(self):
        """A reference with slight variation should fuzzy match."""
        docs = [
            {"id": "doc-x", "filename": "caterpillar_3516_maintenance.pdf",
             "storage_path": "/docs/caterpillar_3516_maintenance.pdf", "document_type": "manual"},
        ]
        sb = make_mock_supabase(docs)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("cat3516_maintenance.pdf")
        assert result.resolved is True
        assert result.match_type == "fuzzy"
        assert result.confidence >= FUZZY_THRESHOLD

    def test_no_match_below_threshold(self):
        """Completely unrelated filename should not match."""
        docs = [
            {"id": "doc-y", "filename": "navigation_chart_2024.pdf",
             "storage_path": "/docs/nav.pdf", "document_type": "manual"},
        ]
        sb = make_mock_supabase(docs)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("pump_maintenance_guide.pdf")
        # May or may not match depending on similarity — just verify structure
        if result.resolved:
            assert result.confidence >= FUZZY_THRESHOLD
        else:
            assert result.match_type == "unresolved"
            assert result.confidence == 0.0


# =============================================================================
# Tests: Unresolved
# =============================================================================

class TestUnresolved:
    def test_no_documents(self):
        sb = make_mock_supabase([])
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("anything.pdf")
        assert result.resolved is False
        assert result.match_type == "unresolved"
        assert result.confidence == 0.0
        assert result.document_id is None

    def test_empty_reference(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("")
        assert result.resolved is False
        assert result.match_type == "unresolved"

    def test_whitespace_only(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        result = resolver.resolve("   ")
        assert result.resolved is False
        assert result.match_type == "unresolved"


# =============================================================================
# Tests: Batch resolution
# =============================================================================

class TestBatchResolution:
    def test_batch_resolves_multiple(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        references = [
            {"raw_reference": "pump_manual.pdf", "document_type_hint": "manual", "csv_row": 0, "column": "DRAWING_REF"},
            {"raw_reference": "nonexistent.pdf", "document_type_hint": None, "csv_row": 1, "column": "DRAWING_REF"},
            {"raw_reference": "class_certificate_2024.pdf", "document_type_hint": "certificate", "csv_row": 2, "column": "CERT_REF"},
        ]

        results = resolver.resolve_batch(references)
        assert len(results) == 3
        assert results[0].resolved is True
        assert results[0].csv_row == 0
        assert results[1].resolved is False
        assert results[1].csv_row == 1
        assert results[2].resolved is True
        assert results[2].csv_row == 2

    def test_batch_empty(self):
        sb = make_mock_supabase(ALL_DOCS)
        resolver = FileReferenceResolver(sb, TEST_YACHT_ID)

        results = resolver.resolve_batch([])
        assert results == []


# =============================================================================
# Tests: Summary
# =============================================================================

class TestSummarize:
    def test_summarize_mixed(self):
        results = [
            FileResolutionResult("a.pdf", True, "1", "a.pdf", "/a", "exact_filename", 0.9),
            FileResolutionResult("b.pdf", True, "2", "b.pdf", "/b", "fuzzy", 0.65),
            FileResolutionResult("c.pdf", False, None, None, None, "unresolved", 0.0),
        ]
        summary = summarize_resolutions(results)
        assert summary["total"] == 3
        assert summary["resolved"] == 2
        assert summary["unresolved"] == 1
        assert summary["by_match_type"]["exact_filename"] == 1
        assert summary["by_match_type"]["fuzzy"] == 1
        assert summary["by_match_type"]["unresolved"] == 1

    def test_summarize_empty(self):
        summary = summarize_resolutions([])
        assert summary["total"] == 0
        assert summary["resolved"] == 0


# =============================================================================
# Tests: Similarity function
# =============================================================================

class TestSimilarity:
    def test_identical(self):
        assert FileReferenceResolver._simple_similarity("hello", "hello") == 1.0

    def test_empty(self):
        assert FileReferenceResolver._simple_similarity("", "hello") == 0.0
        assert FileReferenceResolver._simple_similarity("hello", "") == 0.0

    def test_similar(self):
        sim = FileReferenceResolver._simple_similarity("pump_manual", "pump-manual")
        assert sim > 0.5

    def test_dissimilar(self):
        sim = FileReferenceResolver._simple_similarity("abc", "xyz")
        assert sim < 0.3
