# CelesteOS Local Ingestion Pipeline - Implementation Guide

This directory contains the complete implementation of the CelesteOS local→cloud ingestion workflow as specified in `local-agent-ingestion.md` and `n8n-cloud-receiver.md`.

## 📁 Directory Structure

```
Cloud_PMS/
├── local-agent/                    # macOS Local Agent
│   ├── python-worker/              # Python worker modules
│   │   ├── manifest.py             # SQLite manifest database manager
│   │   ├── hasher.py               # SHA256 hashing
│   │   ├── chunker.py              # File chunking
│   │   ├── nas_scanner.py          # NAS file discovery
│   │   └── uploader.py             # Cloud upload handler
│   └── config/
│       └── config.template.json    # Agent configuration template
│
├── cloud/                          # Cloud Components
│   ├── supabase/
│   │   └── migrations/
│   │       ├── 001_initial_schema.sql      # Core tables
│   │       └── 002_documents_uploads.sql   # Document/upload tables
│   │
│   ├── n8n-workflows/              # n8n workflow JSON files
│   │   ├── upload-init-workflow.json
│   │   ├── upload-chunk-workflow.json
│   │   └── upload-complete-workflow.json
│   │
│   └── .env.example                # Environment variables template
│
└── IMPLEMENTATION_README.md        # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Supabase Account**: Sign up at https://supabase.com
2. **n8n Instance**: Self-hosted or cloud (https://n8n.io)
3. **OpenAI API Key**: For embeddings (https://platform.openai.com)
4. **macOS Computer**: For local agent (Mac Studio/Mac Mini on yacht)

### Step 1: Set Up Supabase Database

1. **Create a new Supabase project**

2. **Run migrations**:
   ```bash
   # Using Supabase CLI
   supabase db push

   # Or manually in Supabase SQL Editor:
   # - Run cloud/supabase/migrations/001_initial_schema.sql
   # - Run cloud/supabase/migrations/002_documents_uploads.sql
   ```

3. **Enable pgvector extension**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

4. **Create storage buckets**:
   - Go to Storage in Supabase dashboard
   - Create bucket: `yacht-uploads` (for temporary chunks)
   - Create bucket: `yacht-documents` (for final documents)
   - Set appropriate RLS policies

5. **Get credentials**:
   - Copy your Supabase URL
   - Copy your anon key
   - Copy your service role key

### Step 2: Set Up n8n Workflows

1. **Install n8n** (if self-hosting):
   ```bash
   npm install -g n8n
   ```

2. **Configure environment**:
   ```bash
   cd cloud
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Import workflows**:
   - Open n8n UI
   - Go to Workflows → Import
   - Import each JSON file from `cloud/n8n-workflows/`:
     - `upload-init-workflow.json`
     - `upload-chunk-workflow.json`
     - `upload-complete-workflow.json`

4. **Configure credentials in n8n**:
   - Add Postgres credentials (Supabase connection)
   - Add Supabase Storage credentials
   - Test each workflow

5. **Activate workflows**:
   - Ensure all three workflows are active
   - Note the webhook URLs (will be like `https://your-n8n.com/webhook/v1/ingest/init`)

### Step 3: Set Up Local Agent (macOS)

1. **Install Python dependencies**:
   ```bash
   cd local-agent/python-worker
   pip3 install -r requirements.txt
   ```

   Create `requirements.txt`:
   ```
   requests>=2.31.0
   ```

2. **Configure the agent**:
   ```bash
   cd local-agent/config
   cp config.template.json config.json
   # Edit config.json with your settings
   ```

   Update these fields:
   - `cloud.api_endpoint`: Your n8n webhook base URL
   - `cloud.yacht_signature`: Yacht signature from provisioning
   - `cloud.refresh_token`: Refresh token from provisioning
   - `nas.mount_point`: Your NAS mount path
   - `nas.watch_directories`: Directories to sync

3. **Mount NAS** (using SMB):
   ```bash
   # macOS Finder: Go → Connect to Server
   # Or via command line:
   mount -t smbfs //username:password@nas-ip/share /Volumes/CelesteOS_NAS
   ```

4. **Test the worker**:
   ```bash
   cd local-agent/python-worker
   python3 test_agent.py  # You'll need to create a test script
   ```

### Step 4: Create Test Script

Create `local-agent/python-worker/test_agent.py`:

```python
#!/usr/bin/env python3
"""
Test script for CelesteOS local agent
"""

import os
import logging
from manifest import ManifestDB
from nas_scanner import NASScanner
from hasher import FileHasher
from chunker import FileChunker
from uploader import CloudUploader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_workflow():
    """Test the complete ingestion workflow"""

    # Configuration (load from config.json in production)
    config = {
        'nas_mount': '/Volumes/CelesteOS_NAS',
        'api_endpoint': 'https://your-n8n.com/webhook',
        'yacht_signature': 'your-yacht-signature',
        'auth_token': 'your-jwt-token',
        'manifest_db': os.path.expanduser('~/Library/Application Support/CelesteOS/test_manifest.sqlite')
    }

    # 1. Initialize manifest database
    logger.info("Initializing manifest database...")
    manifest = ManifestDB(config['manifest_db'])

    # 2. Scan NAS
    logger.info("Scanning NAS...")
    scanner = NASScanner(config['nas_mount'])
    files = scanner.scan_directory(recursive=True)
    logger.info(f"Found {len(files)} files")

    # 3. Add files to manifest
    for file_meta in files:
        manifest.add_or_update_nas_file(
            file_path=file_meta['file_path'],
            nas_path=file_meta['nas_path'],
            file_size=file_meta['file_size'],
            last_modified=file_meta['last_modified'],
            extension=file_meta['extension'],
            mime_type=file_meta['mime_type']
        )

    # 4. Hash files
    logger.info("Computing hashes...")
    files_to_hash = manifest.get_files_needing_hash(limit=5)
    for file_info in files_to_hash:
        try:
            sha256 = FileHasher.compute_sha256(file_info['file_path'])
            manifest.update_file_hash(file_info['id'], sha256)
            logger.info(f"Hashed: {file_info['file_path']} -> {sha256[:16]}...")
        except Exception as e:
            logger.error(f"Failed to hash {file_info['file_path']}: {e}")

    # 5. Queue files for upload
    logger.info("Queuing files for upload...")
    files_to_upload = manifest.get_files_for_upload_queue(limit=1)

    if files_to_upload:
        file_info = files_to_upload[0]

        # 6. Chunk file
        logger.info(f"Chunking file: {file_info['filename']}")
        chunker = FileChunker(chunk_size=10*1024*1024)  # 10MB chunks
        chunks = chunker.create_chunks(file_info['file_path'], file_info['sha256'])

        # 7. Create upload queue entry
        queue_id = manifest.create_upload_queue_entry(file_info['id'], len(chunks))

        # Add chunks to manifest
        for chunk in chunks:
            manifest.add_chunk_to_queue(
                queue_id=queue_id,
                chunk_index=chunk['chunk_index'],
                chunk_sha256=chunk['chunk_sha256'],
                chunk_size=chunk['chunk_size'],
                chunk_path=chunk['chunk_path']
            )

        # 8. Upload to cloud
        logger.info("Uploading to cloud...")
        uploader = CloudUploader(
            api_endpoint=config['api_endpoint'],
            yacht_signature=config['yacht_signature'],
            auth_token=config['auth_token']
        )

        try:
            result = uploader.upload_file_with_chunks(
                file_path=file_info['file_path'],
                file_sha256=file_info['sha256'],
                chunks=chunks,
                nas_path=file_info['nas_path'],
                progress_callback=lambda idx, total: logger.info(f"Progress: {idx}/{total}")
            )

            if result['success']:
                manifest.mark_upload_complete(queue_id, result['document_id'])
                logger.info(f"Upload successful: {result['document_id']}")

                # Cleanup chunks
                chunker.cleanup_chunks(chunks)

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            manifest.mark_upload_failed(queue_id, str(e))

    # 9. Print stats
    stats = manifest.get_stats()
    logger.info(f"Manifest stats: {stats}")

    manifest.close()

if __name__ == '__main__':
    test_workflow()
```

## 🔒 Security Setup

### 1. JWT Token Generation

You'll need to create an endpoint to generate JWT tokens for local agents. Example:

```python
import jwt
from datetime import datetime, timedelta

def generate_tokens(yacht_id, user_id):
    access_token = jwt.encode({
        'yacht_id': yacht_id,
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, JWT_SECRET, algorithm='HS256')

    refresh_token = jwt.encode({
        'yacht_id': yacht_id,
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=30)
    }, JWT_SECRET, algorithm='HS256')

    return access_token, refresh_token
```

### 2. Row-Level Security (RLS) Policies

Add to Supabase:

```sql
-- Policy for yacht isolation
CREATE POLICY yacht_isolation_policy ON documents
    FOR ALL
    USING (yacht_id = current_setting('app.current_yacht_id')::uuid);

-- Similar policies for all tables with yacht_id
```

### 3. macOS Keychain Integration

Store yacht signature and NAS credentials in macOS Keychain:

```python
import keyring

# Store
keyring.set_password('com.celesteos.agent', 'yacht_signature', 'YOUR_SIGNATURE')

# Retrieve
yacht_signature = keyring.get_password('com.celesteos.agent', 'yacht_signature')
```

## 📊 Monitoring & Logs

### Local Agent Logs

```bash
# View logs
tail -f ~/Library/Logs/CelesteOS/agent.log

# View manifest stats
sqlite3 ~/Library/Application\ Support/CelesteOS/manifest.sqlite \
  "SELECT status, COUNT(*) FROM nas_files GROUP BY status;"
```

### Cloud Logs

- **n8n**: Check workflow execution logs in n8n UI
- **Supabase**: Query `pipeline_logs` table
- **Metrics**: Query `event_log` and `search_queries` tables

## 🐛 Troubleshooting

### NAS Not Mounting

```bash
# Check if NAS is reachable
ping nas-ip

# Remount
umount /Volumes/CelesteOS_NAS
mount -t smbfs //user:pass@nas-ip/share /Volumes/CelesteOS_NAS
```

### Upload Failures

1. Check n8n workflow is active
2. Verify JWT token is valid
3. Check yacht signature matches
4. Verify Supabase credentials
5. Check network connectivity

### SHA256 Mismatches

- File may have been modified during upload
- Network corruption (check Starlink connection)
- Verify chunk assembly logic in n8n

## 📚 Next Steps

1. **Create macOS GUI app** using Swift (see `agent-spec.md`)
2. **Implement LaunchAgent daemon** for background operation
3. **Add auto-update mechanism**
4. **Implement indexing pipeline** (see `indexing-pipeline.md`)
5. **Add email ingestion** (optional)
6. **Set up monitoring/alerting**

## 📝 Documentation References

- `local-agent-ingestion.md` - Complete local agent specification
- `n8n-cloud-receiver.md` - Cloud receiver workflow specification
- `agent-spec.md` - macOS app specification
- `api-spec.md` - API endpoint definitions
- `security.md` - Security requirements
- `table_configs.md` - Database schema

## 🤝 Support

For issues or questions, see the project documentation or contact the engineering team.

---

**Last Updated**: 2025-11-20
**Version**: 1.0.0
