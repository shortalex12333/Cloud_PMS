#!/usr/bin/env python3
"""
Documents Health Worker (Render Background Service)

Productionized health monitoring for Document Lens v2.

Features:
- Automated health checks every N minutes (configurable)
- Writes results to pms_health_checks table (observable, auditable)
- Emits structured logs for Render dashboard
- Retries with exponential backoff
- Error classification (connectivity vs 4xx vs 5xx)
- Per-endpoint metrics in notes JSON

Canon:
- Backend authority: Only tests endpoints backend exposes
- RLS deny-by-default: Service role writes to health tables
- 500 → fail: Any 5xx error triggers 'unhealthy' status

SLOs:
- Target p95 < 500ms
- Error rate < 1%
- Alert criterion: 2 consecutive unhealthy checks
"""

import os
import sys
import time
import logging
import requests
import jwt as pyjwt
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

# Configuration from environment
HEALTH_CHECK_INTERVAL_MINUTES = int(os.getenv('HEALTH_CHECK_INTERVAL_MINUTES', '15'))
API_BASE = os.getenv('API_BASE_URL', 'https://celeste-pipeline-v1.onrender.com')
TENANT_URL = os.getenv('TENANT_SUPABASE_URL')
JWT_SECRET = os.getenv('TENANT_SUPABASE_JWT_SECRET')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = os.getenv('RENDER_SERVICE_ID')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Rate limiting
MAX_REQUESTS_PER_CHECK = 10  # Cap requests per health check cycle
REQUEST_DELAY_MS = 100  # Delay between requests (rate control)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_MS = 500
MAX_BACKOFF_MS = 5000

# Lens configuration
LENS_ID = "documents"
DOMAIN = "documents"
FEATURE_FLAGS = [
    "DOCUMENT_LENS_V2_ENABLED",
    "DOCUMENT_LENS_SUGGESTIONS_ENABLED",
    "DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED",
]

# Test user (HOD with chief_engineer role)
TEST_USER_ID = os.getenv('TEST_HOD_USER_ID', '05a488fd-e099-4d18-bf86-d87afba4fcdf')
TEST_USER_EMAIL = os.getenv('TEST_HOD_EMAIL', 'hod.test@alex-short.com')
YACHT_ID = os.getenv('TEST_YACHT_ID', '85fe1119-b04c-41ac-80f1-829d23322598')

# Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


class ErrorClass(Enum):
    """Classification of errors for metrics."""
    NONE = "none"
    CONNECTIVITY = "connectivity"
    CLIENT_4XX = "client_4xx"
    SERVER_5XX = "server_5xx"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class EndpointMetrics:
    """Per-endpoint metrics for detailed reporting."""
    endpoint: str
    method: str
    status_code: int
    latency_ms: int
    error_class: str = "none"
    retry_count: int = 0
    error_message: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Structured health check result."""
    lens_id: str
    yacht_id: str
    observed_at: str
    status: str = "healthy"
    p95_latency_ms: Optional[int] = None
    error_rate_percent: float = 0.0
    sample_size: int = 0
    checks: Dict[str, Any] = field(default_factory=dict)
    endpoint_metrics: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    consecutive_unhealthy: int = 0


class HealthCheckError(Exception):
    """Raised when health check fails critically."""
    pass


def classify_error(status_code: int, exception: Optional[Exception] = None) -> ErrorClass:
    """Classify an error for metrics."""
    if exception:
        if isinstance(exception, requests.exceptions.Timeout):
            return ErrorClass.TIMEOUT
        if isinstance(exception, requests.exceptions.ConnectionError):
            return ErrorClass.CONNECTIVITY
        return ErrorClass.UNKNOWN
    if status_code == 0:
        return ErrorClass.CONNECTIVITY
    if 400 <= status_code < 500:
        return ErrorClass.CLIENT_4XX
    if status_code >= 500:
        return ErrorClass.SERVER_5XX
    return ErrorClass.NONE


def exponential_backoff(attempt: int) -> float:
    """Calculate backoff time with jitter."""
    backoff = min(INITIAL_BACKOFF_MS * (2 ** attempt), MAX_BACKOFF_MS)
    jitter = random.uniform(0, backoff * 0.1)
    return (backoff + jitter) / 1000  # Return seconds


def rate_limit_delay():
    """Apply rate limiting delay between requests."""
    time.sleep(REQUEST_DELAY_MS / 1000)


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


def make_request_with_retry(
    method: str,
    url: str,
    headers: Dict[str, str],
    payload: Optional[Dict] = None,
    timeout: int = 10
) -> Tuple[int, Dict, int, int, ErrorClass]:
    """
    Make HTTP request with retries and exponential backoff.

    Returns: (status_code, body, latency_ms, retry_count, error_class)
    """
    retry_count = 0
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        start = time.time()
        try:
            if method.upper() == "GET":
                r = requests.get(url, headers=headers, timeout=timeout)
            else:
                r = requests.post(url, headers=headers, json=payload, timeout=timeout)

            latency_ms = int((time.time() - start) * 1000)

            try:
                body = r.json()
            except:
                body = {"raw": r.text[:500]}  # Truncate long responses

            error_class = classify_error(r.status_code)

            # Don't retry on success or client errors
            if r.status_code < 500:
                return r.status_code, body, latency_ms, retry_count, error_class

            # Retry on 5xx
            retry_count = attempt + 1
            if attempt < MAX_RETRIES - 1:
                backoff = exponential_backoff(attempt)
                logger.warning(f"Retry {retry_count}/{MAX_RETRIES} after {r.status_code}, sleeping {backoff:.2f}s")
                time.sleep(backoff)

        except requests.exceptions.Timeout as e:
            latency_ms = int((time.time() - start) * 1000)
            last_error = e
            retry_count = attempt + 1
            if attempt < MAX_RETRIES - 1:
                backoff = exponential_backoff(attempt)
                logger.warning(f"Timeout, retry {retry_count}/{MAX_RETRIES}, sleeping {backoff:.2f}s")
                time.sleep(backoff)

        except requests.exceptions.ConnectionError as e:
            latency_ms = int((time.time() - start) * 1000)
            last_error = e
            retry_count = attempt + 1
            if attempt < MAX_RETRIES - 1:
                backoff = exponential_backoff(attempt)
                logger.warning(f"Connection error, retry {retry_count}/{MAX_RETRIES}, sleeping {backoff:.2f}s")
                time.sleep(backoff)

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            last_error = e
            error_class = classify_error(0, e)
            return 0, {"error": "exception", "message": str(e)}, latency_ms, retry_count, error_class

    # All retries exhausted
    error_class = classify_error(0, last_error)
    return 0, {"error": "retries_exhausted", "last_error": str(last_error)}, latency_ms, retry_count, error_class


def check_service_health() -> Tuple[str, Dict[str, Any], EndpointMetrics]:
    """Check /v1/actions/health endpoint with metrics."""
    url = f"{API_BASE}/v1/actions/health"
    headers = {"Content-Type": "application/json"}

    status_code, body, latency_ms, retry_count, error_class = make_request_with_retry(
        "GET", url, headers
    )

    metrics = EndpointMetrics(
        endpoint="/v1/actions/health",
        method="GET",
        status_code=status_code,
        latency_ms=latency_ms,
        error_class=error_class.value,
        retry_count=retry_count
    )

    if status_code == 200:
        if body.get("status") == "healthy":
            handlers_loaded = body.get("handlers_loaded", 0)
            total_handlers = body.get("total_handlers", 0)
            if handlers_loaded == total_handlers:
                return "healthy", body, metrics
            else:
                return "degraded", body, metrics
        else:
            return "unhealthy", body, metrics
    else:
        metrics.error_message = f"HTTP {status_code}"
        return "unhealthy", {"error": f"HTTP {status_code}", "body": body}, metrics


def check_feature_flags() -> Tuple[str, Dict[str, str], Optional[EndpointMetrics]]:
    """Check feature flag status via Render API."""
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        return "unknown", {"error": "RENDER_API_KEY or RENDER_SERVICE_ID not set"}, None

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/env-vars"
    headers = {
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Accept": "application/json"
    }

    rate_limit_delay()
    status_code, body, latency_ms, retry_count, error_class = make_request_with_retry(
        "GET", url, headers
    )

    metrics = EndpointMetrics(
        endpoint="/render/env-vars",
        method="GET",
        status_code=status_code,
        latency_ms=latency_ms,
        error_class=error_class.value,
        retry_count=retry_count
    )

    if status_code == 200:
        env_vars = body if isinstance(body, list) else []
        flags = {}
        for item in env_vars:
            if isinstance(item, dict) and "envVar" in item:
                key = item["envVar"].get("key", "")
                if key in FEATURE_FLAGS:
                    flags[key] = item["envVar"].get("value", "")

        all_enabled = all(flags.get(flag) == "true" for flag in FEATURE_FLAGS)
        if all_enabled:
            return "enabled", flags, metrics
        else:
            return "disabled", flags, metrics
    else:
        metrics.error_message = f"HTTP {status_code}"
        return "unknown", {"error": f"HTTP {status_code}"}, metrics


def check_endpoint(
    jwt_token: str,
    endpoint: str,
    method: str = "GET",
    payload: Optional[Dict] = None
) -> Tuple[int, Dict, EndpointMetrics]:
    """Check endpoint availability with metrics."""
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    url = f"{API_BASE}{endpoint}"
    rate_limit_delay()

    status_code, body, latency_ms, retry_count, error_class = make_request_with_retry(
        method, url, headers, payload
    )

    metrics = EndpointMetrics(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        latency_ms=latency_ms,
        error_class=error_class.value,
        retry_count=retry_count,
        error_message=body.get("error") if status_code >= 400 else None
    )

    return status_code, body, metrics


def compute_percentiles(latencies: List[int]) -> Dict[str, int]:
    """Compute P50, P95, P99 latencies."""
    if not latencies:
        return {"p50": 0, "p95": 0, "p99": 0}

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    return {
        "p50": sorted_latencies[int(n * 0.50)],
        "p95": sorted_latencies[min(int(n * 0.95), n - 1)],
        "p99": sorted_latencies[min(int(n * 0.99), n - 1)]
    }


# Track consecutive unhealthy checks for alerting
_consecutive_unhealthy = 0


def run_health_check() -> HealthCheckResult:
    """
    Run comprehensive health check with metrics collection.

    Returns structured result with per-endpoint metrics.
    """
    global _consecutive_unhealthy

    logger.info(f"Starting health check for lens={LENS_ID} yacht={YACHT_ID}")

    result = HealthCheckResult(
        lens_id=LENS_ID,
        yacht_id=YACHT_ID,
        observed_at=datetime.now(timezone.utc).isoformat()
    )

    all_metrics: List[EndpointMetrics] = []
    latencies: List[int] = []

    # Check 1: Service Health
    logger.info("Check 1: Service health endpoint")
    health_status, health_data, health_metrics = check_service_health()
    result.checks["service_health"] = {
        "status": health_status,
        "data": health_data
    }
    all_metrics.append(health_metrics)
    latencies.append(health_metrics.latency_ms)

    if health_status != "healthy":
        result.status = "degraded" if health_status == "degraded" else "unhealthy"
        result.errors.append(f"Service health: {health_status}")
        logger.warning(f"Service health: {health_status}")
    else:
        logger.info(f"✅ Service health: {health_status} ({health_data.get('handlers_loaded', 0)}/{health_data.get('total_handlers', 0)} handlers)")

    # Check 2: Feature Flags (optional)
    logger.info("Check 2: Feature flags status")
    flag_status, flags, flag_metrics = check_feature_flags()
    result.checks["feature_flags"] = {
        "status": flag_status,
        "flags": flags
    }
    if flag_metrics:
        all_metrics.append(flag_metrics)

    if flag_status == "disabled":
        result.status = "unhealthy"
        result.errors.append(f"Feature flags: {flag_status}")
        logger.error(f"Feature flags: {flag_status} - {flags}")
    elif flag_status == "enabled":
        logger.info(f"✅ Feature flags: {flag_status}")
    else:
        logger.warning(f"⚠️ Feature flags: {flag_status} (check skipped)")

    # Generate JWT for endpoint checks
    jwt_token = generate_jwt(TEST_USER_ID, TEST_USER_EMAIL)

    # Check 3: List Endpoint
    logger.info("Check 3: List endpoint")
    status, body, list_metrics = check_endpoint(jwt_token, f"/v1/actions/list?domain={DOMAIN}")
    result.checks["list_endpoint"] = {
        "status_code": status,
        "latency_ms": list_metrics.latency_ms,
        "action_count": body.get("total_count", 0) if status == 200 else None
    }
    all_metrics.append(list_metrics)
    latencies.append(list_metrics.latency_ms)

    if status == 503:
        result.status = "unhealthy"
        result.errors.append("List endpoint: 503 FEATURE_DISABLED")
        logger.error(f"❌ List endpoint: 503 FEATURE_DISABLED")
    elif status >= 500:
        result.status = "unhealthy"
        result.errors.append(f"List endpoint: {status}×5xx error")
        logger.error(f"❌ List endpoint: {status}×5xx error")
    elif status == 200:
        logger.info(f"✅ List endpoint: 200 OK ({body.get('total_count', 0)} actions, {list_metrics.latency_ms}ms)")
    else:
        logger.warning(f"⚠️ List endpoint: {status} (unexpected)")

    # Check 4: Execute list_documents
    logger.info("Check 4: Execute list_documents action")
    status, body, exec_metrics = check_endpoint(
        jwt_token,
        "/v1/actions/execute",
        method="POST",
        payload={
            "action": "list_documents",
            "context": {"yacht_id": YACHT_ID},
            "payload": {"limit": 10}
        }
    )
    result.checks["execute_list_documents"] = {
        "status_code": status,
        "latency_ms": exec_metrics.latency_ms
    }
    all_metrics.append(exec_metrics)
    latencies.append(exec_metrics.latency_ms)

    if status >= 500:
        result.status = "unhealthy"
        result.errors.append(f"Execute list_documents: {status}×5xx error")
        logger.error(f"❌ Execute list_documents: {status}×5xx error")
    elif status == 200:
        logger.info(f"✅ Execute list_documents: 200 OK ({exec_metrics.latency_ms}ms)")
    else:
        logger.warning(f"⚠️ Execute list_documents: {status}")

    # Compute metrics
    percentiles = compute_percentiles(latencies)
    result.p95_latency_ms = percentiles["p95"]

    # Error rate calculation
    endpoint_checks = [m for m in all_metrics if m.endpoint.startswith("/v1/")]
    error_count = sum(1 for m in endpoint_checks if m.status_code >= 400 or m.status_code == 0)
    result.error_rate_percent = round((error_count / len(endpoint_checks)) * 100, 2) if endpoint_checks else 0.0
    result.sample_size = len(endpoint_checks)

    # Store endpoint metrics
    result.endpoint_metrics = [asdict(m) for m in all_metrics]

    # Track consecutive unhealthy for alerting
    if result.status == "unhealthy":
        _consecutive_unhealthy += 1
        result.consecutive_unhealthy = _consecutive_unhealthy
        if _consecutive_unhealthy >= 2:
            logger.error(f"🚨 ALERT: {_consecutive_unhealthy} consecutive unhealthy checks")
    else:
        _consecutive_unhealthy = 0
        result.consecutive_unhealthy = 0

    # SLO checks
    if result.p95_latency_ms and result.p95_latency_ms > 500:
        logger.warning(f"⚠️ SLO breach: p95={result.p95_latency_ms}ms > 500ms target")
    if result.error_rate_percent > 1.0:
        logger.warning(f"⚠️ SLO breach: error_rate={result.error_rate_percent}% > 1% target")

    logger.info(f"Health check complete: status={result.status} p95={result.p95_latency_ms}ms error_rate={result.error_rate_percent}%")

    return result


def write_health_check_to_db(result: HealthCheckResult) -> bool:
    """Write health check result to pms_health_checks table with retry."""
    if not TENANT_URL or not SERVICE_KEY:
        logger.warning("TENANT_SUPABASE_URL or SUPABASE_SERVICE_KEY not set - skipping DB write")
        return False

    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # Build notes with endpoint metrics
    notes = {
        "checks": result.checks,
        "errors": result.errors,
        "endpoint_metrics": result.endpoint_metrics,
        "consecutive_unhealthy": result.consecutive_unhealthy,
        "percentiles": compute_percentiles([m["latency_ms"] for m in result.endpoint_metrics])
    }

    health_data = {
        "yacht_id": result.yacht_id,
        "lens_id": result.lens_id,
        "status": result.status,
        "p95_latency_ms": result.p95_latency_ms,
        "error_rate_percent": result.error_rate_percent,
        "sample_size": result.sample_size,
        "observed_at": result.observed_at,
        "notes": notes
    }

    url = f"{TENANT_URL}/rest/v1/pms_health_checks"
    status_code, body, latency_ms, retry_count, error_class = make_request_with_retry(
        "POST", url, headers, health_data
    )

    if status_code in (200, 201):
        response_data = body if isinstance(body, list) else [body]
        check_id = response_data[0].get("id") if response_data else None
        logger.info(f"✅ Wrote health check to DB: id={check_id}")

        # Write health events for errors
        if check_id and result.errors:
            for error in result.errors:
                event_data = {
                    "check_id": check_id,
                    "level": "error",
                    "detail_json": {"message": error}
                }
                make_request_with_retry(
                    "POST",
                    f"{TENANT_URL}/rest/v1/pms_health_events",
                    headers,
                    event_data
                )
            logger.info(f"✅ Wrote {len(result.errors)} health events")

        return True
    else:
        logger.error(f"❌ Failed to write health check to DB: {status_code} - {body}")
        return False


def main():
    """Main loop with graceful shutdown."""
    logger.info(f"Starting {LENS_ID} health worker v2")
    logger.info(f"Interval: {HEALTH_CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"API Base: {API_BASE}")
    logger.info(f"Domain: {DOMAIN}")
    logger.info(f"Feature Flags: {', '.join(FEATURE_FLAGS)}")
    logger.info(f"Rate limit: {REQUEST_DELAY_MS}ms between requests")
    logger.info(f"Max retries: {MAX_RETRIES} with exponential backoff")

    # Validate configuration
    if not JWT_SECRET:
        logger.error("TENANT_SUPABASE_JWT_SECRET not set")
        sys.exit(1)

    if not SERVICE_KEY:
        logger.warning("SUPABASE_SERVICE_KEY not set - DB writes will be skipped")

    if not RENDER_API_KEY:
        logger.warning("RENDER_API_KEY not set - feature flag checks will be skipped")

    # Main loop
    while True:
        try:
            result = run_health_check()
            write_health_check_to_db(result)

            sleep_seconds = HEALTH_CHECK_INTERVAL_MINUTES * 60
            logger.info(f"Sleeping for {HEALTH_CHECK_INTERVAL_MINUTES} minutes...")
            time.sleep(sleep_seconds)

        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}")
            # Sleep for 1 minute before retrying
            time.sleep(60)


if __name__ == "__main__":
    main()
