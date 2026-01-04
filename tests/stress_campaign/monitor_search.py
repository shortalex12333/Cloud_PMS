#!/usr/bin/env python3
"""
Monitor /v2/search endpoint status.
Polls every 5 minutes to detect when the canonical fix is deployed.
"""

import requests
import time
from datetime import datetime
import os

SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SEARCH_URL = "https://celeste-microactions.onrender.com/v2/search"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
LOG_DIR = "tests/stress_campaign/logs"

def check_search():
    """Check if /v2/search is working."""
    try:
        resp = requests.post(
            SEARCH_URL,
            json={"query": "main engine", "yacht_id": TEST_YACHT_ID},
            headers={"Authorization": f"Bearer {SERVICE_KEY}"},
            timeout=60
        )
        if resp.status_code == 200:
            return True, "OK"
        else:
            error = resp.json().get("error", f"HTTP {resp.status_code}")
            return False, error[:100]
    except Exception as e:
        return False, str(e)[:100]

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "search_monitor.log")

    print("=" * 60)
    print(" /v2/search ENDPOINT MONITOR")
    print(" Checking every 5 minutes for canonical fix deployment")
    print("=" * 60)
    print()

    check_count = 0
    while True:
        check_count += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        working, status = check_search()

        status_str = "WORKING" if working else f"BROKEN: {status}"
        log_line = f"[{ts}] Check #{check_count}: {status_str}"
        print(log_line, flush=True)

        with open(log_file, 'a') as f:
            f.write(log_line + "\n")

        if working:
            print("\n" + "=" * 60)
            print(" /v2/search IS NOW WORKING!")
            print(" Render has been redeployed with the canonical fix.")
            print(" Day 2 stress testing can now proceed.")
            print("=" * 60)
            break

        # Wait 5 minutes
        time.sleep(300)

if __name__ == "__main__":
    main()
