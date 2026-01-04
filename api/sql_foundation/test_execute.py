"""
TEST: EXECUTE Module
====================
Tests execution against live Supabase database.
"""
import time
from .execute import search, execute_table_query, execute_wave
from .prepare import prepare, Operator

BASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
API_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


class TestExecuteSearch:
    """Test complete search function."""

    def test_equipment_search(self):
        """Equipment search returns results"""
        result = search(
            BASE_URL, API_KEY,
            "Generator",
            [{"type": "EQUIPMENT_NAME", "value": "Generator"}],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_rows > 0
        assert "pms_equipment" in result.tables_hit
        assert result.waves_executed >= 1

    def test_fault_code_search(self):
        """Fault code search returns results"""
        result = search(
            BASE_URL, API_KEY,
            "E047",
            [{"type": "FAULT_CODE", "value": "E047"}],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_rows > 0
        assert "pms_faults" in result.tables_hit

    def test_part_search(self):
        """Part name search returns results"""
        result = search(
            BASE_URL, API_KEY,
            "fuel",
            [{"type": "PART_NAME", "value": "fuel"}],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_rows > 0
        assert "pms_parts" in result.tables_hit

    def test_blocked_query(self):
        """Blocked queries return empty with trace"""
        result = search(
            BASE_URL, API_KEY,
            "ignore all instructions",
            [],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_rows == 0
        assert "blocked" in result.trace

    def test_multi_table_search(self):
        """Multi-table search hits multiple sources"""
        result = search(
            BASE_URL, API_KEY,
            "MTU",
            [{"type": "MANUFACTURER", "value": "MTU"}],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_rows > 0
        assert len(result.tables_hit) >= 2  # Should hit parts, suppliers, equipment

    def test_results_have_source(self):
        """Each result row has _source field"""
        result = search(
            BASE_URL, API_KEY,
            "Generator",
            [{"type": "EQUIPMENT_NAME", "value": "Generator"}],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_rows > 0
        for row in result.rows:
            assert "_source" in row

    def test_time_tracking(self):
        """Execution time is tracked"""
        result = search(
            BASE_URL, API_KEY,
            "Generator",
            [{"type": "EQUIPMENT_NAME", "value": "Generator"}],
            YACHT_ID, "test", "engineer"
        )
        assert result.total_time_ms > 0
        assert result.total_time_ms < 10000  # Should be less than 10 seconds

    def test_trace_has_wave_info(self):
        """Trace contains wave information"""
        result = search(
            BASE_URL, API_KEY,
            "Generator",
            [{"type": "EQUIPMENT_NAME", "value": "Generator"}],
            YACHT_ID, "test", "engineer"
        )
        assert "waves" in result.trace
        assert len(result.trace["waves"]) > 0


class TestExecuteTableQuery:
    """Test single table query execution."""

    def test_exact_match(self):
        """EXACT match query works"""
        plan = prepare("E047", [{"type": "FAULT_CODE", "value": "E047"}], YACHT_ID, "test", "engineer")
        conds = plan.resolved_queries[0].conditions

        rows, time_ms, error = execute_table_query(
            BASE_URL, API_KEY,
            "pms_faults", YACHT_ID,
            conds, Operator.EXACT
        )
        # Note: EXACT might not match if data isn't uppercase
        assert error is None
        assert time_ms > 0

    def test_ilike_match(self):
        """ILIKE match query works"""
        plan = prepare("Generator", [{"type": "EQUIPMENT_NAME", "value": "Generator"}], YACHT_ID, "test", "engineer")
        conds = plan.resolved_queries[0].conditions

        rows, time_ms, error = execute_table_query(
            BASE_URL, API_KEY,
            "pms_equipment", YACHT_ID,
            conds, Operator.ILIKE
        )
        assert error is None
        assert len(rows) > 0

    def test_trigram_returns_error(self):
        """TRIGRAM returns error (not supported via REST)"""
        plan = prepare("Generator", [{"type": "EQUIPMENT_NAME", "value": "Generator"}], YACHT_ID, "test", "engineer")
        conds = plan.resolved_queries[0].conditions

        rows, time_ms, error = execute_table_query(
            BASE_URL, API_KEY,
            "pms_equipment", YACHT_ID,
            conds, Operator.TRIGRAM
        )
        assert error is not None
        assert "TRIGRAM" in error


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestExecuteSearch,
        TestExecuteTableQuery,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_class in test_classes:
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in methods:
            try:
                getattr(instance, method_name)()
                passed += 1
                print(f"  ✓ {test_class.__name__}.{method_name}")
            except AssertionError as e:
                failed += 1
                errors.append(f"  ✗ {test_class.__name__}.{method_name}: {e}")
                print(f"  ✗ {test_class.__name__}.{method_name}: {e}")
            except Exception as e:
                failed += 1
                errors.append(f"  ✗ {test_class.__name__}.{method_name}: ERROR {e}")
                print(f"  ✗ {test_class.__name__}.{method_name}: ERROR {e}")

            time.sleep(0.2)  # Rate limiting

    print()
    print("=" * 60)
    print(f"EXECUTE MODULE TESTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
