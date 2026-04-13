"""
check.py — assertion helpers that return structured pass/fail dicts.
No exceptions thrown — every failure is recorded, not fatal.
"""

def ok(name: str) -> dict:
    return {"name": name, "pass": True}

def fail(name: str, expected, actual, error: str = "") -> dict:
    return {
        "name":     name,
        "pass":     False,
        "expected": str(expected),
        "actual":   str(actual),
        "error":    error,
    }

def expect_status(name: str, response, expected_status: int) -> dict:
    actual = response.status_code
    if actual == expected_status:
        return ok(name)
    return fail(name, f"HTTP {expected_status}", f"HTTP {actual}", response.text[:200])

def expect_field(name: str, data: dict, field: str, expected=None) -> dict:
    """Assert field exists and optionally matches expected value."""
    if field not in data:
        return fail(name, f"field '{field}' present", "field missing")
    if expected is not None and data[field] != expected:
        return fail(name, expected, data[field])
    return ok(name)

def expect_db_row(name: str, row, field: str = None, expected=None) -> dict:
    """Assert DB row exists and optionally a field matches."""
    if row is None:
        return fail(name, "row exists in DB", "row not found")
    if field and expected is not None:
        actual = row.get(field)
        if actual != expected:
            return fail(name, f"{field}={expected}", f"{field}={actual}")
    return ok(name)

def expect_forbidden(name: str, response) -> dict:
    if response.status_code == 403:
        return ok(name)
    return fail(name, "HTTP 403", f"HTTP {response.status_code}", response.text[:200])

def expect_error_code(name: str, response, code: str) -> dict:
    """Assert envelope error code matches — requires success=False and error.code=code."""
    try:
        body = response.json()
        actual_code = (body.get("error") or {}).get("code", "")
        if body.get("success") == False and actual_code == code:
            return ok(name)
        return fail(name, f"success=False + error.code={code}",
                    f"success={body.get('success')} code={actual_code}")
    except Exception as e:
        return fail(name, f"error.code={code}", "parse error", str(e))
