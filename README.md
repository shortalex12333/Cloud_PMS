# CelesteOS Local Agent

**Version:** 1.1.0
**Platform:** macOS 12.0+ (Monterey or later)
**Purpose:** Yacht NAS document sync agent for CelesteOS cloud

---

## Quick Install

```bash
# Clone or download the local-agent folder
cd local-agent

# Run the installer
chmod +x scripts/install.sh
./scripts/install.sh
```

This installs to `~/.celesteos/` and creates a background service.

---

## What It Does

The CelesteOS Local Agent is a lightweight daemon that runs on the yacht's Mac Studio. It:

1. **Scans** the NAS for engineering documents
2. **Hashes** each file with SHA256 for integrity
3. **Detects** new, modified, and deleted files
4. **Chunks** large files into 64MB segments
5. **Compresses** chunks with gzip
6. **Uploads** to the CelesteOS cloud
7. **Retries** failed uploads with exponential backoff
8. **Logs** all activity for debugging

**The agent does NOT perform:**
- OCR
- Text extraction
- Embedding generation
- AI inference

All intelligence happens in the cloud.

---

## 🔧 Installation

### Prerequisites

- macOS 12.0+ (Monterey or later)
- Python 3.9+
- Network access to NAS (SMB/NFS)
- Valid CelesteOS yacht signature

### Quick Install

```bash
cd local-agent
chmod +x scripts/install.sh
./scripts/install.sh
```

This will:
1. Install Python dependencies
2. Create necessary directories
3. Initialize SQLite database
4. Install launchd daemon
5. Launch setup GUI

### Manual Install

```bash
# Install dependencies
pip3 install -r requirements.txt

# Initialize database
python3 -c "from celesteos_agent.database import Database; Database().init()"

# Configure agent
python3 celesteos_cli.py setup

# Start daemon
python3 celesteos_daemon.py start
```

---

## ⚙️ Configuration

### Initial Setup

On first launch, you'll be prompted for:

1. **Yacht Signature** - Unique identifier from CelesteOS admin
2. **API Endpoint** - Cloud API URL (e.g., `https://api.celesteos.io`)
3. **NAS Path** - Path to NAS mount (e.g., `/Volumes/YachtNAS/Engineering`)
4. **NAS Type** - SMB, NFS, or local
5. **NAS Credentials** - Username (stored securely in Keychain)

### Configuration File

Located at: `~/.celesteos/config.json`

```json
{
  "yacht_signature": "ABC123XYZ",
  "api_endpoint": "https://api.celesteos.io",
  "nas_path": "/Volumes/YachtNAS/Engineering",
  "nas_type": "smb",
  "scan_interval_minutes": 15,
  "chunk_size_mb": 64,
  "max_concurrent_uploads": 3,
  "log_level": "INFO"
}
```

**Note:** NAS password is stored in macOS Keychain, never in config file.

---

## 🚀 Usage

### CLI Commands

```bash
# Start daemon
celesteos-agent start

# Stop daemon
celesteos-agent stop

# Check status
celesteos-agent status

# Force full scan
celesteos-agent scan --full

# View recent activity
celesteos-agent activity --limit 50

# View upload queue
celesteos-agent queue

# Retry failed uploads
celesteos-agent retry

# View errors
celesteos-agent errors

# Test NAS connection
celesteos-agent test-nas

# Reset database (DANGER)
celesteos-agent reset --confirm
```

### GUI Application

Launch the native macOS app:

```bash
open /Applications/CelesteOS\ Agent.app
```

Features:
- Setup wizard
- Real-time sync status
- Upload progress
- Error viewer
- Settings management

---

## 📊 Monitoring

### Status Screen

The GUI shows:

- **Files Scanned:** Total files discovered
- **Files Queued:** Waiting for upload
- **Uploads Active:** Currently uploading
- **Uploads Complete:** Successfully uploaded
- **Errors:** Failed uploads or scan errors
- **Last Scan:** Timestamp of last NAS scan
- **Next Scan:** Countdown to next scheduled scan

### Logs

Logs are written to:

```
~/.celesteos/logs/celesteos-agent.log
```

Log rotation: Daily, 7-day retention

View logs:

```bash
tail -f ~/.celesteos/logs/celesteos-agent.log
```

---

## 🔄 How It Works

### 1. NAS Scanning

- **Full Scan:** Every 15 minutes (configurable)
- **Deep Scan:** Every 1 hour with hash verification
- **File Watcher:** Real-time detection of changes (if supported)

Ignores:
- Hidden files (`.DS_Store`, `.Spotlight-V100`)
- Temp files (`~$*`, `*.tmp`)
- System folders (`$RECYCLE.BIN`, `.Trash`)

### 2. Change Detection

For each file:
1. Compute SHA256 hash
2. Compare with previous hash in database
3. Mark as:
   - **New** - Never seen before
   - **Modified** - Hash changed
   - **Unchanged** - Hash matches
   - **Deleted** - No longer exists

### 3. File Chunking

Files larger than 64MB are chunked:

1. Split into 64MB chunks
2. Compress each chunk with gzip
3. Compute SHA256 per chunk
4. Store in `~/.celesteos/tmp/`
5. Upload sequentially

### 4. Upload Process

For each file:

```
1. POST /v1/ingest/init
   └─> Receive upload_id

2. PATCH /v1/ingest/upload_chunk (for each chunk)
   └─> Headers: Upload-ID, Chunk-Index, Chunk-SHA256
   └─> Body: Compressed chunk bytes

3. POST /v1/ingest/complete
   └─> Signal cloud to assemble & verify
```

### 5. Retry Logic

If upload fails:

| Attempt | Delay   |
|---------|---------|
| 1       | 5s      |
| 2       | 10s     |
| 3       | 30s     |
| 4       | 2min    |
| 5       | 5min    |
| 6+      | Error   |

After 5 retries, job moves to "error" state and requires manual retry.

### 6. Crash Recovery

On daemon restart:
- Resume incomplete uploads
- Re-scan NAS for new changes
- Cleanup orphaned temp chunks
- Log recovery status

---

## 🔐 Security

### Credentials Storage

- **NAS Password:** macOS Keychain (encrypted)
- **Yacht Signature:** Config file (read-only)
- **API Tokens:** Not stored locally (yacht signature used for auth)

### File Access

- **NAS:** Read-only access
- **Temp Files:** Deleted immediately after upload
- **Logs:** Local only, never uploaded

### Network Security

- **HTTPS Only:** All API calls use TLS 1.3
- **SHA256 Verification:** Every file and chunk
- **Yacht Signature:** Validates all requests

---

## 🐛 Troubleshooting

### Common Issues

**Agent won't start**
```bash
# Check logs
cat ~/.celesteos/logs/celesteos-agent.log

# Verify database
python3 celesteos_cli.py check-db

# Test NAS connection
python3 celesteos_cli.py test-nas
```

**Files not uploading**
```bash
# Check queue
python3 celesteos_cli.py queue

# Check errors
python3 celesteos_cli.py errors

# Retry failed uploads
python3 celesteos_cli.py retry
```

**NAS connection fails**
```bash
# Verify mount
ls -la /Volumes/YachtNAS

# Test SMB
smbutil status -ae

# Check credentials
security find-generic-password -s "CelesteOS NAS"
```

**High CPU usage**
- Reduce scan frequency in settings
- Reduce `max_concurrent_uploads`
- Check for large files being hashed repeatedly

---

## 📦 Building DMG Installer

```bash
cd gui/swift
xcodebuild -project CelesteOSAgent.xcodeproj -scheme CelesteOSAgent -configuration Release

# Create DMG
create-dmg \
  --volname "CelesteOS Agent Installer" \
  --volicon "Assets.xcassets/AppIcon.appiconset/icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "CelesteOS Agent.app" 200 190 \
  --hide-extension "CelesteOS Agent.app" \
  --app-drop-link 600 185 \
  "CelesteOS-Agent-Installer.dmg" \
  "build/Release/CelesteOS Agent.app"
```

---

## 🧪 Development

### Running Tests

```bash
# All tests
pytest tests/

# Specific test
pytest tests/test_scanner.py -v

# With coverage
pytest --cov=celesteos_agent tests/
```

### Debug Mode

```bash
# Enable debug logging
export CELESTEOS_LOG_LEVEL=DEBUG
python3 celesteos_daemon.py start
```

---

## 📝 Architecture Notes

### State Machine

Upload jobs progress through states:

```
pending → initializing → uploading → completing → complete
   ↓            ↓            ↓            ↓
 error ←——————————————————————————————————
```

### Database Schema

See `schema.sql` for complete schema.

Key tables:
- `files` - All discovered files
- `upload_queue` - Active/pending uploads
- `upload_chunks` - Individual chunk status
- `errors` - Error log
- `sync_state` - Overall health metrics

### Threading Model

- **Main Thread:** Scheduler & orchestration
- **Scanner Thread:** NAS filesystem walking
- **Hasher Pool:** Parallel SHA256 computation (4 workers)
- **Upload Pool:** Parallel uploads (3 workers)
- **Watcher Thread:** Real-time file change detection

---

## 🔄 Auto-Update

The agent checks for updates daily:

```
POST /v1/agent/check-update
Response: { "version": "1.1.0", "download_url": "..." }
```

If newer version available:
1. Download new DMG
2. Verify signature
3. Prompt user to install
4. Silent install if configured

---

## 🆘 Support

**Documentation:** https://docs.celesteos.io/local-agent
**Issues:** Report to yacht's CelesteOS admin
**Logs:** Always include `celesteos-agent.log` when reporting issues

---

## 📄 License

Proprietary - CelesteOS Inc.
