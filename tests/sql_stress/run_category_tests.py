#!/usr/bin/env python3
"""Run tests from specific categories."""
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/sql_stress')
from stress_runner import run_batch, analyze_results, generate_report, TestResult, STRESS_TESTS_PATH, REPORT_PATH, RESULTS_PATH
from datetime import datetime

# Load all tests
with open(STRESS_TESTS_PATH) as f:
    data = json.load(f)
all_tests = data["tests"]

# Get tests by category
categories = {}
for t in all_tests:
    cat = t["category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(t)

print("Available categories:")
for cat, tests in sorted(categories.items()):
    print(f"  {cat}: {len(tests)} tests")

# Run sample from each category
sample_size = 10
all_results = []

for cat in sorted(categories.keys()):
    tests = categories[cat][:sample_size]
    print(f"\nRunning {len(tests)} tests from {cat}...")
    results = run_batch(tests, delay=0.5)
    all_results.extend(results)

    passed = sum(1 for r in results if r.status_code == 200)
    print(f"  Result: {passed}/{len(tests)} passed")

# Analyze and report
print("\nAnalyzing...")
analysis = analyze_results(all_results)
report = generate_report(analysis, all_results)

# Save
with open(RESULTS_PATH, "w") as f:
    json.dump({
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(all_results),
        "results": [r.to_dict() for r in all_results]
    }, f, indent=2)

with open(REPORT_PATH, "w") as f:
    f.write(report)

print(f"\nTotal: {analysis['summary']['total']}")
print(f"Passed: {analysis['summary']['passed']}")
print(f"Pass Rate: {analysis['summary']['pass_rate']}%")
