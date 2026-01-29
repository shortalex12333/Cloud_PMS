"""
Security Metrics Tests
======================

Tests for security metrics collection and logging.
"""

import pytest
from unittest.mock import MagicMock, patch
import logging


class TestSecurityMetricsCounters:
    """Test security counter functions."""

    def test_ownership_check_passed_logs(self, caplog):
        """Test ownership passed metric is logged."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.INFO):
            SecurityMetrics.ownership_check_passed("equipment", "yacht-001-test")

        assert any("security.ownership.passed" in r.message for r in caplog.records)

    def test_ownership_check_failed_logs(self, caplog):
        """Test ownership failed metric is logged."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.INFO):
            SecurityMetrics.ownership_check_failed("equipment", "yacht-001-test")

        assert any("security.ownership.failed" in r.message for r in caplog.records)

    def test_cross_yacht_attempt_logs_warning(self, caplog):
        """Test cross-yacht attempt logs warning."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.WARNING):
            SecurityMetrics.cross_yacht_attempt(
                source_yacht_id="yacht-001-attacker",
                target_yacht_id="yacht-002-victim",
                action="read_equipment",
            )

        # Should have both metric and warning
        assert any("cross_yacht" in r.message.lower() for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_incident_mode_activated_logs_warning(self, caplog):
        """Test incident mode activation logs warning."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.WARNING):
            SecurityMetrics.incident_mode_activated("Security breach detected")

        assert any("ACTIVATED" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_audit_write_failure_logs_error(self, caplog):
        """Test audit write failure logs error."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.ERROR):
            SecurityMetrics.audit_write_failure(
                action="create_fault",
                yacht_id="yacht-001-test",
                error="connection_timeout",
            )

        assert any("FAILED" in r.message for r in caplog.records)
        assert any(r.levelno == logging.ERROR for r in caplog.records)

    def test_sql_injection_attempt_logs_warning(self, caplog):
        """Test SQL injection attempt logs warning."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.WARNING):
            SecurityMetrics.sql_injection_attempt("entity_id", "yacht-001-test")

        assert any("sql_injection" in r.message.lower() for r in caplog.records)

    def test_unsecured_handler_logs_critical(self, caplog):
        """Test unsecured handler logs critical."""
        from utils.security_metrics import SecurityMetrics

        with caplog.at_level(logging.CRITICAL):
            SecurityMetrics.unsecured_handler_detected("dangerous_handler")

        assert any("unsecured" in r.message.lower() for r in caplog.records)
        assert any(r.levelno == logging.CRITICAL for r in caplog.records)


class TestSecurityMetricsYachtIdTruncation:
    """Test that yacht IDs are properly truncated in metrics."""

    def test_yacht_id_truncated_in_tags(self, caplog):
        """Yacht IDs should be truncated to first 8 chars in metrics."""
        from utils.security_metrics import SecurityMetrics

        full_yacht_id = "yacht-001-full-uuid-here-very-long"

        with caplog.at_level(logging.INFO):
            SecurityMetrics.ownership_check_passed("equipment", full_yacht_id)

        # Check that full yacht ID is NOT in logs (truncated for privacy)
        for record in caplog.records:
            if hasattr(record, 'metric_tags'):
                yacht_tag = record.metric_tags.get('yacht_id', '')
                assert len(yacht_tag) <= 8
                assert full_yacht_id not in str(record)


class TestSecurityMetricsBackend:
    """Test metrics backend interface."""

    def test_set_metrics_backend(self):
        """Test backend can be swapped."""
        from utils.security_metrics import MetricsBackend, set_metrics_backend

        mock_backend = MagicMock(spec=MetricsBackend)
        set_metrics_backend(mock_backend)

        from utils.security_metrics import SecurityMetrics
        SecurityMetrics.ownership_check_passed("test", "yacht-001")

        # Mock backend should have been called
        assert mock_backend.increment.called

        # Reset to default
        set_metrics_backend(MetricsBackend())

    def test_increment_includes_tags(self, caplog):
        """Test that increment includes tags in log."""
        from utils.security_metrics import MetricsBackend

        backend = MetricsBackend()

        with caplog.at_level(logging.INFO):
            backend.increment(
                "test.metric",
                value=5,
                tags={"tag1": "value1", "tag2": "value2"}
            )

        assert any("test.metric" in r.message for r in caplog.records)

    def test_timing_metric(self, caplog):
        """Test timing metric logs correctly."""
        from utils.security_metrics import MetricsBackend

        backend = MetricsBackend()

        with caplog.at_level(logging.INFO):
            backend.timing("test.timing", 123.45, tags={"operation": "test"})

        assert any("test.timing" in r.message for r in caplog.records)

    def test_gauge_metric(self, caplog):
        """Test gauge metric logs correctly."""
        from utils.security_metrics import MetricsBackend

        backend = MetricsBackend()

        with caplog.at_level(logging.INFO):
            backend.gauge("test.gauge", 42.0, tags={"component": "test"})

        assert any("test.gauge" in r.message for r in caplog.records)


class TestTimedSecurityOperationDecorator:
    """Test the timing decorator."""

    @pytest.mark.asyncio
    async def test_async_timed_operation_success(self, caplog):
        """Test async timed operation on success."""
        from utils.security_metrics import timed_security_operation

        @timed_security_operation("test_async")
        async def async_operation():
            return "success"

        with caplog.at_level(logging.INFO):
            result = await async_operation()

        assert result == "success"
        assert any("test_async" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_async_timed_operation_failure(self, caplog):
        """Test async timed operation on failure."""
        from utils.security_metrics import timed_security_operation

        @timed_security_operation("test_async_fail")
        async def async_operation():
            raise ValueError("test error")

        with caplog.at_level(logging.INFO):
            with pytest.raises(ValueError):
                await async_operation()

        assert any("test_async_fail" in r.message for r in caplog.records)

    def test_sync_timed_operation_success(self, caplog):
        """Test sync timed operation on success."""
        from utils.security_metrics import timed_security_operation

        @timed_security_operation("test_sync")
        def sync_operation():
            return "success"

        with caplog.at_level(logging.INFO):
            result = sync_operation()

        assert result == "success"
        assert any("test_sync" in r.message for r in caplog.records)

    def test_sync_timed_operation_failure(self, caplog):
        """Test sync timed operation on failure."""
        from utils.security_metrics import timed_security_operation

        @timed_security_operation("test_sync_fail")
        def sync_operation():
            raise RuntimeError("test error")

        with caplog.at_level(logging.INFO):
            with pytest.raises(RuntimeError):
                sync_operation()

        assert any("test_sync_fail" in r.message for r in caplog.records)


class TestAllSecurityMetricsMethods:
    """Test that all SecurityMetrics methods execute without error."""

    def test_all_counters_callable(self):
        """All counter methods should be callable without error."""
        from utils.security_metrics import SecurityMetrics

        # Test all methods with dummy data
        methods_and_args = [
            ("ownership_check_passed", ("equipment", "yacht-001")),
            ("ownership_check_failed", ("equipment", "yacht-001")),
            ("cross_yacht_attempt", ("yacht-001", "yacht-002", "test_action")),
            ("role_check_passed", ("captain", "read", "yacht-001")),
            ("role_check_failed", ("crew", "captain", "admin_action", "yacht-001")),
            ("incident_mode_block", ("streaming", "yacht-001")),
            ("incident_mode_activated", ("test_reason",)),
            ("incident_mode_deactivated", ()),
            ("yacht_freeze_block", ("write", "yacht-001")),
            ("yacht_frozen", ("yacht-001", "test_reason")),
            ("yacht_unfrozen", ("yacht-001",)),
            ("signed_url_generated", ("download", "yacht-001")),
            ("signed_url_blocked", ("incident_mode", "yacht-001")),
            ("path_traversal_attempt", ("../../../etc/passwd", "yacht-001")),
            ("auth_success", ("user-001", "yacht-001")),
            ("auth_failure", ("invalid_token",)),
            ("jwt_expired", ()),
            ("jwt_invalid", ("malformed",)),
            ("rate_limit_exceeded", ("/api/search", "yacht-001", "user-001")),
            ("streaming_rate_limit", ("yacht-001", "user-001")),
            ("streaming_cancelled", ("yacht-001", "user_abort")),
            ("audit_write_success", ("create_fault", "yacht-001")),
            ("audit_write_failure", ("create_fault", "yacht-001", "db_error")),
            ("sql_injection_attempt", ("entity_id", "yacht-001")),
            ("unsecured_handler_detected", ("test_handler",)),
            ("handler_execution_denied", ("test_handler", "role_denied", "yacht-001")),
        ]

        for method_name, args in methods_and_args:
            method = getattr(SecurityMetrics, method_name)
            # Should not raise
            method(*args)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
