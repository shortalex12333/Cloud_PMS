"""
api.py — HTTP client for HoR endpoints.
All calls go to real API. Token passed per call. No session reuse.
"""
import requests
import os

API_BASE = os.environ.get("HOR_TEST_API_BASE", "http://localhost:8000")
TIMEOUT  = 15


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }


def get(path: str, token: str, params: dict = None) -> requests.Response:
    return requests.get(
        f"{API_BASE}{path}",
        headers=_headers(token),
        params=params or {},
        timeout=TIMEOUT,
    )


def post(path: str, token: str, body: dict = None) -> requests.Response:
    return requests.post(
        f"{API_BASE}{path}",
        headers=_headers(token),
        json=body or {},
        timeout=TIMEOUT,
    )
