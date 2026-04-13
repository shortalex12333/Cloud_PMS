"""
auth.py — real JWT tokens via Supabase auth API.
No hardcoded tokens. Fresh auth every run.
"""
import requests

SUPABASE_URL  = "https://vzsohavtuotocgrfkfyd.supabase.co"
ANON_KEY      = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
AUTH_ENDPOINT = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"

USERS = {
    # role          email                                password
    "crew":         ("engineer.test@alex-short.com",         "Password2!"),  # role=crew,           dept=general
    "hod":          ("captain.tenant@alex-short.com",        "Password2!"),  # role=chief_engineer,  dept=engineering
    "captain":      ("x@alex-short.com",                     "Password2!"),  # role=captain,         dept=deck
    "fleet_manager":("fleet-test-1775570624@celeste7.ai",    "Password2!"),  # role=manager,         dept=interior
}

def get_token(role: str) -> dict:
    """Returns {"token": str, "user_id": str, "role": str} or raises."""
    if role not in USERS:
        raise ValueError(f"No test user configured for role: {role}")
    email, password = USERS[role]
    r = requests.post(
        AUTH_ENDPOINT,
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Auth failed for {role} ({email}): {r.status_code} {r.text}")
    data = r.json()
    return {
        "token":   data["access_token"],
        "user_id": data["user"]["id"],
        "role":    role,
        "email":   email,
    }

def get_all_tokens() -> dict:
    tokens = {}
    for role in USERS:
        try:
            tokens[role] = get_token(role)
            email = USERS[role][0]
            print(f"  ✓ Auth OK: {role} ({email}) uid={tokens[role]['user_id'][:8]}...")
        except Exception as e:
            tokens[role] = None
            print(f"  ✗ Auth FAILED: {role} — {e}")
    return tokens
