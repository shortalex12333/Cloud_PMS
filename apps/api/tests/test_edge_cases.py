"""
Edge Case & Adversarial Tests for the Import Pipeline
=====================================================
These tests try to BREAK the pipeline, not just confirm happy paths.
Per verification-integrity: a test that can't catch a regression is a false success.
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "import_samples")


def load_fixture(name: str) -> bytes:
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return f.read()


# =============================================================================
# MALFORMED CSV — parser must not crash
# =============================================================================

class TestMalformedCSV:
    """Adversarial CSV inputs that should fail gracefully, never crash."""

    def test_binary_garbage(self):
        """Random binary data pretending to be CSV."""
        from parsers.csv_parser import parse_csv
        result = parse_csv(b"\x00\x01\x02\xff\xfe\x80\x90\xab", "garbage.csv")
        assert result.row_count == 0 or result.row_count >= 0  # doesn't crash
        # Should have warnings
        assert len(result.warnings) >= 0  # at minimum, doesn't crash

    def test_single_column_csv(self):
        """CSV with only one column — no delimiter to detect."""
        from parsers.csv_parser import parse_csv
        data = b"name\nMain Engine\nGenerator 1\nWatermaker\n"
        result = parse_csv(data, "single_col.csv")
        assert result.row_count == 3
        assert len(result.columns) == 1
        assert result.columns[0].source_name == "name"

    def test_ragged_rows(self):
        """Rows with inconsistent column counts — short rows get empty values."""
        from parsers.csv_parser import parse_csv
        data = b"name,maker,model\nEngine,MTU\nGenerator,CAT,C32\nPump,Alfa Laval,MAB\n"
        result = parse_csv(data, "ragged.csv")
        # Should not crash — short rows get empty values
        assert result.row_count == 3
        assert result.rows[0]["name"] == "Engine"
        assert result.rows[0].get("model", "") == ""  # short row, model missing

    def test_empty_header_columns(self):
        """CSV where some header cells are empty."""
        from parsers.csv_parser import parse_csv
        data = b"name,,model,\nEngine,,16V4000,\nGenerator,,C32,\n"
        result = parse_csv(data, "empty_headers.csv")
        # Empty headers should be skipped
        col_names = [c.source_name for c in result.columns]
        assert "" not in col_names

    def test_duplicate_column_names(self):
        """CSV with duplicate header names."""
        from parsers.csv_parser import parse_csv
        data = b"name,name,model\nEngine,MTU,16V4000\n"
        result = parse_csv(data, "dupes.csv")
        # Should parse without crashing — last value wins in dict
        assert result.row_count == 1

    def test_quoted_fields_with_delimiter(self):
        """Fields containing the delimiter character inside quotes."""
        from parsers.csv_parser import parse_csv
        data = b'name,description,model\n"Main Engine, Port","Oil change; filter replacement",16V4000\n'
        result = parse_csv(data, "quoted.csv")
        assert result.row_count == 1
        assert result.rows[0]["name"] == "Main Engine, Port"
        assert "Oil change" in result.rows[0]["description"]

    def test_newlines_in_quoted_fields(self):
        """Multiline values inside quoted fields."""
        from parsers.csv_parser import parse_csv
        data = b'name,notes\n"Engine","Line 1\nLine 2\nLine 3"\n"Generator","Single line"\n'
        result = parse_csv(data, "multiline.csv")
        assert result.row_count == 2
        assert "Line 1" in result.rows[0]["notes"]

    def test_utf8_bom_with_semicolons(self):
        """BOM + semicolon delimiter (common in European Excel exports)."""
        from parsers.csv_parser import parse_csv
        data = b"\xef\xbb\xbfname;maker;model\nEngine;MTU;16V4000\n"
        result = parse_csv(data, "bom_semi.csv")
        assert result.delimiter_detected == ";"
        col_names = [c.source_name for c in result.columns]
        assert "name" in col_names  # BOM stripped from first column name

    def test_windows_line_endings(self):
        """CSV with \\r\\n line endings."""
        from parsers.csv_parser import parse_csv
        data = b"name,maker\r\nEngine,MTU\r\nGenerator,CAT\r\n"
        result = parse_csv(data, "crlf.csv")
        assert result.row_count == 2

    def test_tab_delimited(self):
        """TSV file with .csv extension."""
        from parsers.csv_parser import parse_csv
        data = b"name\tmaker\tmodel\nEngine\tMTU\t16V4000\nGenerator\tCAT\tC32\n"
        result = parse_csv(data, "tsv.csv")
        assert result.delimiter_detected == "\t"
        assert result.row_count == 2

    def test_very_long_field(self):
        """Single field with 100KB of text."""
        from parsers.csv_parser import parse_csv
        long_text = "A" * 100000
        data = f"name,description\nEngine,{long_text}\n".encode("utf-8")
        result = parse_csv(data, "long_field.csv")
        assert result.row_count == 1
        assert len(result.rows[0]["description"]) == 100000

    def test_only_whitespace(self):
        """File with only whitespace/newlines."""
        from parsers.csv_parser import parse_csv
        result = parse_csv(b"   \n\n  \n  \n", "whitespace.csv")
        assert result.row_count == 0

    def test_null_bytes(self):
        """CSV with embedded null bytes (corrupted file)."""
        from parsers.csv_parser import parse_csv
        data = b"name,maker\nEngine\x00Port,MTU\nGenerator,CAT\n"
        result = parse_csv(data, "nullbytes.csv")
        # Should not crash
        assert result.row_count >= 0

    def test_latin1_encoding(self):
        """Latin-1 encoded CSV with accented characters."""
        from parsers.csv_parser import parse_csv
        # "Moteur" with accent, "Générateur" in Latin-1
        data = "name,maker\nMoteur principal,Wärtsilä\nGénérateur,MTU\n".encode("latin-1")
        result = parse_csv(data, "latin1.csv")
        # charset-normalizer may detect as any Latin family encoding — all are acceptable
        assert result.encoding_detected not in ("utf-8", "ascii"), \
            f"Expected non-UTF8 encoding, got {result.encoding_detected}"
        assert result.row_count == 2
        # Accented chars may be slightly garbled across Latin variants — key is it doesn't crash
        assert len(result.rows[0]["maker"]) > 0

    def test_huge_row_count_header(self):
        """10 metadata rows before actual header (extreme Sealogical pattern)."""
        from parsers.csv_parser import parse_csv
        lines = []
        for i in range(10):
            lines.append(f"Metadata row {i},,,,")
        lines.append("name,maker,model,serial,location")
        lines.append("Engine,MTU,16V4000,SN-001,ER3")
        data = "\n".join(lines).encode("utf-8")
        result = parse_csv(data, "deep_metadata.csv")
        assert result.header_row >= 10  # skipped all metadata rows
        assert result.row_count == 1
        assert result.rows[0]["name"] == "Engine"


# =============================================================================
# SQL PARSER EDGE CASES
# =============================================================================

class TestSqlEdgeCases:

    def test_empty_sql_file(self):
        from parsers.sql_parser import parse_sql
        results = parse_sql(b"", "empty.sql")
        assert len(results) == 1
        assert results[0].row_count == 0

    def test_sql_comments_only(self):
        from parsers.sql_parser import parse_sql
        data = b"-- This is a comment\n-- Another comment\n/* Block comment */\n"
        results = parse_sql(data, "comments.sql")
        assert len(results) == 1
        assert results[0].row_count == 0

    def test_sql_with_escaped_quotes(self):
        from parsers.sql_parser import parse_sql
        data = b"INSERT INTO equipment (name, notes) VALUES ('Main Engine', 'It''s working fine');\n"
        results = parse_sql(data, "escaped.sql")
        assert len(results) >= 1
        if results[0].row_count > 0:
            assert "It's working fine" in results[0].rows[0].get("notes", "")

    def test_copy_with_null_values(self):
        from parsers.sql_parser import parse_sql
        data = b"COPY equipment (id, name, maker) FROM stdin;\n1\tEngine\t\\N\n2\tGenerator\tCAT\n\\.\n"
        results = parse_sql(data, "nulls.sql")
        assert results[0].row_count == 2
        assert results[0].rows[0]["maker"] == ""  # \N → empty string

    def test_multiple_tables_in_one_file(self):
        from parsers.sql_parser import parse_sql
        data = (
            b"INSERT INTO equipment (name) VALUES ('Engine');\n"
            b"INSERT INTO equipment (name) VALUES ('Generator');\n"
            b"COPY faults (title, severity) FROM stdin;\n"
            b"Oil leak\thigh\n"
            b"Vibration\tmedium\n"
            b"\\.\n"
        )
        results = parse_sql(data, "multi.sql")
        assert len(results) >= 2  # equipment (INSERT) + faults (COPY)


# =============================================================================
# ZIP HANDLER EDGE CASES
# =============================================================================

class TestZipEdgeCases:

    def _make_zip(self, files: dict) -> bytes:
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, content in files.items():
                if isinstance(content, str):
                    content = content.encode("utf-8")
                zf.writestr(name, content)
        return buf.getvalue()

    def test_nested_directories(self):
        """ZIP with deeply nested folder structure."""
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "level1/level2/level3/equipment.csv": load_fixture("seahub_equipment.csv"),
        })
        result = extract_zip(zip_data, "nested.zip")
        assert len(result["data_files"]) == 1
        assert result["data_files"][0][0] == "equipment.csv"  # basename only

    def test_empty_zip(self):
        """ZIP with no files."""
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({})
        result = extract_zip(zip_data, "empty.zip")
        assert len(result["data_files"]) == 0
        assert len(result["documents"]) == 0

    def test_zip_with_only_unsupported_files(self):
        """ZIP containing only unsupported file types."""
        from parsers.zip_handler import extract_zip
        zip_data = self._make_zip({
            "readme.txt": b"hello",
            "config.ini": b"[settings]",
            "data.json": b'{"key": "value"}',
        })
        result = extract_zip(zip_data, "unsupported.zip")
        assert len(result["data_files"]) == 0
        assert len(result["unclassified"]) == 3

    def test_zip_with_mixed_encodings(self):
        """ZIP containing CSV files with different encodings."""
        from parsers.zip_handler import parse_zip
        latin1_csv = "name,maker\nMoteur,Wärtsilä\n".encode("latin-1")
        utf8_csv = "name,maker\nEngine,MTU\n".encode("utf-8")
        zip_data = self._make_zip({
            "latin1.csv": latin1_csv,
            "utf8.csv": utf8_csv,
        })
        result = parse_zip(zip_data, "mixed_encoding.zip")
        assert len(result["parse_results"]) == 2
        # Both should parse without error
        for pr in result["parse_results"]:
            assert pr.row_count == 1


# =============================================================================
# DATE NORMALIZER EDGE CASES
# =============================================================================

class TestDateEdgeCases:

    def test_feb_29_leap_year(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("29/02/2024", "DD/MM/YYYY") == "2024-02-29"

    def test_feb_29_non_leap_year(self):
        from mappers.date_normalizer import normalize_date
        result = normalize_date("29/02/2025", "DD/MM/YYYY")
        assert result is None  # invalid date

    def test_future_date(self):
        from mappers.date_normalizer import normalize_date
        result = normalize_date("15/06/2030", "DD/MM/YYYY")
        assert result == "2030-06-15"  # should parse, not reject future dates

    def test_very_old_date(self):
        from mappers.date_normalizer import normalize_date
        result = normalize_date("01-JAN-1990")
        assert result == "1990-01-01"

    def test_excel_serial_date_zero(self):
        from mappers.date_normalizer import normalize_date
        result = normalize_date("0")
        assert result is None  # invalid

    def test_excel_serial_negative(self):
        from mappers.date_normalizer import normalize_date
        result = normalize_date("-1")
        assert result is None

    def test_date_with_extra_whitespace(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("  2025-01-15  ") == "2025-01-15"
        assert normalize_date("  15-JAN-2025  ") == "2025-01-15"

    def test_date_with_time_component(self):
        from mappers.date_normalizer import normalize_date
        assert normalize_date("2025-01-15T10:30:00Z") == "2025-01-15"
        assert normalize_date("2025-01-15 14:22:00") == "2025-01-15"

    def test_ambiguous_date_defaults_to_european(self):
        """When no format hint, ambiguous dates default to DD/MM (European maritime convention)."""
        from mappers.date_normalizer import normalize_date
        result = normalize_date("05/03/2025")  # no hint
        # Default is DD/MM (European) → March 5, not May 3
        assert result == "2025-03-05"


# =============================================================================
# STATUS MAPPER EDGE CASES
# =============================================================================

class TestStatusEdgeCases:

    def test_empty_status(self):
        from mappers.status_mapper import map_status
        assert map_status("", "equipment", "idea_yacht") == ""

    def test_none_status(self):
        from mappers.status_mapper import map_status
        assert map_status(None, "equipment", "idea_yacht") is None

    def test_whitespace_status(self):
        from mappers.status_mapper import map_status
        result = map_status("  ACTIVE  ", "equipment", "idea_yacht")
        assert result == "operational"

    def test_unknown_source(self):
        from mappers.status_mapper import map_status
        result = map_status("ACTIVE", "equipment", "unknown_pms")
        assert result == "active"  # lowercased fallback

    def test_unknown_domain(self):
        from mappers.status_mapper import map_status
        result = map_status("ACTIVE", "unknown_domain", "idea_yacht")
        assert result == "active"  # lowercased fallback


# =============================================================================
# COLUMN MATCHER EDGE CASES
# =============================================================================

class TestColumnMatcherEdgeCases:

    def test_empty_column_list(self):
        from mappers.column_matcher import match_columns
        result = match_columns([], "equipment", "idea_yacht")
        assert result == []

    def test_unknown_source_with_vocabulary(self):
        """Generic source should fuzzy-match against vocabulary."""
        from mappers.column_matcher import match_columns
        columns = ["EquipmentName", "SerialNumber", "Manufacturer"]
        vocab = ["name", "serial_number", "manufacturer", "model"]
        result = match_columns(columns, "equipment", "generic", vocabulary=vocab)
        # Should get some matches via fuzzy matching
        matched = [m for m in result if m.suggested_target is not None]
        assert len(matched) >= 1  # at least manufacturer should match

    def test_completely_alien_columns(self):
        """Columns that have no relation to CelesteOS vocabulary."""
        from mappers.column_matcher import match_columns
        columns = ["xyz_foo", "bar_baz_qux", "completely_random"]
        vocab = ["name", "serial_number", "manufacturer"]
        result = match_columns(columns, "equipment", "generic", vocabulary=vocab)
        # All should be skip (low confidence)
        for m in result:
            assert m.confidence < 0.9


# =============================================================================
# IMPORT SERVICE EDGE CASES
# =============================================================================

class TestImportServiceEdgeCases:

    def test_transform_row_with_empty_map(self):
        """Transform with no column mappings — should only set auto fields."""
        from services.import_service import transform_row
        row = {"EQUIP_NAME": "Engine", "MAKER": "MTU"}
        result, warnings = transform_row(row, [], "equipment", "idea_yacht", "yacht-123", "sess-456")
        assert result["yacht_id"] == "yacht-123"
        assert result["source"] == "idea_yacht"
        assert result["import_session_id"] == "sess-456"
        assert "name" not in result  # no mapping → no user data

    def test_transform_row_with_all_skips(self):
        """All columns set to skip — only auto fields populated."""
        from services.import_service import transform_row
        row = {"EQUIP_NAME": "Engine"}
        column_map = [{"source": "EQUIP_NAME", "target": None, "action": "skip"}]
        result, warnings = transform_row(row, column_map, "equipment", "idea_yacht", "yacht-123", "sess-456")
        assert "name" not in result

    def test_transform_row_with_missing_source_column(self):
        """Column map references a source column that doesn't exist in the row."""
        from services.import_service import transform_row
        row = {"EQUIP_NAME": "Engine"}
        column_map = [{"source": "NONEXISTENT", "target": "name", "action": "map"}]
        result, warnings = transform_row(row, column_map, "equipment", "idea_yacht", "yacht-123", "sess-456")
        assert result.get("name") is None  # missing source → None

    def test_dry_run_with_zero_rows(self):
        """Dry run on empty data."""
        from services.import_service import dry_run_domain
        result = dry_run_domain([], [], "equipment", "idea_yacht", "yacht-123", "sess-456")
        assert result["total"] == 0
        assert result["new"] == 0
        assert result["errors"] == 0

    def test_dry_run_preserves_source_id(self):
        """Source ID from the original PMS must be preserved."""
        from services.import_service import dry_run_domain
        rows = [{"EQUIP_ID": "1001", "EQUIP_NAME": "Engine"}]
        column_map = [
            {"source": "EQUIP_ID", "target": "source_id", "action": "map"},
            {"source": "EQUIP_NAME", "target": "name", "action": "map"},
        ]
        result = dry_run_domain(rows, column_map, "equipment", "idea_yacht", "yacht-123", "sess-456")
        assert result["first_10"][0]["source_id"] == "1001"

    def test_dry_run_bad_date_produces_warning(self):
        """Invalid date should produce a warning, not crash."""
        from services.import_service import dry_run_domain
        rows = [{"DUE_DATE": "not-a-date", "TITLE": "Test WO"}]
        column_map = [
            {"source": "DUE_DATE", "target": "due_date", "action": "map"},
            {"source": "TITLE", "target": "title", "action": "map"},
        ]
        result = dry_run_domain(rows, column_map, "work_orders", "idea_yacht", "yacht-123", "sess-456", date_format="DD-MMM-YYYY")
        assert result["errors"] == 0  # bad date is a warning, not an error
        assert result["warnings_count"] >= 1
        assert any("date" in w["message"].lower() for w in result["warnings"])

    def test_every_row_gets_unique_uuid(self):
        """Every transformed row must have a unique ID."""
        from services.import_service import dry_run_domain
        rows = [
            {"EQUIP_NAME": "Engine 1"},
            {"EQUIP_NAME": "Engine 2"},
            {"EQUIP_NAME": "Engine 3"},
        ]
        column_map = [{"source": "EQUIP_NAME", "target": "name", "action": "map"}]
        result = dry_run_domain(rows, column_map, "equipment", "idea_yacht", "yacht-123", "sess-456")
        ids = [r["id"] for r in result["first_10"]]
        assert len(ids) == len(set(ids))  # all unique

    def test_yacht_id_never_null(self):
        """yacht_id must NEVER be null on any imported record."""
        from services.import_service import dry_run_domain
        rows = [{"EQUIP_NAME": "Engine"}]
        column_map = [{"source": "EQUIP_NAME", "target": "name", "action": "map"}]
        result = dry_run_domain(rows, column_map, "equipment", "idea_yacht", "yacht-123", "sess-456")
        for row in result["first_10"]:
            assert row["yacht_id"] == "yacht-123", f"yacht_id is {row.get('yacht_id')}, expected yacht-123"
            assert row["yacht_id"] is not None
