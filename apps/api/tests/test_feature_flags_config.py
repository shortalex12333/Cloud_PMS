"""
Feature Flags Configuration Tests
==================================

Tests for environment-based feature flag behavior.

Security invariants tested:
1. Disabled features return 404 (not 403, to prevent enumeration)
2. Enabled features return 200 for authorized roles
3. Feature flags default to DISABLED (deny-by-default)
4. Config validation fails fast on missing critical envs
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# =============================================================================
# CONFIG MODULE TESTS
# =============================================================================

class TestEnvironmentParsing:
    """Test environment variable parsing."""

    def test_bool_env_true_values(self):
        """Test boolean parsing for true values."""
        from config.env import _bool_env

        for value in ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]:
            with patch.dict(os.environ, {"TEST_VAR": value}):
                # Need to reimport to get fresh evaluation
                assert _bool_env("TEST_VAR", False) is True

    def test_bool_env_false_values(self):
        """Test boolean parsing for false values."""
        from config.env import _bool_env

        for value in ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]:
            with patch.dict(os.environ, {"TEST_VAR": value}):
                assert _bool_env("TEST_VAR", True) is False

    def test_bool_env_default(self):
        """Test boolean default when not set."""
        from config.env import _bool_env

        # Ensure var is not set
        if "TEST_UNSET_VAR" in os.environ:
            del os.environ["TEST_UNSET_VAR"]

        assert _bool_env("TEST_UNSET_VAR", False) is False
        assert _bool_env("TEST_UNSET_VAR", True) is True

    def test_int_env_valid(self):
        """Test integer parsing for valid values."""
        from config.env import _int_env

        with patch.dict(os.environ, {"TEST_INT": "42"}):
            assert _int_env("TEST_INT", 0) == 42

    def test_int_env_invalid(self):
        """Test integer parsing falls back on invalid."""
        from config.env import _int_env

        with patch.dict(os.environ, {"TEST_INT": "not-a-number"}):
            assert _int_env("TEST_INT", 99) == 99

    def test_environment_detection(self):
        """Test environment detection from ENVIRONMENT var."""
        from config.env import get_environment, Environment

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert get_environment() == Environment.PRODUCTION

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            assert get_environment() == Environment.STAGING

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert get_environment() == Environment.DEVELOPMENT

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            assert get_environment() == Environment.TEST


class TestSettingsDefaults:
    """Test that settings have secure defaults."""

    def test_email_features_default_disabled(self):
        """All email features should default to disabled."""
        # Clear email env vars
        email_vars = [
            "EMAIL_EVIDENCE_ENABLED", "EMAIL_FOCUS_ENABLED",
            "EMAIL_LINK_ENABLED", "EMAIL_RELATED_ENABLED",
            "EMAIL_RENDER_ENABLED", "EMAIL_SEARCH_ENABLED",
            "EMAIL_SYNC_ENABLED", "EMAIL_THREAD_ENABLED",
            "EMAIL_TRANSPORT_ENABLED",
        ]

        cleared_env = {k: "" for k in email_vars}

        with patch.dict(os.environ, cleared_env, clear=False):
            from config.env import EmailSettings
            settings = EmailSettings()

            assert settings.evidence_enabled is False
            assert settings.focus_enabled is False
            assert settings.link_enabled is False
            assert settings.related_enabled is False
            assert settings.render_enabled is False
            assert settings.search_enabled is False
            assert settings.sync_enabled is False
            assert settings.thread_enabled is False
            assert settings.transport_enabled is False

    def test_fault_lens_features_default_disabled(self):
        """All Fault Lens features should default to disabled."""
        fault_vars = [
            "FAULT_LENS_SIGNED_ACTIONS_ENABLED",
            "FAULT_LENS_SUGGESTIONS_ENABLED",
            "FAULT_LENS_V1_ENABLED",
            "FEATURE_CERTIFICATES",
            "UI_CERTIFICATES",
        ]

        cleared_env = {k: "" for k in fault_vars}

        with patch.dict(os.environ, cleared_env, clear=False):
            from config.env import FaultLensSettings
            settings = FaultLensSettings()

            assert settings.signed_actions_enabled is False
            assert settings.suggestions_enabled is False
            assert settings.v1_enabled is False
            assert settings.feature_certificates is False
            assert settings.ui_certificates is False

    def test_worker_staging_mode_default_true(self):
        """Worker staging mode should default to True (safer)."""
        with patch.dict(os.environ, {"WORKER_STAGING_MODE": ""}, clear=False):
            from config.env import WorkerSettings
            settings = WorkerSettings()

            # Default should be True (staging mode = safer)
            assert settings.staging_mode is True


class TestFeatureGuards:
    """Test feature flag guard functions."""

    def test_check_feature_enabled_raises_404_when_disabled(self):
        """Disabled features should raise 404."""
        from config.env import check_feature_enabled

        with pytest.raises(HTTPException) as exc_info:
            check_feature_enabled("test_feature", enabled=False)

        # Must be 404 (not 403) to prevent enumeration
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    def test_check_feature_enabled_passes_when_enabled(self):
        """Enabled features should not raise."""
        from config.env import check_feature_enabled

        # Should not raise
        check_feature_enabled("test_feature", enabled=True)


# =============================================================================
# EMAIL FEATURE FLAG TESTS
# =============================================================================

class TestEmailFeatureFlags:
    """Test email endpoint behavior based on feature flags."""

    def test_email_search_disabled_returns_404(self):
        """When EMAIL_SEARCH_ENABLED=false, endpoint returns 404."""
        from config.env import check_feature_enabled

        # Simulate disabled feature
        with pytest.raises(HTTPException) as exc_info:
            check_feature_enabled("email_search", enabled=False)

        assert exc_info.value.status_code == 404
        # Message should be generic (prevent enumeration)
        assert "email" not in exc_info.value.detail.lower()

    def test_email_search_enabled_passes_guard(self):
        """When EMAIL_SEARCH_ENABLED=true, guard passes."""
        from config.env import check_feature_enabled

        # Should not raise
        check_feature_enabled("email_search", enabled=True)

    @pytest.mark.parametrize("feature_var,feature_attr", [
        ("EMAIL_EVIDENCE_ENABLED", "evidence_enabled"),
        ("EMAIL_FOCUS_ENABLED", "focus_enabled"),
        ("EMAIL_LINK_ENABLED", "link_enabled"),
        ("EMAIL_RELATED_ENABLED", "related_enabled"),
        ("EMAIL_RENDER_ENABLED", "render_enabled"),
        ("EMAIL_SEARCH_ENABLED", "search_enabled"),
        ("EMAIL_SYNC_ENABLED", "sync_enabled"),
        ("EMAIL_THREAD_ENABLED", "thread_enabled"),
        ("EMAIL_TRANSPORT_ENABLED", "transport_enabled"),
    ])
    def test_email_feature_toggle(self, feature_var: str, feature_attr: str):
        """Test each email feature can be toggled."""
        from config.env import EmailSettings

        # Test disabled (default)
        with patch.dict(os.environ, {feature_var: "false"}):
            settings = EmailSettings()
            assert getattr(settings, feature_attr) is False

        # Test enabled
        with patch.dict(os.environ, {feature_var: "true"}):
            settings = EmailSettings()
            assert getattr(settings, feature_attr) is True


# =============================================================================
# FAULT LENS FEATURE FLAG TESTS
# =============================================================================

class TestFaultLensFeatureFlags:
    """Test Fault Lens endpoint behavior based on feature flags."""

    def test_signed_actions_disabled_returns_404(self):
        """When FAULT_LENS_SIGNED_ACTIONS_ENABLED=false, returns 404."""
        from config.env import check_feature_enabled

        with pytest.raises(HTTPException) as exc_info:
            check_feature_enabled("fault_lens_signed_actions", enabled=False)

        assert exc_info.value.status_code == 404

    def test_certificates_feature_disabled(self):
        """When FEATURE_CERTIFICATES=false, certificate routes blocked."""
        from config.env import check_feature_enabled

        with pytest.raises(HTTPException) as exc_info:
            check_feature_enabled("certificates", enabled=False)

        assert exc_info.value.status_code == 404

    @pytest.mark.parametrize("feature_var,feature_attr", [
        ("FAULT_LENS_SIGNED_ACTIONS_ENABLED", "signed_actions_enabled"),
        ("FAULT_LENS_SUGGESTIONS_ENABLED", "suggestions_enabled"),
        ("FAULT_LENS_V1_ENABLED", "v1_enabled"),
        ("FEATURE_CERTIFICATES", "feature_certificates"),
        ("UI_CERTIFICATES", "ui_certificates"),
    ])
    def test_fault_lens_feature_toggle(self, feature_var: str, feature_attr: str):
        """Test each Fault Lens feature can be toggled."""
        from config.env import FaultLensSettings

        # Test disabled
        with patch.dict(os.environ, {feature_var: "false"}):
            settings = FaultLensSettings()
            assert getattr(settings, feature_attr) is False

        # Test enabled
        with patch.dict(os.environ, {feature_var: "true"}):
            settings = FaultLensSettings()
            assert getattr(settings, feature_attr) is True


# =============================================================================
# WORKER SETTINGS TESTS
# =============================================================================

class TestWorkerSettings:
    """Test worker configuration settings."""

    def test_concurrency_limits_parsed(self):
        """Test concurrency limits are parsed correctly."""
        from config.env import WorkerSettings

        with patch.dict(os.environ, {
            "MAX_CONCURRENT_GLOBAL": "100",
            "MAX_CONCURRENT_PER_WATCHER": "10",
        }):
            settings = WorkerSettings()
            assert settings.max_concurrent_global == 100
            assert settings.max_concurrent_per_watcher == 10

    def test_staging_mode_disables_production(self):
        """Staging mode should indicate not production."""
        from config.env import WorkerSettings

        with patch.dict(os.environ, {"WORKER_STAGING_MODE": "true"}):
            settings = WorkerSettings()
            assert settings.staging_mode is True
            assert settings.is_production_mode is False

        with patch.dict(os.environ, {"WORKER_STAGING_MODE": "false"}):
            settings = WorkerSettings()
            assert settings.staging_mode is False
            assert settings.is_production_mode is True


# =============================================================================
# STARTUP VALIDATION TESTS
# =============================================================================

class TestStartupValidation:
    """Test startup validation behavior."""

    def test_validation_passes_in_development(self):
        """Validation should pass in development even with missing envs."""
        from config.env import validate_startup, ConfigurationError

        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "MASTER_SUPABASE_URL": "",  # Missing
            "MASTER_SUPABASE_SERVICE_KEY": "",  # Missing
        }, clear=False):
            # Should not raise in development
            result = validate_startup()
            assert "warnings" in result

    def test_validation_fails_in_production_without_critical(self):
        """Validation should fail in production without critical envs."""
        from config.env import ConfigurationError

        # This test needs to be careful about module caching
        # We patch the settings directly
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "MASTER_SUPABASE_URL": "",
            "MASTER_SUPABASE_SERVICE_KEY": "",
            "MASTER_SUPABASE_JWT_SECRET": "",
        }, clear=False):
            # Need fresh import to get new settings
            import importlib
            import config.env as env_module

            # Patch the settings object
            env_module.settings.environment = env_module.Environment.PRODUCTION
            env_module.settings.identity.master_supabase_url = ""
            env_module.settings.identity.master_supabase_service_key = ""
            env_module.settings.identity.master_supabase_jwt_secret = ""

            with pytest.raises(ConfigurationError):
                env_module.validate_startup()

    def test_feature_summary_includes_all_features(self):
        """Feature summary should include all feature flags."""
        from config.env import get_feature_summary

        summary = get_feature_summary()

        # Check email features
        assert "email_search" in summary
        assert "email_sync" in summary

        # Check fault lens features
        assert "fault_lens_signed_actions" in summary
        assert "certificates_backend" in summary

        # Check worker mode
        assert "worker_staging_mode" in summary


# =============================================================================
# CONSISTENCY TESTS
# =============================================================================

class TestFeatureFlagConsistency:
    """Test feature flag behavior is consistent."""

    def test_disabled_features_return_same_error(self):
        """All disabled features should return identical 404."""
        from config.env import check_feature_enabled

        features = [
            "email_search",
            "email_sync",
            "certificates",
            "fault_lens_signed_actions",
        ]

        for feature in features:
            with pytest.raises(HTTPException) as exc_info:
                check_feature_enabled(feature, enabled=False)

            # All should be 404 with same message
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Not found"

    def test_no_feature_leakage_in_errors(self):
        """Error messages should not leak feature names."""
        from config.env import check_feature_enabled

        feature_names = [
            "email_search",
            "email_sync_very_secret",
            "certificates_internal",
            "admin_panel",
        ]

        for feature in feature_names:
            with pytest.raises(HTTPException) as exc_info:
                check_feature_enabled(feature, enabled=False)

            # Feature name should not appear in error
            assert feature not in exc_info.value.detail.lower()
            assert "email" not in exc_info.value.detail.lower()
            assert "certificate" not in exc_info.value.detail.lower()
            assert "admin" not in exc_info.value.detail.lower()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
