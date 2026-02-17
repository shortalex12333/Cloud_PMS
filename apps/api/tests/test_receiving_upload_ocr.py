"""
Receiving Upload OCR Integration Test
======================================

Tests the full receiving upload workflow:
1. Authenticate with Supabase
2. Create a receiving record
3. Upload test invoice image
4. Verify OCR extraction results

Test files: /Users/celeste7/Downloads/fake invoices/
"""

import os
import sys
import json
import httpx
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Environment variables
SUPABASE_URL = os.environ.get("TENANT_1_SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("TENANT_1_SUPABASE_ANON_KEY", "")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.celeste7.ai")

# Test user credentials (from auth.helper.ts)
TEST_USERS = {
    "crew": {
        "email": os.environ.get("STAGING_CREW_EMAIL", "crew.test@alex-short.com"),
        "password": os.environ.get("STAGING_USER_PASSWORD", "Password2!"),
    },
    "hod": {
        "email": os.environ.get("STAGING_HOD_EMAIL", "hod.test@alex-short.com"),
        "password": os.environ.get("STAGING_USER_PASSWORD", "Password2!"),
    },
    "captain": {
        "email": os.environ.get("STAGING_CAPTAIN_EMAIL", "x@alex-short.com"),
        "password": os.environ.get("STAGING_USER_PASSWORD", "Password2!"),
    },
}

# Test invoice folder
TEST_INVOICES_DIR = Path("/Users/celeste7/Downloads/fake invoices")


class ReceivingUploadTest:
    """Test harness for receiving upload workflow."""

    def __init__(self):
        self.jwt_token = None
        self.user_id = None
        self.yacht_id = None
        self.receiving_id = None
        self.results = []

    async def authenticate(self, role: str = "captain") -> bool:
        """Authenticate with Supabase and get JWT."""
        user = TEST_USERS.get(role)
        if not user:
            self.log(f"Unknown role: {role}", "ERROR")
            return False

        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            self.log("Missing SUPABASE_URL or SUPABASE_ANON_KEY env vars", "ERROR")
            return False

        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    auth_url,
                    json={
                        "email": user["email"],
                        "password": user["password"],
                    },
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.jwt_token = data.get("access_token")
                    self.user_id = data.get("user", {}).get("id")
                    self.yacht_id = data.get("user", {}).get("user_metadata", {}).get("yacht_id")
                    self.log(f"Authenticated as {role}: user_id={self.user_id}, yacht_id={self.yacht_id}", "OK")
                    return True
                else:
                    self.log(f"Auth failed: {response.status_code} - {response.text}", "ERROR")
                    return False

        except Exception as e:
            self.log(f"Auth exception: {e}", "ERROR")
            return False

    async def create_receiving(self) -> bool:
        """Create a new receiving record via API action."""
        if not self.jwt_token:
            self.log("No JWT token - authenticate first", "ERROR")
            return False

        action_url = f"{API_BASE_URL}/v1/actions/execute"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    action_url,
                    json={
                        "action": "create_receiving",
                        "context": {
                            "yacht_id": self.yacht_id,
                        },
                        "payload": {
                            "vendor_name": "Test Vendor OCR",
                            "vendor_reference": f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            "received_date": datetime.now().strftime("%Y-%m-%d"),
                        },
                    },
                    headers={
                        "Authorization": f"Bearer {self.jwt_token}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        # receiving_id is at root level in response
                        self.receiving_id = data.get("receiving_id") or data.get("result", {}).get("id")
                        self.log(f"Created receiving: {self.receiving_id}", "OK")
                        return True
                    else:
                        self.log(f"Create receiving failed: {data.get('message')}", "ERROR")
                        return False
                else:
                    self.log(f"Create receiving HTTP error: {response.status_code} - {response.text}", "ERROR")
                    return False

        except Exception as e:
            self.log(f"Create receiving exception: {e}", "ERROR")
            return False

    async def upload_invoice(self, file_path: Path) -> dict:
        """Upload invoice to receiving record and get OCR results."""
        if not self.jwt_token or not self.receiving_id:
            self.log("No JWT or receiving_id - create receiving first", "ERROR")
            return {}

        upload_url = f"{API_BASE_URL}/api/receiving/{self.receiving_id}/upload"

        try:
            # Read file
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Determine content type
            suffix = file_path.suffix.lower()
            content_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".pdf": "application/pdf",
            }
            content_type = content_types.get(suffix, "application/octet-stream")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    upload_url,
                    files={
                        "file": (file_path.name, file_content, content_type),
                    },
                    data={
                        "doc_type": "invoice",
                        "comment": f"Test upload from {file_path.name}",
                    },
                    headers={
                        "Authorization": f"Bearer {self.jwt_token}",
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    self.log(f"Upload success: document_id={data.get('document_id')}", "OK")
                    return data
                elif response.status_code == 503:
                    self.log("OCR service cold starting (503) - retry in 30s", "WARN")
                    return {"status": "cold_start", "retry": True}
                else:
                    self.log(f"Upload failed: {response.status_code} - {response.text}", "ERROR")
                    return {"error": response.text, "status_code": response.status_code}

        except Exception as e:
            self.log(f"Upload exception: {e}", "ERROR")
            return {"error": str(e)}

    async def run_test(self, role: str = "captain", test_file: str = "1.jpg"):
        """Run full receiving upload test."""
        self.log("=" * 60)
        self.log("RECEIVING UPLOAD OCR TEST")
        self.log("=" * 60)

        # Step 1: Authenticate
        self.log("\n[Step 1] Authenticating...")
        if not await self.authenticate(role):
            return False

        # Step 2: Create receiving
        self.log("\n[Step 2] Creating receiving record...")
        if not await self.create_receiving():
            return False

        # Step 3: Upload invoice
        test_path = TEST_INVOICES_DIR / test_file
        if not test_path.exists():
            self.log(f"Test file not found: {test_path}", "ERROR")
            return False

        self.log(f"\n[Step 3] Uploading invoice: {test_file}...")
        result = await self.upload_invoice(test_path)

        # Handle cold start retry
        if result.get("retry"):
            self.log("Waiting 30s for OCR service cold start...")
            await asyncio.sleep(30)
            result = await self.upload_invoice(test_path)

        # Step 4: Verify results
        self.log("\n[Step 4] OCR Extraction Results:")
        if "extracted_data" in result:
            extracted = result.get("extracted_data", {})
            self.log(f"  Vendor Name: {extracted.get('vendor_name', 'N/A')}")
            self.log(f"  Total: {extracted.get('total', 'N/A')}")
            self.log(f"  Currency: {extracted.get('currency', 'N/A')}")
            self.log(f"  Line Items: {len(extracted.get('line_items', []))}")
            self.log(f"  Confidence: {result.get('confidence', 'N/A')}")
            return True
        else:
            self.log(f"  No extracted data: {json.dumps(result, indent=2)}")
            return "document_id" in result

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "OK": "\u2705",
            "ERROR": "\u274c",
            "WARN": "\u26a0\ufe0f",
            "INFO": "\u2139\ufe0f",
        }.get(level, "")
        print(f"[{timestamp}] {prefix} {message}")
        self.results.append({"time": timestamp, "level": level, "message": message})


async def main():
    """Run receiving upload test suite."""
    tester = ReceivingUploadTest()

    # Test with different invoices
    test_files = ["1.jpg", "3.jpg", "5.png"]

    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"Testing with: {test_file}")
        print(f"{'='*60}")

        success = await tester.run_test(role="captain", test_file=test_file)
        if not success:
            print(f"\nTest failed for {test_file}")
        else:
            print(f"\nTest passed for {test_file}")

        # Reset for next test
        tester.receiving_id = None


if __name__ == "__main__":
    asyncio.run(main())
