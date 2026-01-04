import os
"""
7-Day Stress Testing Campaign Configuration
============================================
LOCKED PRODUCTION FACTS - DO NOT MODIFY
"""

# Endpoints
EXTRACT_URL = "https://extract.core.celeste7.ai/extract"
SEARCH_URL = "https://celeste-microactions.onrender.com/v2/search"
HEALTH_URL = "https://celeste-microactions.onrender.com/health"

# Authentication
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Test yacht (verified to exist)
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Contractual Lanes (LOCKED)
VALID_LANES = {"BLOCKED", "NO_LLM", "RULES_ONLY", "GPT"}

# Daily minimums per lane
DAILY_MINIMUMS = {
    "NO_LLM": 200,
    "GPT": 100,
    "RULES_ONLY": 50,
    "BLOCKED": 30,
}

# Concurrency settings
MIN_CONCURRENCY = 5
MAX_CONCURRENCY = 50

# Target total calls over 7 days
TARGET_TOTAL_CALLS = 10000
CALLS_PER_DAY = TARGET_TOTAL_CALLS // 7  # ~1428/day

# Pass thresholds
POLITE_PREFIX_PASS_RATE = 0.95
NON_DOMAIN_BLOCK_RATE = 0.95
SEARCH_SUCCESS_RATE = 0.98

# Logging
LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/stress_campaign/logs"
