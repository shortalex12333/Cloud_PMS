#!/usr/bin/env python3
"""
CelesteOS MVP Uploader with NAS Metadata
Uploads files with directory structure metadata for yacht-aware storage.
Worker 4 - Local Agent Engineer
"""

import os
import json
import sys
from pathlib import Path
import requests
from datetime import datetime
import mimetypes


def load_config(config_path='config.json'):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Validate required fields
        required = ['yacht_id', 'root_path']
        for field in required:
            if field not in config:
                print(f"❌ ERROR: Missing required field '{field}' in config.json")
                sys.exit(1)

        return config
    except FileNotFoundError:
        print(f"❌ ERROR: Config file not found: {config_path}")
        print("Create config.json with yacht_id and root_path")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in config file: {e}")
        sys.exit(1)


def extract_directory_metadata(file_path, root_path):
    """Extract directory hierarchy metadata from file path.

    Args:
        file_path: Absolute path to file (Path object)
        root_path: Root NAS path (Path object)

    Returns:
        dict with 'directories' (list) and 'system_path' (string)

    Example:
        file_path: /Users/celeste7/Documents/yacht-nas/ROOT/Engineering/MainEngine/manual.pdf
        root_path: /Users/celeste7/Documents/yacht-nas/ROOT

        Returns:
            {
                'directories': ['Engineering', 'MainEngine'],
                'system_path': 'Engineering/MainEngine'
            }
    """
    try:
        # Get relative path from root
        relative_path = file_path.relative_to(root_path)

        # Extract directory parts (exclude the filename)
        directories = list(relative_path.parts[:-1])

        # Create system_path string
        system_path = "/".join(directories) if directories else ""

        return {
            'directories': directories,
            'system_path': system_path
        }
    except ValueError:
        # File is not under root_path
        print(f"   ⚠️  WARNING: File not under root_path: {file_path}")
        return {
            'directories': [],
            'system_path': ''
        }


def scan_folder(root_path):
    """Recursively scan folder and return list of file paths."""
    folder = Path(root_path).expanduser()

    if not folder.exists():
        print(f"❌ ERROR: Folder does not exist: {folder}")
        sys.exit(1)

    if not folder.is_dir():
        print(f"❌ ERROR: Path is not a directory: {folder}")
        sys.exit(1)

    print(f"📁 Scanning folder: {folder}")

    files = []
    for file_path in folder.rglob('*'):
        if file_path.is_file():
            # Skip hidden files and system files
            if not file_path.name.startswith('.'):
                files.append(file_path)

    print(f"✓ Found {len(files)} files")
    return files


def upload_file(file_path, yacht_id, root_path, webhook_url):
    """Upload a single file to the n8n webhook with metadata.

    Args:
        file_path: Path object for the file
        yacht_id: Yacht identifier
        root_path: Path object for NAS root
        webhook_url: Webhook endpoint URL
    """
    filename = file_path.name
    local_path = str(file_path.absolute())

    # Extract directory metadata
    metadata = extract_directory_metadata(file_path, root_path)
    directories = metadata['directories']
    system_path = metadata['system_path']

    print(f"\n📤 Uploading: {filename}")
    print(f"   Path: {local_path}")
    print(f"   Size: {file_path.stat().st_size} bytes")
    print(f"   System Path: {system_path if system_path else '(root level)'}")
    print(f"   Directories: {directories}")

    try:
        # Prepare headers
        headers = {
            'X-Yacht-ID': yacht_id
        }

        # Detect mime type based on file extension
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        # Prepare multipart form data
        with open(file_path, 'rb') as f:
            files_payload = {
                'file': (filename, f, mime_type)
            }

            # Form data with all metadata
            data = {
                'filename': filename,
                'local_path': local_path,
                'system_path': system_path,
                'directories': json.dumps(directories),
                'yacht_id': yacht_id,
                'file_size': str(file_path.stat().st_size),
                'content_type': mime_type
            }

            # Send POST request
            response = requests.post(
                webhook_url,
                headers=headers,
                files=files_payload,
                data=data,
                timeout=60
            )

        # Check response
        if response.status_code == 200:
            print(f"   ✅ SUCCESS (200 OK)")
            try:
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}")
            return True
        else:
            print(f"   ❌ FAILED ({response.status_code})")
            print(f"   Response: {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        print(f"   ❌ FAILED (Timeout)")
        return False

    except requests.exceptions.RequestException as e:
        print(f"   ❌ FAILED (Network error: {e})")
        return False

    except Exception as e:
        print(f"   ❌ FAILED (Error: {e})")
        return False


def main():
    """Main execution function."""
    print("=" * 60)
    print("CelesteOS MVP Uploader with NAS Metadata")
    print("Testing n8n webhook ingestion")
    print("=" * 60)
    print()

    # Load configuration
    config = load_config()

    yacht_id = config['yacht_id']
    root_path = Path(config['root_path']).expanduser()
    webhook_url = config.get('webhook_url', 'https://api.celeste7.ai/webhook/ingest-docs-nas-cloud')

    print(f"Yacht ID: {yacht_id}")
    print(f"Root Path: {root_path}")
    print(f"Webhook: {webhook_url}")
    print()

    # Scan folder
    files = scan_folder(root_path)

    if not files:
        print("\n⚠️  No files found to upload")
        sys.exit(0)

    # Upload files
    print(f"\n{'=' * 60}")
    print("Starting uploads...")
    print(f"{'=' * 60}")

    successful = 0
    failed = 0

    for file_path in files:
        success = upload_file(file_path, yacht_id, root_path, webhook_url)
        if success:
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("UPLOAD SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total files: {len(files)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print()

    if failed > 0:
        print("⚠️  Some uploads failed. Check the output above for details.")
        sys.exit(1)
    else:
        print("🎉 All uploads successful!")
        sys.exit(0)


if __name__ == '__main__':
    main()
