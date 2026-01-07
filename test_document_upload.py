"""
Test Document Upload to Cloud_PMS API
Simulates Local Agent uploading documents to cloud

Tests:
1. Upload test documents to /webhook/ingest-docs-nas-cloud
2. Verify duplicate detection
3. Check document metadata insertion
4. (Optional) Test indexing endpoint
"""

import os
import json
import httpx
import hashlib
from pathlib import Path

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")  # Change to Render URL when deployed
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # Test yacht ID
TEST_DOCS_DIR = Path(__file__).parent / "test_documents"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


async def upload_document(file_path: Path, system_path: str = "", doc_type: str = "general"):
    """
    Upload a document to the cloud API

    Args:
        file_path: Path to file
        system_path: System classification path (e.g., "02_ENGINEERING/fuel_systems")
        doc_type: Document type classification
    """
    print(f"\n{'='*60}")
    print(f"Uploading: {file_path.name}")
    print(f"{'='*60}")

    # Read file
    with open(file_path, "rb") as f:
        file_content = f.read()

    file_size = len(file_content)
    sha256 = calculate_sha256(file_path)

    # Determine content type
    content_type = "text/plain"
    if file_path.suffix == ".pdf":
        content_type = "application/pdf"
    elif file_path.suffix in [".doc", ".docx"]:
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Build metadata
    metadata = {
        "yacht_id": YACHT_ID,
        "filename": file_path.name,
        "content_type": content_type,
        "file_size": file_size,
        "system_path": system_path,
        "directories": system_path.split("/") if system_path else [],
        "doc_type": doc_type,
        "system_tag": doc_type,
        "local_path": str(file_path),
        "sha256": sha256
    }

    print(f"File size: {file_size:,} bytes")
    print(f"SHA-256: {sha256}")
    print(f"Content type: {content_type}")
    print(f"System path: {system_path or '(root)'}")

    # Upload to API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {
                "file": (file_path.name, file_content, content_type)
            }
            data = {
                "data": json.dumps(metadata)
            }

            response = await client.post(
                f"{API_URL}/webhook/ingest-docs-nas-cloud",
                files=files,
                data=data
            )

            print(f"\nResponse status: {response.status_code}")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")

            if result.get("status") == "success":
                print(f"\n✅ SUCCESS: Document uploaded")
                print(f"   Document ID: {result.get('document_id')}")
                print(f"   Storage path: {result.get('storage_path')}")
                return result
            elif result.get("status") == "duplicate":
                print(f"\n⚠️  DUPLICATE: File already exists")
                print(f"   Document ID: {result.get('document_id')}")
                return result
            else:
                print(f"\n❌ ERROR: Upload failed")
                print(f"   Message: {result.get('message')}")
                return result

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        return {"status": "error", "message": str(e)}


async def test_duplicate_detection(file_path: Path):
    """Test that uploading the same file twice is detected as duplicate"""
    print(f"\n{'='*60}")
    print(f"TESTING DUPLICATE DETECTION")
    print(f"{'='*60}")

    print("\nFirst upload (should succeed):")
    result1 = await upload_document(file_path)

    print("\nSecond upload (should detect duplicate):")
    result2 = await upload_document(file_path)

    if result2.get("status") == "duplicate":
        print("\n✅ Duplicate detection PASSED")
    else:
        print("\n❌ Duplicate detection FAILED")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CelesteOS Document Upload Test")
    print("="*60)
    print(f"API URL: {API_URL}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Test docs: {TEST_DOCS_DIR}")

    # Check if test documents exist
    if not TEST_DOCS_DIR.exists():
        print(f"\n❌ ERROR: Test documents directory not found: {TEST_DOCS_DIR}")
        return

    test_files = list(TEST_DOCS_DIR.glob("*.txt"))
    if not test_files:
        print(f"\n❌ ERROR: No test files found in {TEST_DOCS_DIR}")
        return

    print(f"\nFound {len(test_files)} test files:")
    for f in test_files:
        print(f"  - {f.name}")

    # Test 1: Upload engine manual
    print("\n" + "="*60)
    print("TEST 1: Upload Engine Manual")
    print("="*60)
    await upload_document(
        TEST_DOCS_DIR / "engine_manual.txt",
        system_path="02_ENGINEERING/engines",
        doc_type="manual"
    )

    # Test 2: Upload HVAC service log
    print("\n" + "="*60)
    print("TEST 2: Upload HVAC Service Log")
    print("="*60)
    await upload_document(
        TEST_DOCS_DIR / "hvac_service_log.txt",
        system_path="02_ENGINEERING/hvac",
        doc_type="service_log"
    )

    # Test 3: Upload safety checklist
    print("\n" + "="*60)
    print("TEST 3: Upload Safety Checklist")
    print("="*60)
    await upload_document(
        TEST_DOCS_DIR / "safety_checklist.txt",
        system_path="01_OPERATIONS/safety",
        doc_type="checklist"
    )

    # Test 4: Duplicate detection
    print("\n" + "="*60)
    print("TEST 4: Duplicate Detection")
    print("="*60)
    await test_duplicate_detection(TEST_DOCS_DIR / "engine_manual.txt")

    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
