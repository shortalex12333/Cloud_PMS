"""
Tests for XLSX, SQL, and ZIP parsers.
Verification-integrity compliant: checks CONTENT, not just existence.
"""

import os
import sys
import io
import zipfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "import_samples")


def load_fixture(name: str) -> bytes:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "rb") as f:
        return f.read()


# =============================================================================
# SQL Parser Tests
# =============================================================================

class TestSqlParser:
    """Test SQL dump parsing (IDEA Yacht format)."""

    def setup_method(self):
        from parsers.sql_parser import parse_sql
        raw = load_fixture("idea_yacht_equipment.sql")
        self.results = parse_sql(raw, "idea_yacht_equipment.sql")

    def test_returns_parse_results(self):
        assert len(self.results) >= 1

    def test_row_count_is_5(self):
        """SQL fixture has 5 INSERT statements."""
        result = self.results[0]
        assert result.row_count == 5, f"Expected 5 rows, got {result.row_count}"

    def test_columns_detected(self):
        result = self.results[0]
        col_names = [c.source_name for c in result.columns]
        assert "EQUIP_NAME" in col_names
        assert "MAKER" in col_names
        assert "SERIAL_NO" in col_names

    def test_first_row_content(self):
        result = self.results[0]
        first = result.rows[0]
        assert first["EQUIP_NAME"] == "Main Engine Port"
        assert first["MAKER"] == "MTU"
        assert first["SERIAL_NO"] == "MTU-2019-7834"

    def test_domain_detected(self):
        result = self.results[0]
        assert result.domain_hint == "equipment"

    def test_sample_values_populated(self):
        result = self.results[0]
        name_col = next(c for c in result.columns if c.source_name == "EQUIP_NAME")
        assert len(name_col.sample_values) >= 3
        assert "Main Engine Port" in name_col.sample_values


class TestSqlParserCopyFormat:
    """Test pg_dump COPY ... FROM stdin format."""

    def test_copy_block_parsing(self):
        from parsers.sql_parser import parse_sql
        sql = """COPY equipment (equip_id, equip_name, maker) FROM stdin;
1001\tMain Engine Port\tMTU
1002\tMain Engine Starboard\tMTU
1003\tLO Pump\tAlfa Laval
\\.
"""
        results = parse_sql(sql.encode("utf-8"), "copy_test.sql")
        assert len(results) == 1
        assert results[0].row_count == 3
        assert results[0].rows[0]["equip_name"] == "Main Engine Port"
        assert results[0].rows[2]["maker"] == "Alfa Laval"


# =============================================================================
# ZIP Handler Tests
# =============================================================================

class TestZipHandler:
    """Test ZIP extraction and file routing."""

    def _make_zip(self, files: dict) -> bytes:
        """Create a ZIP in memory from {filename: content} dict."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, content in files.items():
                if isinstance(content, str):
                    content = content.encode("utf-8")
                zf.writestr(name, content)
        return buf.getvalue()

    def test_csv_files_routed_to_data(self):
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "equipment.csv": load_fixture("seahub_equipment.csv"),
        })
        result = extract_zip(zip_data, "test.zip")
        assert len(result["data_files"]) == 1
        assert result["data_files"][0][0] == "equipment.csv"
        assert result["data_files"][0][1] == ".csv"

    def test_pdf_files_routed_to_documents(self):
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "manuals/Engine_Manual.pdf": b"%PDF-1.4 fake content",
        })
        result = extract_zip(zip_data, "test.zip")
        assert len(result["documents"]) == 1
        assert result["documents"][0].filename == "Engine_Manual.pdf"
        assert result["documents"][0].content_type == "application/pdf"
        assert result["documents"][0].domain_hint == "manuals"

    def test_folder_domain_hints(self):
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "certificates/Class_Certificate.pdf": b"%PDF fake",
            "photos/fault_evidence.jpg": b"\xff\xd8\xff fake jpg",
            "drawings/engine_schematic.png": b"\x89PNG fake",
        })
        result = extract_zip(zip_data, "test.zip")
        docs = {d.filename: d for d in result["documents"]}
        assert docs["Class_Certificate.pdf"].domain_hint == "certificates"
        assert docs["fault_evidence.jpg"].domain_hint == "photos"
        assert docs["engine_schematic.png"].domain_hint == "drawings"

    def test_macos_resources_skipped(self):
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "__MACOSX/._equipment.csv": b"mac resource fork",
            ".DS_Store": b"ds store",
            "equipment.csv": load_fixture("seahub_equipment.csv"),
        })
        result = extract_zip(zip_data, "test.zip")
        assert len(result["data_files"]) == 1  # only the real CSV
        assert len(result["documents"]) == 0
        assert len(result["unclassified"]) == 0

    def test_unknown_files_unclassified(self):
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "readme.txt": b"some readme",
            "config.ini": b"[settings]\nkey=value",
        })
        result = extract_zip(zip_data, "test.zip")
        assert len(result["unclassified"]) == 2

    def test_mixed_zip_full_parse(self):
        """Test ZIP with data files + documents — full parse pipeline."""
        from parsers.zip_handler import parse_zip
        zip_data = self._make_zip({
            "Equipment/equipment.csv": load_fixture("seahub_equipment.csv"),
            "Certificates/class_cert.pdf": b"%PDF fake cert",
            "manuals/engine_manual.pdf": b"%PDF fake manual",
        })
        result = parse_zip(zip_data, "mixed.zip", source="seahub")
        assert len(result["parse_results"]) == 1  # one CSV parsed
        assert result["parse_results"][0].domain_hint == "equipment"
        assert result["parse_results"][0].row_count == 8
        assert len(result["documents"]) == 2  # two PDFs

    def test_invalid_zip(self):
        from parsers.zip_handler import extract_zip
        result = extract_zip(b"not a zip file", "bad.zip")
        assert len(result["warnings"]) == 1
        assert result["warnings"][0].severity == "red"


# =============================================================================
# Date Normalizer Tests
# =============================================================================

class TestDateNormalizer:
    """Test date normalization across all PMS formats."""

    def test_iso_passthrough(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("2025-01-15") == "2025-01-15"

    def test_iso_with_time(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("2025-01-15T10:30:00Z") == "2025-01-15"

    def test_dd_mmm_yyyy(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("15-JAN-2025") == "2025-01-15"
        assert normalize_date("01-DEC-2024") == "2024-12-01"

    def test_dd_mm_yyyy(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("25/03/2025", "DD/MM/YYYY") == "2025-03-25"

    def test_mm_dd_yyyy(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("03/25/2025", "MM/DD/YYYY") == "2025-03-25"

    def test_excel_serial(self):
        from mappers.date_normalizer import normalize_date
        # 45307 = 2024-01-15 in Excel serial
        result = normalize_date("45307")
        assert result == "2024-01-15", f"Expected 2024-01-15, got {result}"

    def test_empty_string(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("") is None
        assert normalize_date(None) is None

    def test_invalid_date(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("not a date") is None


# =============================================================================
# Status Mapper Tests
# =============================================================================

class TestStatusMapper:
    """Test status value mapping across PMS sources."""

    def test_idea_equipment_active(self):
        from mappers.status_mapper import map_status
        assert map_status("ACTIVE", "equipment", "idea_yacht") == "operational"

    def test_idea_wo_completed(self):
        from mappers.status_mapper import map_status
        assert map_status("COMPLETED", "work_orders", "idea_yacht") == "completed"

    def test_idea_wo_open_maps_to_planned(self):
        """Real DB enum: planned, in_progress, completed, deferred, cancelled, closed. No 'open'."""
        from mappers.status_mapper import map_status
        assert map_status("OPEN", "work_orders", "idea_yacht") == "planned"

    def test_idea_wo_priority_maps_to_enum(self):
        """Real DB enum: routine, important, critical, emergency. No 'high', 'normal', 'low'."""
        from mappers.status_mapper import map_status
        assert map_status("HIGH", "work_orders_priority", "idea_yacht") == "important"
        assert map_status("NORMAL", "work_orders_priority", "idea_yacht") == "routine"
        assert map_status("CRITICAL", "work_orders_priority", "idea_yacht") == "critical"

    def test_idea_wo_type_maps_to_enum(self):
        """Real DB enum: scheduled, corrective, unplanned, preventive."""
        from mappers.status_mapper import map_status
        assert map_status("PM", "work_orders_type", "idea_yacht") == "scheduled"
        assert map_status("CM", "work_orders_type", "idea_yacht") == "corrective"

    def test_seahub_wo_open_maps_to_planned(self):
        from mappers.status_mapper import map_status
        assert map_status("open", "work_orders", "seahub") == "planned"

    def test_sealogical_equipment(self):
        from mappers.status_mapper import map_status
        assert map_status("Active", "equipment", "sealogical") == "operational"

    def test_case_insensitive(self):
        from mappers.status_mapper import map_status
        assert map_status("active", "equipment", "idea_yacht") == "operational"

    def test_already_canonical(self):
        from mappers.status_mapper import map_status
        assert map_status("operational", "equipment", "generic") == "operational"

    def test_unknown_status_lowercased(self):
        from mappers.status_mapper import map_status
        result = map_status("SOME_WEIRD_STATUS", "equipment", "idea_yacht")
        assert result == "some_weird_status"


# =============================================================================
# Column Matcher Tests
# =============================================================================

class TestColumnMatcher:
    """Test column name matching."""

    def test_idea_equipment_profile(self):
        from mappers.column_matcher import match_columns
        columns = ["EQUIP_NAME", "MAKER", "MODEL", "SERIAL_NO", "LOCATION"]
        mappings = match_columns(columns, "equipment", "idea_yacht")
        mapping_dict = {m.source_name: m for m in mappings}

        assert mapping_dict["EQUIP_NAME"].suggested_target == "name"
        assert mapping_dict["EQUIP_NAME"].confidence == 1.0
        assert mapping_dict["MAKER"].suggested_target == "manufacturer"
        assert mapping_dict["SERIAL_NO"].suggested_target == "serial_number"

    def test_seahub_defects_profile(self):
        from mappers.column_matcher import match_columns
        columns = ["defect_id", "title", "description", "reported_by", "closed_date"]
        mappings = match_columns(columns, "faults", "seahub")
        mapping_dict = {m.source_name: m for m in mappings}

        assert mapping_dict["defect_id"].suggested_target == "source_id"
        assert mapping_dict["title"].suggested_target == "title"
        assert mapping_dict["reported_by"].suggested_target == "source_reported_by"
        assert mapping_dict["closed_date"].suggested_target == "resolved_at"

    def test_skip_columns(self):
        from mappers.column_matcher import match_columns
        columns = ["PARENT_EQUIP_ID", "CREATED_DATE"]
        mappings = match_columns(columns, "equipment", "idea_yacht")
        for m in mappings:
            assert m.action == "skip"
            assert m.confidence == 0.0

    def test_generic_fuzzy_matching(self):
        from mappers.column_matcher import match_columns
        columns = ["equipment_name", "serial_num", "mfg"]
        vocab = ["name", "serial_number", "manufacturer", "model", "location"]
        mappings = match_columns(columns, "equipment", "generic", vocabulary=vocab)
        # At minimum, equipment_name should match "name"
        name_mapping = next(m for m in mappings if m.source_name == "equipment_name")
        assert name_mapping.suggested_target is not None
        assert name_mapping.confidence > 0.5
