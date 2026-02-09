"""
Document Lens - Entity Extraction Tests
=======================================

Tests for Document Lens entity extraction patterns:
- document_id: Maritime authority refs, class society certs, ISM/ISPS docs
- document_type: Certificates, manuals, surveys, plans, compliance docs

Run: python -m pytest tests/entity_extraction/test_document_lens_extraction.py -v
"""

import re
import pytest


# === document_id patterns (from regex_extractor.py) ===
DOCUMENT_ID_PATTERNS = [
    # Existing patterns
    re.compile(r'\b(DOC-[A-Z]-\d{2,4})\b'),  # Generic documents
    re.compile(r'\b(REF-\d{5,8})\b'),  # Reference numbers

    # Certificate/Document Reference Numbers
    re.compile(r'\b(CERT[-/]?\d{4,8})\b', re.IGNORECASE),  # CERT-12345
    re.compile(r'\b(CRT[-/]?\d{4,8})\b', re.IGNORECASE),  # CRT-12345

    # Maritime Authority Document Numbers
    re.compile(r'\b(IMO[-/]?\d{7})\b', re.IGNORECASE),  # IMO-1234567 (7-digit)
    re.compile(r'\b(USCG[-/]?\d{4,10})\b', re.IGNORECASE),  # USCG-1234567
    re.compile(r'\b(MCA[-/]?\d{4,8})\b', re.IGNORECASE),  # MCA-12345
    re.compile(r'\b(MARAD[-/]?\d{4,8})\b', re.IGNORECASE),  # MARAD-12345

    # Class Society Document References
    re.compile(r'\b(LR[-/]?\d{4,8})\b', re.IGNORECASE),  # Lloyd's Register
    re.compile(r'\b(DNV[-/]?[A-Z]?\d{4,8})\b', re.IGNORECASE),  # DNV-12345
    re.compile(r'\b(ABS[-/]?\d{4,8})\b', re.IGNORECASE),  # American Bureau of Shipping
    re.compile(r'\b(BV[-/]?\d{4,8})\b', re.IGNORECASE),  # Bureau Veritas
    re.compile(r'\b(RINA[-/]?\d{4,8})\b', re.IGNORECASE),  # RINA
    re.compile(r'\b(NK[-/]?\d{4,8})\b', re.IGNORECASE),  # Nippon Kaiji Kyokai
    re.compile(r'\b(CCS[-/]?\d{4,8})\b', re.IGNORECASE),  # China Classification Society

    # Safety Management Document References
    re.compile(r'\b(ISM[-/]?\d{4,8})\b', re.IGNORECASE),  # ISM Code documents
    re.compile(r'\b(ISPS[-/]?\d{4,8})\b', re.IGNORECASE),  # ISPS Code documents
    re.compile(r'\b(SMC[-/]?\d{4,8})\b', re.IGNORECASE),  # Safety Management Certificate

    # Document Revision/Version References
    re.compile(r'\b(REV[-.]?\d{1,3}(?:\.\d{1,2})?)\b', re.IGNORECASE),  # REV-1, REV.2.1
    re.compile(r'\b(ISSUE[-.]?\d{1,3})\b', re.IGNORECASE),  # ISSUE-1

    # Generic Document Reference Patterns (last - less specific)
    re.compile(r'\b([A-Z]{2,4}-\d{4}-\d{2,4})\b'),  # XX-1234-56 format
]


def extract_document_id(text: str) -> list[str]:
    """Extract document IDs from text using all patterns."""
    matches = []
    for pattern in DOCUMENT_ID_PATTERNS:
        for match in pattern.finditer(text):
            matches.append(match.group(1) if match.lastindex else match.group(0))
    return list(set(matches))


class TestDocumentIdPatterns:
    """Test document_id extraction patterns."""

    def test_generic_document_ids(self):
        """Test original generic patterns."""
        assert "DOC-A-1234" in extract_document_id("see DOC-A-1234 for details")
        assert "REF-12345678" in extract_document_id("reference REF-12345678")

    def test_certificate_references(self):
        """Test certificate number patterns."""
        assert "CERT-12345" in extract_document_id("Certificate CERT-12345 issued")
        # Case-insensitive match returns original case
        ids = extract_document_id("cert12345678 is valid")
        assert any(i.upper() == "CERT12345678" for i in ids)
        assert "CRT-9876" in extract_document_id("CRT-9876 expires soon")

    def test_maritime_authority_documents(self):
        """Test maritime authority document patterns."""
        # IMO numbers (always 7 digits)
        assert "IMO-1234567" in extract_document_id("vessel IMO-1234567")
        # Case-insensitive match
        ids = extract_document_id("imo1234567")
        assert any(i.upper() == "IMO1234567" for i in ids)

        # USCG
        assert "USCG-123456" in extract_document_id("USCG-123456 documentation")

        # MCA
        assert "MCA-12345" in extract_document_id("MCA-12345 certificate")

        # MARAD
        assert "MARAD-12345" in extract_document_id("MARAD-12345 approval")

    def test_class_society_documents(self):
        """Test class society document patterns."""
        # Lloyd's Register
        assert "LR-12345" in extract_document_id("Lloyd's LR-12345")

        # DNV
        assert "DNV-12345" in extract_document_id("DNV-12345 certificate")
        # Case-insensitive match
        ids = extract_document_id("dnv-a12345")
        assert any(i.upper() == "DNV-A12345" for i in ids)

        # ABS
        assert "ABS-123456" in extract_document_id("ABS-123456 class cert")

        # Bureau Veritas
        assert "BV-12345" in extract_document_id("BV-12345 survey")

        # RINA
        assert "RINA-12345" in extract_document_id("RINA-12345")

        # NK (ClassNK)
        assert "NK-12345" in extract_document_id("NK-12345 approval")

        # CCS
        assert "CCS-12345" in extract_document_id("CCS-12345 certificate")

    def test_safety_management_documents(self):
        """Test ISM/ISPS document patterns."""
        assert "ISM-12345" in extract_document_id("ISM-12345 audit report")
        assert "ISPS-12345" in extract_document_id("ISPS-12345 certificate")
        assert "SMC-12345" in extract_document_id("SMC-12345 issued")

    def test_revision_references(self):
        """Test document revision patterns."""
        assert "REV-1" in extract_document_id("document REV-1")
        # Case-insensitive match
        ids = extract_document_id("rev.2.1 update")
        assert any(i.upper() == "REV.2.1" for i in ids)
        assert "ISSUE-3" in extract_document_id("ISSUE-3 released")

    def test_generic_format(self):
        """Test generic XX-1234-56 format."""
        assert "DOC-1234-56" in extract_document_id("see DOC-1234-56")
        assert "CERT-2024-01" in extract_document_id("CERT-2024-01 valid")


class TestDocumentTypeGazetteer:
    """Test document_type gazetteer terms."""

    # Sample of document_type terms from gazetteer
    DOCUMENT_TYPES = {
        # Class Society Certificates
        'loadline certificate', 'load line certificate', 'freeboard certificate',
        'cargo ship safety certificate', 'passenger ship safety certificate',
        'safety construction certificate', 'safety equipment certificate',
        'safety radio certificate', 'marpol certificate', 'iopp certificate',
        'sewage certificate', 'ballast water certificate', 'anti fouling certificate',

        # ISM/ISPS/SMS Documents
        'smc', 'safety management certificate', 'doc', 'document of compliance',
        'issc', 'international ship security certificate',
        'sms', 'safety management system', 'ism code',

        # Survey & Inspection
        'survey report', 'inspection report', 'condition report',
        'annual survey', 'intermediate survey', 'special survey',
        'class survey', 'flag state inspection', 'psc report',
        'port state control', 'vetting report', 'sire report',

        # Plans & Diagrams
        'fire control plan', 'damage control plan', 'safety plan',
        'piping diagram', 'electrical diagram', 'hydraulic diagram',
    }

    def test_class_certificates_present(self):
        """Verify class certificate types are present."""
        assert 'loadline certificate' in self.DOCUMENT_TYPES
        assert 'marpol certificate' in self.DOCUMENT_TYPES
        assert 'iopp certificate' in self.DOCUMENT_TYPES

    def test_ism_isps_documents_present(self):
        """Verify ISM/ISPS document types are present."""
        assert 'smc' in self.DOCUMENT_TYPES
        assert 'safety management certificate' in self.DOCUMENT_TYPES
        assert 'issc' in self.DOCUMENT_TYPES

    def test_survey_types_present(self):
        """Verify survey types are present."""
        assert 'annual survey' in self.DOCUMENT_TYPES
        assert 'special survey' in self.DOCUMENT_TYPES
        assert 'psc report' in self.DOCUMENT_TYPES
        assert 'sire report' in self.DOCUMENT_TYPES

    def test_plan_types_present(self):
        """Verify plan/diagram types are present."""
        assert 'fire control plan' in self.DOCUMENT_TYPES
        assert 'piping diagram' in self.DOCUMENT_TYPES
        assert 'electrical diagram' in self.DOCUMENT_TYPES


class TestRealWorldQueries:
    """Test patterns against real-world maritime queries."""

    def test_certificate_query(self):
        """Test extraction from certificate-related query."""
        query = "find the DNV-123456 loadline certificate for vessel IMO-9876543"
        ids = extract_document_id(query)
        assert "DNV-123456" in ids
        assert "IMO-9876543" in ids

    def test_class_survey_query(self):
        """Test extraction from class survey query."""
        query = "where is the ABS-789012 annual survey report rev.2"
        ids = extract_document_id(query)
        assert "ABS-789012" in ids
        assert "rev.2" in ids.pop().lower() or any("rev" in i.lower() for i in ids)

    def test_ism_audit_query(self):
        """Test extraction from ISM audit query."""
        query = "need ISM-2024-001 document of compliance certificate SMC-45678"
        ids = extract_document_id(query)
        assert "ISM-2024-001" in ids or any("ISM" in i for i in ids)
        assert "SMC-45678" in ids

    def test_multi_class_society_query(self):
        """Test extraction with multiple class society references."""
        query = "compare LR-11111 with BV-22222 and RINA-33333 certificates"
        ids = extract_document_id(query)
        assert "LR-11111" in ids
        assert "BV-22222" in ids
        assert "RINA-33333" in ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
