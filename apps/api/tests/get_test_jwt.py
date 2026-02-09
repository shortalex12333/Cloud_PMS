#!/usr/bin/env python3
"""
Get JWT token for testing
Uses Supabase password grant to authenticate test user
"""

from supabase import create_client
import os

# TENANT_1 credentials
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.Qn_lmvW-tXiKCIvXLFgKBSlZn9_ZbYjMOBPpHsWJmxo"

# Test user credentials (from environment or default)
TEST_EMAIL = os.getenv("TEST_USER_EMAIL", "test@celeste7.ai")
TEST_PASSWORD = os.getenv("TEST_USER_PASSWORD", "testpassword123")

def get_jwt():
    """Authenticate and return JWT token"""

    print("Connecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Authenticating user: {TEST_EMAIL}")

    try:
        response = supabase.auth.sign_in_with_password({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })

        if response.session:
            jwt = response.session.access_token
            user_id = response.user.id
            yacht_id = response.user.user_metadata.get("yacht_id")

            print(f"\n✅ Authentication successful")
            print(f"User ID: {user_id}")
            print(f"Yacht ID: {yacht_id}")
            print(f"\nJWT Token (use this for tests):")
            print(f"{jwt}")
            print(f"\nExport for use:")
            print(f"export TEST_JWT_TOKEN='{jwt}'")

            return jwt
        else:
            print("❌ Authentication failed - no session returned")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTry creating a test user first:")
        print(f"  Email: {TEST_EMAIL}")
        print(f"  Password: {TEST_PASSWORD}")
        return None

if __name__ == "__main__":
    get_jwt()
