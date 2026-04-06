"""
Tests for the CSV parser.
Verification-integrity compliant: every assertion checks CONTENT, not just existence.
"""

import os
import sys
import pytest

# Ensure the api directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers.csv_parser import parse_csv, detect_encoding, detect_delimiter, find_header_row, detect_date_format

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "import_samples")


def load_fixture(name: str) -> bytes:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "rb") as f:
        return f.read()


# =============================================================================
# IDEA Yacht (semicolon delimiter, UPPER_SNAKE_CASE, DD-MMM-YYYY dates)
# =============================================================================

class TestIdeaYachtEquipment:
    """Test parsing IDEA Yacht equipment export."""

    def setup_method(self):
        raw = load_fixture("idea_yacht_equipment.csv")
        self.result = parse_csv(raw, "idea_yacht_equipment.csv")

    def test_encoding_detected(self):
        # IDEA Yacht fixture is UTF-8 (test fixture; real exports may be Latin-1)
        assert self.result.encoding_detected in ("utf-8", "ascii")

    def test_delimiter_is_semicolon(self):
        """IDEA Yacht uses semicolons, not commas."""
        assert self.result.delimiter_detected == ";", \
            f"Expected semicolon delimiter, got {repr(self.result.delimiter_detected)}"

    def test_header_row_is_zero(self):
        """No metadata rows — header is row 0."""
        assert self.result.header_row == 0

    def test_row_count_is_15(self):
        """Fixture has exactly 15 equipment records."""
        assert self.result.row_count == 15, \
            f"Expected 15 rows, got {self.result.row_count}"

    def test_columns_include_equip_name(self):
        """IDEA Yacht exports EQUIP_NAME as the equipment name column."""
        col_names = [c.source_name for c in self.result.columns]
        assert "EQUIP_NAME" in col_names, \
            f"Expected EQUIP_NAME in columns, got {col_names}"

    def test_columns_include_parent_equip_id(self):
        """IDEA Yacht has hierarchical equipment with PARENT_EQUIP_ID."""
        col_names = [c.source_name for c in self.result.columns]
        assert "PARENT_EQUIP_ID" in col_names

    def test_sample_values_are_real_data(self):
        """Sample values must contain actual equipment names, not empty strings."""
        equip_col = next(c for c in self.result.columns if c.source_name == "EQUIP_NAME")
        assert len(equip_col.sample_values) >= 3, \
            f"Expected >=3 sample values, got {len(equip_col.sample_values)}"
        assert "Main Engine Port" in equip_col.sample_values, \
            f"Expected 'Main Engine Port' in samples, got {equip_col.sample_values}"

    def test_date_format_detected(self):
        """IDEA Yacht uses DD-MMM-YYYY format."""
        assert self.result.date_format_detected == "DD-MMM-YYYY", \
            f"Expected DD-MMM-YYYY, got {self.result.date_format_detected}"

    def test_domain_detected_as_equipment(self):
        """Domain should be inferred as 'equipment' from column names."""
        assert self.result.domain_hint == "equipment", \
            f"Expected domain 'equipment', got {self.result.domain_hint}"

    def test_first_row_has_correct_data(self):
        """Verify first row content — not just that rows exist."""
        first = self.result.rows[0]
        assert first["EQUIP_NAME"] == "Main Engine Port"
        assert first["MAKER"] == "MTU"
        assert first["MODEL"] == "16V4000 M93L"
        assert first["SERIAL_NO"] == "MTU-2019-7834"


class TestIdeaYachtWorkOrders:
    """Test parsing IDEA Yacht work order export."""

    def setup_method(self):
        raw = load_fixture("idea_yacht_work_orders.csv")
        self.result = parse_csv(raw, "idea_yacht_work_orders.csv")

    def test_delimiter_is_semicolon(self):
        assert self.result.delimiter_detected == ";"

    def test_row_count_is_12(self):
        assert self.result.row_count == 12

    def test_domain_detected_as_work_orders(self):
        assert self.result.domain_hint == "work_orders"

    def test_has_wo_number_column(self):
        col_names = [c.source_name for c in self.result.columns]
        assert "WO_NUMBER" in col_names

    def test_first_row_content(self):
        first = self.result.rows[0]
        assert first["WO_NUMBER"] == "WO-2025-001"
        assert first["STATUS"] == "COMPLETED"
        assert first["PRIORITY"] == "HIGH"


# =============================================================================
# Seahub (comma delimiter, snake_case, ISO dates)
# =============================================================================

class TestSeahubEquipment:
    """Test parsing Seahub equipment export."""

    def setup_method(self):
        raw = load_fixture("seahub_equipment.csv")
        self.result = parse_csv(raw, "seahub_equipment.csv")

    def test_delimiter_is_comma(self):
        assert self.result.delimiter_detected == ","

    def test_row_count_is_8(self):
        assert self.result.row_count == 8

    def test_domain_detected_as_equipment(self):
        assert self.result.domain_hint == "equipment"

    def test_uses_snake_case_headers(self):
        col_names = [c.source_name for c in self.result.columns]
        assert "equipment_name" in col_names
        assert "serial_number" in col_names


class TestSeahubDefects:
    """Test parsing Seahub defects export — vocabulary mismatch test."""

    def setup_method(self):
        raw = load_fixture("seahub_defects.csv")
        self.result = parse_csv(raw, "seahub_defects.csv")

    def test_delimiter_is_comma(self):
        assert self.result.delimiter_detected == ","

    def test_row_count_is_5(self):
        assert self.result.row_count == 5

    def test_domain_detected_as_faults(self):
        """Seahub calls them 'defects' but domain should map to 'faults'."""
        assert self.result.domain_hint == "faults", \
            f"Expected domain 'faults' (from defect_id column), got {self.result.domain_hint}"

    def test_has_defect_columns(self):
        col_names = [c.source_name for c in self.result.columns]
        assert "defect_id" in col_names
        assert "corrective_action" in col_names


class TestSeahubCertificates:
    """Test parsing Seahub certificates export."""

    def setup_method(self):
        raw = load_fixture("seahub_certificates.csv")
        self.result = parse_csv(raw, "seahub_certificates.csv")

    def test_row_count_is_8(self):
        assert self.result.row_count == 8

    def test_domain_detected_as_certificates(self):
        assert self.result.domain_hint == "certificates"

    def test_date_format_is_iso(self):
        """Seahub uses ISO dates."""
        assert self.result.date_format_detected == "ISO"


# =============================================================================
# Sealogical (metadata rows above header, DD/MM/YYYY dates, Title Case)
# =============================================================================

class TestSealogicalEquipment:
    """Test parsing Sealogical equipment export with metadata rows."""

    def setup_method(self):
        raw = load_fixture("sealogical_equipment.csv")
        self.result = parse_csv(raw, "sealogical_equipment.csv")

    def test_header_row_skips_metadata(self):
        """Sealogical has 4 metadata rows before the header."""
        assert self.result.header_row == 4, \
            f"Expected header at row 4 (after metadata), got {self.result.header_row}"

    def test_metadata_rows_warning(self):
        """Should warn about skipped metadata rows."""
        skip_warnings = [w for w in self.result.warnings if "metadata" in w.message.lower()]
        assert len(skip_warnings) >= 1

    def test_row_count_is_8(self):
        assert self.result.row_count == 8

    def test_domain_detected_as_equipment(self):
        assert self.result.domain_hint == "equipment"

    def test_title_case_headers(self):
        """Sealogical uses 'Equipment Name' style headers."""
        col_names = [c.source_name for c in self.result.columns]
        assert "Equipment Name" in col_names
        assert "Serial Number" in col_names

    def test_date_format_dd_mm_yyyy(self):
        """Sealogical uses DD/MM/YYYY dates."""
        assert self.result.date_format_detected == "DD/MM/YYYY", \
            f"Expected DD/MM/YYYY, got {self.result.date_format_detected}"

    def test_first_row_content_correct(self):
        """Verify actual data, not just row count."""
        first = self.result.rows[0]
        assert first["Equipment Name"] == "Main Engine Port"
        assert first["Manufacturer"] == "MTU"


# =============================================================================
# Edge cases
# =============================================================================

class TestEdgeCases:
    """Test parser edge cases."""

    def test_empty_file(self):
        result = parse_csv(b"", "empty.csv")
        assert result.row_count == 0
        assert any(w.severity == "red" for w in result.warnings)

    def test_header_only_file(self):
        raw = b"name,manufacturer,model\n"
        result = parse_csv(raw, "header_only.csv")
        assert result.row_count == 0
        assert len(result.columns) == 3

    def test_bom_stripped(self):
        raw = b"\xef\xbb\xbfname,value\ntest,123\n"
        result = parse_csv(raw, "bom.csv")
        col_names = [c.source_name for c in result.columns]
        assert "name" in col_names, f"BOM not stripped, got {col_names}"


# =============================================================================
# Date format detection unit tests
# =============================================================================

class TestDateFormatDetection:
    def test_iso_dates(self):
        assert detect_date_format(["2025-01-15", "2025-03-20", "2024-12-01"]) == "ISO"

    def test_dd_mmm_yyyy(self):
        assert detect_date_format(["15-JAN-2025", "20-MAR-2025", "01-DEC-2024"]) == "DD-MMM-YYYY"

    def test_dd_mm_yyyy_unambiguous(self):
        # 25 can only be day, not month
        assert detect_date_format(["25/01/2025", "15/03/2025"]) == "DD/MM/YYYY"

    def test_mm_dd_yyyy_unambiguous(self):
        # 25 in second position can only be day
        assert detect_date_format(["01/25/2025", "03/15/2025"]) == "MM/DD/YYYY"

    def test_ambiguous_dates(self):
        # 01/02/2025 — could be Jan 2 or Feb 1
        assert detect_date_format(["01/02/2025", "03/04/2025"]) == "ambiguous"

    def test_no_dates(self):
        assert detect_date_format(["hello", "world"]) is None

    def test_empty_list(self):
        assert detect_date_format([]) is None
