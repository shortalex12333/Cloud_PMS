#!/usr/bin/env python3
"""
CelesteOS Production Stress Test Runner
========================================

Runs the V2 stress test dataset against the production /extract endpoint.

Features:
- 15-second throttle between requests
- Full result collection and storage
- Progress tracking and resumable
- Detailed analytics output
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# =============================================================================
# CONFIGURATION (from n8n)
# =============================================================================

ENDPOINT = "https://extract.core.celeste7.ai/extract"
JWT_TOKEN = os.environ.get("SUPABASE_SERVICE_KEY", "")
YACHT_SALT = "e49469e09cb6529e0bfef118370cf8425b006f0abbc77475da2e0cb479af8b18"

DELAY_SECONDS = 15  # Wait between requests
TIMEOUT_SECONDS = 60  # Request timeout
BATCH_SIZE = 5  # Save results every N requests
MAX_CASES = None  # Set to limit cases (None = all)

# Files
DATASET_FILE = "stress_test_dataset_v2.json"
RESULTS_FILE = "production_stress_results_v2.json"
PROGRESS_FILE = "production_stress_progress_v2.json"

# =============================================================================
# STRESS TEST RUNNER
# =============================================================================

class ProductionStressTest:
    def __init__(
        self,
        endpoint: str = ENDPOINT,
        jwt_token: str = JWT_TOKEN,
        yacht_salt: str = YACHT_SALT,
        delay: int = DELAY_SECONDS
    ):
        self.endpoint = endpoint
        self.jwt_token = jwt_token
        self.yacht_salt = yacht_salt
        self.delay = delay
        self.results = []
        self.start_index = 0

        # Load progress if exists
        self._load_progress()

    def _load_progress(self):
        """Load progress from previous run if exists."""
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE) as f:
                    progress = json.load(f)
                    self.start_index = progress.get("last_completed", 0)
                    print(f"Resuming from case {self.start_index}")
            except:
                pass

        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE) as f:
                    data = json.load(f)
                    self.results = data.get("results", [])
                    print(f"Loaded {len(self.results)} existing results")
            except:
                pass

    def _save_progress(self, index: int):
        """Save current progress."""
        with open(PROGRESS_FILE, "w") as f:
            json.dump({"last_completed": index, "timestamp": datetime.now().isoformat()}, f)

    def _save_results(self):
        """Save all results to file."""
        output = {
            "meta": {
                "endpoint": self.endpoint,
                "total_results": len(self.results),
                "last_updated": datetime.now().isoformat(),
                "delay_seconds": self.delay
            },
            "results": self.results,
            "summary": self._calculate_summary()
        }
        with open(RESULTS_FILE, "w") as f:
            json.dump(output, f, indent=2)

    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics from results."""
        if not self.results:
            return {}

        total = len(self.results)
        successful = sum(1 for r in self.results if r.get("status") == "success")
        failed = sum(1 for r in self.results if r.get("status") == "error")

        # Action detection accuracy
        action_correct = 0
        action_wrong = 0
        false_positives = 0
        false_negatives = 0

        # Entity extraction accuracy
        entity_hits = 0
        entity_misses = 0

        for r in self.results:
            expected = r.get("expected", {})
            actual = r.get("response", {})

            if r.get("status") != "success":
                continue

            # Check action detection
            expected_trigger = expected.get("should_trigger_action", False)
            expected_action = expected.get("primary_action", "none_search_only")

            # Get actual action from response
            actual_action = actual.get("action") or actual.get("intent")
            actual_triggered = actual_action is not None and actual_action != "none_search_only"

            if expected_trigger and actual_triggered:
                if actual_action == expected_action:
                    action_correct += 1
                else:
                    action_wrong += 1
            elif expected_trigger and not actual_triggered:
                false_negatives += 1
            elif not expected_trigger and actual_triggered:
                false_positives += 1
            else:
                action_correct += 1  # Both say no action = correct

            # Check entity extraction
            expected_entities = expected.get("expected_entities", [])
            actual_entities = actual.get("entities", [])
            actual_values = {e.get("value", "").lower() for e in actual_entities}

            for exp_ent in expected_entities:
                hint = exp_ent.get("value_hint", "").lower()
                if hint in actual_values or any(hint in v for v in actual_values):
                    entity_hits += 1
                else:
                    entity_misses += 1

        return {
            "total_tests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "action_detection": {
                "correct": action_correct,
                "wrong_action": action_wrong,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "accuracy": round(action_correct / max(successful, 1) * 100, 2)
            },
            "entity_extraction": {
                "hits": entity_hits,
                "misses": entity_misses,
                "accuracy": round(entity_hits / max(entity_hits + entity_misses, 1) * 100, 2)
            }
        }

    def make_request(self, query: str, session_id: str = None) -> Dict:
        """Make a single request to the endpoint."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}",
        }

        payload = {
            "query": query,
            "include_embedding": False,  # Skip embedding to speed up
            "session_id": session_id or f"stress-test-{int(time.time())}"
        }

        try:
            start_time = time.time()
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=TIMEOUT_SECONDS
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                resp_data = response.json()
                # Remove embedding to save space
                if "embedding" in resp_data:
                    del resp_data["embedding"]
                return {
                    "status": "success",
                    "status_code": 200,
                    "response_time_ms": round(elapsed * 1000),
                    "response": resp_data
                }
            else:
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "response_time_ms": round(elapsed * 1000),
                    "response_error": response.text[:500]
                }

        except requests.exceptions.Timeout:
            return {"status": "error", "error_type": "timeout"}
        except requests.exceptions.ConnectionError as e:
            return {"status": "error", "error_type": "connection", "error_msg": str(e)[:200]}
        except Exception as e:
            return {"status": "error", "error_type": "unknown", "error_msg": str(e)[:200]}

    def run(self, dataset_path: str = DATASET_FILE, max_cases: Optional[int] = MAX_CASES):
        """Run the stress test."""
        # Load dataset
        print(f"Loading dataset from {dataset_path}...")
        with open(dataset_path) as f:
            dataset = json.load(f)

        cases = dataset.get("cases", [])
        total_cases = len(cases)

        if max_cases:
            cases = cases[:max_cases]
            print(f"Limited to {max_cases} cases")

        print(f"Total cases: {len(cases)}")
        print(f"Starting from index: {self.start_index}")
        print(f"Delay between requests: {self.delay} seconds")
        print(f"Endpoint: {self.endpoint}")
        print("=" * 70)

        # Skip already completed
        cases_to_run = cases[self.start_index:]

        if not cases_to_run:
            print("All cases already completed!")
            return

        # Estimate time
        estimated_time = len(cases_to_run) * self.delay
        print(f"Estimated time: {estimated_time // 3600}h {(estimated_time % 3600) // 60}m")
        print("=" * 70)

        for i, case in enumerate(cases_to_run):
            current_index = self.start_index + i
            case_id = case.get("id", f"Q{current_index:04d}")
            query = case.get("query", "")
            expected = case.get("expected", {})
            bucket = case.get("bucket", {})

            print(f"\n[{current_index + 1}/{total_cases}] {case_id}")
            print(f"  Query: {query[:60]}{'...' if len(query) > 60 else ''}")
            print(f"  Expected: {expected.get('primary_action', 'N/A')} (trigger={expected.get('should_trigger_action')})")
            print(f"  Bucket: {bucket.get('query_form')} / {bucket.get('noise_type')} / {bucket.get('difficulty')}")

            # Make request
            result = self.make_request(query)

            # Add metadata
            result["case_id"] = case_id
            result["query"] = query
            result["expected"] = expected
            result["bucket"] = bucket
            result["timestamp"] = datetime.now().isoformat()

            # Show result
            if result["status"] == "success":
                resp = result.get("response", {})
                action = resp.get("action") or resp.get("intent", "N/A")
                entities = resp.get("entities", [])
                lane = resp.get("lane", "?")
                print(f"  Result: SUCCESS ({result.get('response_time_ms')}ms) [Lane: {lane}]")
                print(f"  Action: {action} (conf: {resp.get('action_confidence', resp.get('intent_confidence', 0)):.2f})")
                entity_strs = [f"{e.get('type')}:{e.get('value')}" for e in entities[:3]]
                print(f"  Entities: {entity_strs}")

                # Check accuracy
                exp_trigger = expected.get("should_trigger_action", False)
                exp_action = expected.get("primary_action", "none_search_only")
                act_triggered = action is not None and action != "none_search_only"

                if exp_trigger == act_triggered and (not exp_trigger or action == exp_action):
                    print(f"  Match: CORRECT")
                elif not exp_trigger and act_triggered:
                    print(f"  Match: FALSE POSITIVE (expected no action)")
                elif exp_trigger and not act_triggered:
                    print(f"  Match: FALSE NEGATIVE (expected {exp_action})")
                else:
                    print(f"  Match: WRONG ACTION (expected {exp_action}, got {action})")
            else:
                print(f"  Result: ERROR - {result.get('status_code', result.get('error_type', 'unknown'))}")

            self.results.append(result)

            # Save progress periodically
            if (i + 1) % BATCH_SIZE == 0:
                self._save_progress(current_index + 1)
                self._save_results()
                summary = self._calculate_summary()
                print(f"\n  [Checkpoint {current_index + 1}] Accuracy: Action={summary['action_detection']['accuracy']}% Entity={summary['entity_extraction']['accuracy']}%")

            # Wait before next request (except for last one)
            if i < len(cases_to_run) - 1:
                for remaining in range(self.delay, 0, -1):
                    print(f"\r  Waiting: {remaining}s ", end="", flush=True)
                    time.sleep(1)
                print("\r" + " " * 20 + "\r", end="")

        # Final save
        self._save_progress(len(cases))
        self._save_results()

        # Print summary
        print("\n" + "=" * 70)
        print("STRESS TEST COMPLETE")
        print("=" * 70)
        summary = self._calculate_summary()
        print(json.dumps(summary, indent=2))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="CelesteOS Production Stress Test")
    parser.add_argument("--delay", type=int, default=DELAY_SECONDS, help="Seconds between requests")
    parser.add_argument("--max", type=int, default=None, help="Max cases to run")
    parser.add_argument("--reset", action="store_true", help="Reset progress and start fresh")

    args = parser.parse_args()

    if args.reset:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            print("Progress reset.")
        if os.path.exists(RESULTS_FILE):
            os.remove(RESULTS_FILE)
            print("Results reset.")

    runner = ProductionStressTest(delay=args.delay)
    runner.run(max_cases=args.max)


if __name__ == "__main__":
    main()
