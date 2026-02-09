#!/usr/bin/env python3
"""Test image upload with multipart/form-data"""
import requests

API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
PART_ID = "5dd34337-c4c4-41dd-9c6b-adf84af349a8"  # TEAK_COMPOUND

# Captain JWT (expires 2025-02-09)
CAPTAIN_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ1MzI2LCJpYXQiOjE3NzA2NDE3MjYsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MTcyNn1dLCJzZXNzaW9uX2lkIjoiMTFkNjI1YTAtNGQyMS00NDZkLWJhODktOWM5ZThhOGU2ZWVkIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.3ltGmlehSM2kEgUpBgjzL1wsHRugoTpCldwmBEkoop4"

headers = {"Authorization": f"Bearer {CAPTAIN_JWT}"}

# Multipart form data
files = {
    "file": ("test-image.png", open("test-results/test-image.png", "rb"), "image/png")
}

data = {
    "part_id": PART_ID,
    "yacht_id": YACHT_ID,
    "description": "E2E test - captain upload via multipart"
}

print("🧪 Testing image upload with multipart/form-data...")
print(f"   Endpoint: {API_BASE}/v1/parts/upload-image")
print(f"   Part: {PART_ID}")
print(f"   Yacht: {YACHT_ID}")

response = requests.post(
    f"{API_BASE}/v1/parts/upload-image",
    headers=headers,
    files=files,
    data=data,
    timeout=30
)

print(f"\n📊 Response: HTTP {response.status_code}")
print(f"   Body: {response.text[:500]}")

if response.status_code == 200:
    print("\n✅ Upload successful!")
    result = response.json()
    print(f"   Storage path: {result.get('storage_path', 'N/A')}")
    print(f"   Image URL: {result.get('image_url', 'N/A')[:80]}...")
else:
    print(f"\n❌ Upload failed: {response.status_code}")
