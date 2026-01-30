#!/usr/bin/env python3
"""
Render Environment Validation Script
=====================================

Validates presence and format of critical environment variables.
Prints a redacted summary suitable for CI/CD logs.

Usage:
    python scripts/ops/check_render_env.py

Exit codes:
    0 - All critical envs present
    1 - Missing critical envs
    2 - Configuration error

Environment:
    Reads from current environment variables.
    For local testing, source your .env file first.
"""

import os
import sys
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class EnvVar:
    """Environment variable specification."""
    name: str
    required: bool
    secret: bool  # If true, value is redacted in output
    pattern: Optional[str] = None  # Regex pattern for validation
    description: str = ""


# Critical identity/auth variables
IDENTITY_VARS = [
    EnvVar("MASTER_SUPABASE_URL", required=True, secret=False,
           pattern=r"^https://.*\.supabase\.co$",
           description="MASTER Supabase URL"),
    EnvVar("MASTER_SUPABASE_SERVICE_KEY", required=True, secret=True,
           pattern=r"^eyJ",
           description="MASTER service role key"),
    EnvVar("MASTER_SUPABASE_JWT_SECRET", required=True, secret=True,
           description="JWT signing secret"),
    EnvVar("TENANT_SUPABASE_JWT_SECRET", required=False, secret=True,
           description="Tenant JWT secret (optional)"),
    EnvVar("DEFAULT_YACHT_CODE", required=False, secret=False,
           pattern=r"^y[A-Z0-9_]+$",
           description="Default yacht code"),
]

# Per-yacht tenant variables (check for at least one)
TENANT_VARS = [
    EnvVar("yTEST_YACHT_001_SUPABASE_URL", required=False, secret=False,
           pattern=r"^https://.*\.supabase\.co$",
           description="Test yacht Supabase URL"),
    EnvVar("yTEST_YACHT_001_SUPABASE_SERVICE_KEY", required=False, secret=True,
           pattern=r"^eyJ",
           description="Test yacht service key"),
    EnvVar("yTEST_YACHT_001_SUPABASE_JWT_SECRET", required=False, secret=True,
           description="Test yacht JWT secret"),
]

# Email feature flags
EMAIL_VARS = [
    EnvVar("EMAIL_EVIDENCE_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email evidence feature"),
    EnvVar("EMAIL_FOCUS_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email focus feature"),
    EnvVar("EMAIL_LINK_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email link feature"),
    EnvVar("EMAIL_RELATED_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email related feature"),
    EnvVar("EMAIL_RENDER_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email render feature"),
    EnvVar("EMAIL_SEARCH_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email search feature"),
    EnvVar("EMAIL_SYNC_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email sync feature"),
    EnvVar("EMAIL_THREAD_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email thread feature"),
    EnvVar("EMAIL_TRANSPORT_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Email transport feature"),
]

# Fault Lens feature flags
FAULT_LENS_VARS = [
    EnvVar("FAULT_LENS_SIGNED_ACTIONS_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Fault Lens signed actions"),
    EnvVar("FAULT_LENS_SUGGESTIONS_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Fault Lens suggestions"),
    EnvVar("FAULT_LENS_V1_ENABLED", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Fault Lens v1"),
    EnvVar("FEATURE_CERTIFICATES", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Certificates backend"),
    EnvVar("UI_CERTIFICATES", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Certificates UI"),
]

# Worker/streaming settings
WORKER_VARS = [
    EnvVar("MAX_CONCURRENT_GLOBAL", required=False, secret=False,
           pattern=r"^\d+$",
           description="Max global concurrency"),
    EnvVar("MAX_CONCURRENT_PER_WATCHER", required=False, secret=False,
           pattern=r"^\d+$",
           description="Max per-watcher concurrency"),
    EnvVar("WORKER_BATCH_SIZE", required=False, secret=False,
           pattern=r"^\d+$",
           description="Worker batch size"),
    EnvVar("WORKER_POLL_INTERVAL", required=False, secret=False,
           pattern=r"^\d+$",
           description="Worker poll interval"),
    EnvVar("WORKER_STAGING_MODE", required=False, secret=False,
           pattern=r"^(true|false)$",
           description="Worker staging mode"),
]

# AI/external services
AI_VARS = [
    EnvVar("OPENAI_API_KEY", required=False, secret=True,
           pattern=r"^sk-",
           description="OpenAI API key"),
    EnvVar("AZURE_READ_APP_ID", required=False, secret=False,
           description="Azure read app ID"),
    EnvVar("AZURE_READ_CLIENT_SECRET", required=False, secret=True,
           description="Azure read secret"),
    EnvVar("AZURE_WRITE_APP_ID", required=False, secret=False,
           description="Azure write app ID"),
    EnvVar("AZURE_WRITE_CLIENT_SECRET", required=False, secret=True,
           description="Azure write secret"),
]

# Infrastructure
INFRA_VARS = [
    EnvVar("ENVIRONMENT", required=False, secret=False,
           pattern=r"^(development|staging|production|test)$",
           description="Environment"),
    EnvVar("LOG_LEVEL", required=False, secret=False,
           pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
           description="Log level"),
    EnvVar("PORT", required=False, secret=False,
           pattern=r"^\d+$",
           description="HTTP port"),
    EnvVar("PYTHONPATH", required=False, secret=False,
           description="Python path"),
]


# =============================================================================
# VALIDATION
# =============================================================================

def redact_value(value: str, secret: bool) -> str:
    """Redact secret values for safe logging."""
    if not value:
        return "(not set)"
    if not secret:
        return value[:50] + "..." if len(value) > 50 else value
    # Redact secrets: show first 4 and last 4 chars
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def validate_env_var(env_var: EnvVar) -> Tuple[bool, str, str]:
    """
    Validate a single environment variable.

    Returns:
        (is_valid, status_message, redacted_value)
    """
    value = os.getenv(env_var.name, "")
    redacted = redact_value(value, env_var.secret)

    if not value:
        if env_var.required:
            return False, "MISSING (required)", redacted
        return True, "not set", redacted

    if env_var.pattern:
        if not re.match(env_var.pattern, value, re.IGNORECASE):
            return False, "INVALID FORMAT", redacted

    return True, "OK", redacted


def validate_all() -> Tuple[bool, Dict[str, List[Tuple[EnvVar, bool, str, str]]]]:
    """
    Validate all environment variables.

    Returns:
        (all_valid, results_by_category)
    """
    categories = {
        "Identity/Auth": IDENTITY_VARS,
        "Tenant (per-yacht)": TENANT_VARS,
        "Email Features": EMAIL_VARS,
        "Fault Lens Features": FAULT_LENS_VARS,
        "Worker Settings": WORKER_VARS,
        "AI/External Services": AI_VARS,
        "Infrastructure": INFRA_VARS,
    }

    results: Dict[str, List[Tuple[EnvVar, bool, str, str]]] = {}
    all_valid = True

    for category, vars_list in categories.items():
        results[category] = []
        for env_var in vars_list:
            is_valid, status, redacted = validate_env_var(env_var)
            results[category].append((env_var, is_valid, status, redacted))
            if not is_valid and env_var.required:
                all_valid = False

    return all_valid, results


def check_tenant_configured(results: Dict) -> bool:
    """Check if at least one tenant is configured."""
    tenant_results = results.get("Tenant (per-yacht)", [])
    for env_var, is_valid, status, _ in tenant_results:
        if "SUPABASE_URL" in env_var.name and status == "OK":
            return True
    return False


# =============================================================================
# OUTPUT
# =============================================================================

def print_results(results: Dict[str, List[Tuple[EnvVar, bool, str, str]]]):
    """Print validation results in a formatted table."""
    print("=" * 70)
    print("RENDER ENVIRONMENT VALIDATION")
    print("=" * 70)
    print()

    for category, vars_results in results.items():
        print(f"[{category}]")
        print("-" * 70)

        for env_var, is_valid, status, redacted in vars_results:
            # Status indicator
            if status == "OK":
                indicator = "[OK]"
            elif status == "not set":
                indicator = "[--]"
            elif "MISSING" in status:
                indicator = "[!!]"
            else:
                indicator = "[??]"

            # Format line
            name = env_var.name[:35].ljust(35)
            status_str = status[:15].ljust(15)

            if env_var.secret and status == "OK":
                value_str = redacted
            elif status == "OK":
                value_str = redacted[:20] + "..." if len(redacted) > 20 else redacted
            else:
                value_str = ""

            print(f"  {indicator} {name} {status_str} {value_str}")

        print()


def print_summary(all_valid: bool, results: Dict):
    """Print summary and recommendations."""
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Count by status
    total = 0
    ok_count = 0
    not_set_count = 0
    missing_count = 0
    invalid_count = 0

    for category, vars_results in results.items():
        for _, is_valid, status, _ in vars_results:
            total += 1
            if status == "OK":
                ok_count += 1
            elif status == "not set":
                not_set_count += 1
            elif "MISSING" in status:
                missing_count += 1
            else:
                invalid_count += 1

    print(f"  Total variables checked: {total}")
    print(f"  Configured:              {ok_count}")
    print(f"  Not set (optional):      {not_set_count}")
    print(f"  Missing (required):      {missing_count}")
    print(f"  Invalid format:          {invalid_count}")
    print()

    # Check tenant configuration
    if not check_tenant_configured(results):
        print("  [WARN] No tenant (yacht) Supabase configured")

    # Overall status
    if all_valid:
        print("  STATUS: PASS - All required variables present")
    else:
        print("  STATUS: FAIL - Missing required variables")

    print("=" * 70)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    try:
        all_valid, results = validate_all()
        print_results(results)
        print_summary(all_valid, results)

        # Exit code
        if all_valid:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: Configuration validation failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
