#!/usr/bin/env python3
"""
parts Health Worker (Render Background Service)

Productionized replacement for ad-hoc monitor_canary_health.py

Purpose:
- Automated health checks every N minutes (configurable)
- Writes results to pms_health_checks table (observable, auditable)
- Emits structured logs for Render dashboard
- Detects feature flag toggles (503 → 200 transitions)

Canon:
- Backend authority: Only tests endpoints backend exposes
- RLS deny-by-default: Service role writes to health tables
- 500 → fail: Any 5xx error triggers 'unhealthy' status

Generated from: docs/pipeline/templates/lens_ops/health_worker_template.py
"""

import os
import sys
import time
import logging
import requests
import jwt as pyjwt
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

# Configuration from environment
HEALTH_CHECK_INTERVAL_MINUTES = int(os.getenv('HEALTH_CHECK_INTERVAL_MINUTES', '15'))
API_BASE = os.getenv('API_BASE_URL', 'https://pipeline-core.int.celeste7.ai')
TENANT_URL = os.getenv('TENANT_SUPABASE_URL')
JWT_SECRET = os.getenv('TENANT_SUPABASE_JWT_SECRET')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = os.getenv('RENDER_SERVICE_ID')

# Lens configuration (replace with actual values)
LENS_ID = "parts"  # e.g., "faults"
DOMAIN = "parts"  # e.g., "faults"
FEATURE_FLAGS = [
    "PARTS_LENS_V2_ENABLED",  # e.g., "FAULT_LENS_V1_ENABLED"
    "PARTS_LENS_SUGGESTIONS_ENABLED",  # e.g., "FAULT_LENS_SUGGESTIONS_ENABLED"
    "PARTS_LENS_SIGNED_ACTIONS_ENABLED",  # e.g., "FAULT_LENS_SIGNED_ACTIONS_ENABLED"
]

# Test user (HOD with chief_engineer role)
TEST_USER_ID = "05a488fd-e099-4d18-bf86-d87afba4fcdf"  # e.g., "05a488fd-e099-4d18-bf86-d87afba4fcdf"
TEST_USER_EMAIL = "hod.test@alex-short.com"  # e.g., "hod.test@alex-short.com"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # e.g., "85fe1119-b04c-41ac-80f1-829d23322598"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    """Raised when health check fails critically."""
    pass


def generate_jwt(user_id: str, email: str) -> str:
    """Generate a fresh JWT token for testing."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=2)
    payload = {
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": f"{TENANT_URL}/auth/v1",
        "sub": user_id,
        "email": email,
        "phone": "",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {},
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"health-{int(now.timestamp())}"
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def check_service_health() -> Tuple[str, Dict[str, Any]]:
    """Check /v1/actions/health endpoint."""
    try:
        r = requests.get(f"{API_BASE}/v1/actions/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "healthy":
                handlers_loaded = data.get("handlers_loaded", 0)
                total_handlers = data.get("total_handlers", 0)
                if handlers_loaded == total_handlers:
                    return "healthy", data
                else:
                    return "degraded", data
            else:
                return "unhealthy", data
        else:
            return "unhealthy", {"error": f"HTTP {r.status_code}", "body": r.text}
    except Exception as e:
        return "unhealthy", {"error": "exception", "message": str(e)}


def check_feature_flags() -> Tuple[str, Dict[str, str]]:
    """Check feature flag status via Render API."""
    try:
        url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars"
        headers = {
            "Authorization": f"Bearer {RENDER_API_KEY}",
            "Accept": "application/json"
        }
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200:
            env_vars = r.json()
            flags = {}
            for item in env_vars:
                key = item["envVar"]["key"]
                if key in FEATURE_FLAGS:
                    flags[key] = item["envVar"]["value"]

            # Check all expected flags are enabled
            all_enabled = all(flags.get(flag) == "true" for flag in FEATURE_FLAGS)
            if all_enabled:
                return "enabled", flags
            else:
                return "disabled", flags
        else:
            return "unknown", {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return "unknown", {"error": "exception", "message": str(e)}


def check_endpoint(jwt_token: str, endpoint: str, method: str = "GET", payload: Dict = None) -> Tuple[int, Dict, int]:
    """
    Check endpoint availability.

    Returns: (status_code, response_body, latency_ms)
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    start = time.time()
    try:
        if method.upper() == "GET":
            r = requests.get(f"{API_BASE}{endpoint}", headers=headers, timeout=10)
        else:
            r = requests.post(f"{API_BASE}{endpoint}", headers=headers, json=payload, timeout=10)

        latency_ms = int((time.time() - start) * 1000)

        try:
            body = r.json()
        except:
            body = {"raw": r.text}

        return r.status_code, body, latency_ms
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return 0, {"error": "exception", "message": str(e)}, latency_ms


def run_health_check() -> Dict[str, Any]:
    """
    Run comprehensive health check.

    Returns result dict with status, latencies, errors.
    """
    logger.info(f"Starting health check for lens=parts yacht=85fe1119-b04c-41ac-80f1-829d23322598")

    result = {
        "lens_id": LENS_ID,
        "yacht_id": YACHT_ID,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "latencies_ms": [],
        "errors": [],
        "status": "healthy"  # default, will downgrade if issues found
    }

    # Check 1: Service Health
    logger.info("Check 1: Service health endpoint")
    health_status, health_data = check_service_health()
    result["checks"]["service_health"] = {
        "status": health_status,
        "data": health_data
    }

    if health_status != "healthy":
        result["status"] = "degraded" if health_status == "degraded" else "unhealthy"
        result["errors"].append(f"Service health: {health_status}")
        logger.warning(f"Service health: {health_status}")
    else:
        logger.info(f"✅ Service health: {health_status} ({health_data.get('handlers_loaded', 0)}/{health_data.get('total_handlers', 0)} handlers)")

    # Check 2: Feature Flags
    logger.info("Check 2: Feature flags status")
    flag_status, flags = check_feature_flags()
    result["checks"]["feature_flags"] = {
        "status": flag_status,
        "flags": flags
    }

    if flag_status != "enabled":
        result["status"] = "unhealthy"
        result["errors"].append(f"Feature flags: {flag_status}")
        logger.error(f"Feature flags: {flag_status} - {flags}")
    else:
        logger.info(f"✅ Feature flags: {flag_status} - {', '.join(f'{k}={v}' for k, v in flags.items())}")

    # Generate JWT for endpoint checks
    jwt_token = generate_jwt(TEST_USER_ID, TEST_USER_EMAIL)

    # Check 3: List Endpoint
    logger.info("Check 3: List endpoint")
    status, body, latency = check_endpoint(jwt_token, f"/v1/actions/list?domain=parts")
    result["checks"]["list_endpoint"] = {
        "status_code": status,
        "latency_ms": latency,
        "action_count": body.get("total_count", 0) if status == 200 else None
    }
    result["latencies_ms"].append(latency)

    if status == 503:
        result["status"] = "unhealthy"
        result["errors"].append("List endpoint: 503 FEATURE_DISABLED (flags may have been toggled off)")
        logger.error(f"❌ List endpoint: 503 FEATURE_DISABLED")
    elif status >= 500:
        result["status"] = "unhealthy"
        result["errors"].append(f"List endpoint: {status}×5xx error")
        logger.error(f"❌ List endpoint: {status}×5xx error")
    elif status == 200:
        logger.info(f"✅ List endpoint: 200 OK ({body.get('total_count', 0)} actions, {latency}ms)")
    else:
        logger.warning(f"⚠️ List endpoint: {status} (unexpected)")

    # Check 4: Suggestions Endpoint
    logger.info("Check 4: Suggestions endpoint")
    status, body, latency = check_endpoint(
        jwt_token,
        "/v1/actions/suggestions",
        method="POST",
        payload={"domain": DOMAIN}
    )
    result["checks"]["suggestions_endpoint"] = {
        "status_code": status,
        "latency_ms": latency,
        "action_count": body.get("total_count", 0) if status == 200 else None
    }
    result["latencies_ms"].append(latency)

    if status == 503:
        result["status"] = "unhealthy"
        result["errors"].append("Suggestions endpoint: 503 FEATURE_DISABLED")
        logger.error(f"❌ Suggestions endpoint: 503 FEATURE_DISABLED")
    elif status >= 500:
        result["status"] = "unhealthy"
        result["errors"].append(f"Suggestions endpoint: {status}×5xx error")
        logger.error(f"❌ Suggestions endpoint: {status}×5xx error")
    elif status == 200:
        logger.info(f"✅ Suggestions endpoint: 200 OK ({body.get('total_count', 0)} actions, {latency}ms)")
    else:
        logger.warning(f"⚠️ Suggestions endpoint: {status} (unexpected)")

    # Compute metrics
    if result["latencies_ms"]:
        result["p95_latency_ms"] = int(sorted(result["latencies_ms"])[int(len(result["latencies_ms"]) * 0.95)])
    else:
        result["p95_latency_ms"] = None

    total_checks = 2  # list + suggestions
    error_checks = sum(1 for c in [result["checks"]["list_endpoint"], result["checks"]["suggestions_endpoint"]] if c["status_code"] >= 400)
    result["error_rate_percent"] = round((error_checks / total_checks) * 100, 2) if total_checks > 0 else 0.0
    result["sample_size"] = total_checks

    # Overall status
    logger.info(f"Health check complete: status={result['status']} p95={result['p95_latency_ms']}ms error_rate={result['error_rate_percent']}%")

    return result


def write_health_check_to_db(result: Dict[str, Any]):
    """Write health check result to pms_health_checks table."""
    try:
        headers = {
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json"
        }

        # Insert health check row
        health_data = {
            "yacht_id": result["yacht_id"],
            "lens_id": result["lens_id"],
            "status": result["status"],
            "p95_latency_ms": result["p95_latency_ms"],
            "error_rate_percent": result["error_rate_percent"],
            "sample_size": result["sample_size"],
            "observed_at": result["observed_at"],
            "notes": {
                "checks": result["checks"],
                "errors": result["errors"]
            }
        }

        r = requests.post(
            f"{TENANT_URL}/rest/v1/pms_health_checks",
            headers=headers,
            json=health_data,
            timeout=10
        )

        if r.status_code in (200, 201):
            check_id = r.json()[0]["id"]
            logger.info(f"✅ Wrote health check to DB: id={check_id}")

            # Insert health events for each error
            if result["errors"]:
                for error in result["errors"]:
                    event_data = {
                        "check_id": check_id,
                        "level": "error",
                        "detail_json": {"message": error}
                    }
                    requests.post(
                        f"{TENANT_URL}/rest/v1/pms_health_events",
                        headers=headers,
                        json=event_data,
                        timeout=10
                    )
                logger.info(f"✅ Wrote {len(result['errors'])} health events")
        else:
            logger.error(f"❌ Failed to write health check to DB: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"❌ Exception writing to DB: {str(e)}")


def main():
    """Main loop."""
    logger.info(f"Starting parts health worker")
    logger.info(f"Interval: {HEALTH_CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"API Base: {API_BASE}")
    logger.info(f"Domain: parts")
    logger.info(f"Feature Flags: {', '.join(FEATURE_FLAGS)}")

    # Validate configuration
    if not JWT_SECRET:
        logger.error("TENANT_SUPABASE_JWT_SECRET not set")
        sys.exit(1)

    if not SERVICE_KEY:
        logger.error("SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    if not RENDER_API_KEY:
        logger.warning("RENDER_API_KEY not set - feature flag checks will fail")

    # Main loop
    while True:
        try:
            # Run health check
            result = run_health_check()

            # Write to DB
            write_health_check_to_db(result)

            # Sleep until next check
            sleep_seconds = HEALTH_CHECK_INTERVAL_MINUTES * 60
            logger.info(f"Sleeping for {HEALTH_CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(sleep_seconds)

        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}")
            # Sleep for 1 minute before retrying
            time.sleep(60)


if __name__ == "__main__":
    main()
