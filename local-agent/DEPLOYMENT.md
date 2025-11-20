# CelesteOS Local Agent - Deployment Guide

**Version:** 1.0
**Target Platform:** macOS 12.0+ (Mac Studio / Mac Mini)
**Deployment Environment:** Yacht onboard network

---

## Pre-Deployment Checklist

### Hardware Requirements

- **Mac Studio** or **Mac Mini** (Apple Silicon or Intel)
- **macOS 12.0+** (Monterey or later)
- **8GB RAM minimum** (16GB recommended)
- **50GB free disk space** (for temporary chunks)
- **Network connectivity** to yacht NAS and internet

### Network Requirements

- **NAS Access:** SMB or NFS connectivity to yacht NAS
- **Internet Access:** HTTPS connectivity to CelesteOS cloud API
- **Firewall:** Port 443 (HTTPS) outbound allowed

### Prerequisites

1. **Python 3.9+** installed
2. **NAS credentials** (username/password)
3. **CelesteOS yacht signature** (obtained from CelesteOS admin)
4. **Cloud API endpoint** (provided by CelesteOS)

---

## Installation Steps

### Step 1: Download Agent

```bash
# Clone or download the agent code
cd /Applications
git clone https://github.com/celesteos/local-agent.git
cd local-agent
```

### Step 2: Run Installer

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

The installer will:
1. Check Python version
2. Install Python dependencies
3. Create required directories
4. Initialize database
5. Create command-line shortcuts
6. Install launchd service
7. Run setup wizard

### Step 3: Complete Setup Wizard

Answer the following prompts:

1. **Yacht Signature:** Enter the unique signature from CelesteOS admin
2. **Yacht Name:** Enter yacht name (e.g., "STELLA MARIS")
3. **API Endpoint:** Enter cloud API URL (e.g., `https://api.celesteos.io`)
4. **NAS Mount Path:** Path to NAS (e.g., `/Volumes/YachtNAS/Engineering`)
5. **NAS Type:** Select `smb`, `nfs`, or `local`
6. **NAS Credentials:**
   - Hostname/IP
   - Share name
   - Username
   - Password (stored securely in macOS Keychain)

### Step 4: Verify Configuration

```bash
# Test NAS connectivity
celesteos-agent test-nas

# Check configuration
cat ~/.celesteos/config.json
```

### Step 5: Start the Daemon

```bash
# Load and start the agent
launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist

# Verify it's running
celesteos-agent status
```

---

## Post-Installation Verification

### Check Daemon Status

```bash
celesteos-agent status
```

Expected output:
```
CelesteOS Agent Status

Yacht: STELLA MARIS
Signature: ABC123XYZ

Daemon Status: RUNNING

File Statistics
┌─────────────────┬───────┐
│ Metric          │ Count │
├─────────────────┼───────┤
│ Files Uploaded  │ 0     │
│ Files Pending   │ X     │
│ Files Uploading │ 0     │
│ Files Error     │ 0     │
│ Active Uploads  │ 0     │
└─────────────────┴───────┘
```

### Monitor Initial Scan

```bash
# Watch logs in real-time
tail -f ~/.celesteos/logs/celesteos-agent.log

# Or use CLI
celesteos-agent logs
```

Expected log entries:
```
2024-XX-XX 10:00:00 | INFO | Starting NAS scan
2024-XX-XX 10:00:05 | INFO | Scanned 100 files...
2024-XX-XX 10:00:10 | INFO | Scanned 200 files...
2024-XX-XX 10:01:00 | INFO | Scan completed: 532 files discovered
2024-XX-XX 10:01:05 | INFO | Queueing 532 files for upload
2024-XX-XX 10:01:10 | INFO | Upload initialized: Manual_CAT3516.pdf
```

### Check Upload Queue

```bash
celesteos-agent queue
```

Should show pending uploads with progress.

### View Recent Activity

```bash
celesteos-agent activity
```

---

## Configuration Files

### Main Config

**Location:** `~/.celesteos/config.json`

```json
{
  "yacht_signature": "ABC123XYZ",
  "yacht_name": "STELLA MARIS",
  "api_endpoint": "https://api.celesteos.io",
  "nas_path": "/Volumes/YachtNAS/Engineering",
  ...
}
```

**Permissions:** 600 (owner read/write only)

### Database

**Location:** `~/.celesteos/celesteos.db`

SQLite database containing:
- File registry
- Upload queue
- Error logs
- Activity history

**Backup recommended:** Copy this file for disaster recovery

### Logs

**Location:** `~/.celesteos/logs/celesteos-agent.log`

**Rotation:** Daily, 7-day retention

**Format:** JSON (for easy parsing)

---

## Operational Commands

### Daemon Management

```bash
# Start daemon
launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist

# Stop daemon
launchctl unload ~/Library/LaunchAgents/com.celesteos.agent.plist

# Restart daemon
launchctl unload ~/Library/LaunchAgents/com.celesteos.agent.plist
launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist

# Check if daemon is running
launchctl list | grep celesteos
```

### Status & Monitoring

```bash
# Overall status
celesteos-agent status

# Upload queue
celesteos-agent queue

# Recent activity
celesteos-agent activity

# Errors
celesteos-agent errors

# Logs (last 50 lines)
celesteos-agent logs
```

### Manual Operations

```bash
# Test NAS connectivity
celesteos-agent test-nas

# Retry failed uploads
celesteos-agent retry

# Force scan (requires daemon running)
celesteos-agent scan --full
```

---

## Troubleshooting

### Daemon Won't Start

**Symptoms:** Status shows "stopped" or "error"

**Diagnosis:**
```bash
# Check launchd logs
cat ~/Library/Logs/celesteos-agent.log

# Check daemon stderr
cat ~/.celesteos/logs/daemon-stderr.log

# Verify Python path
which python3

# Check dependencies
python3 -m pip list | grep celesteos
```

**Common fixes:**
- Reinstall dependencies: `pip3 install -r requirements.txt`
- Check Python version: Must be 3.9+
- Verify config: `cat ~/.celesteos/config.json`

### NAS Connection Fails

**Symptoms:** "NAS connectivity test failed"

**Diagnosis:**
```bash
# Check mount
ls -la /Volumes/YachtNAS

# Test SMB
smbutil status -ae

# Verify credentials
celesteos-agent test-nas
```

**Common fixes:**
- Verify NAS is powered on and network-accessible
- Check NAS credentials in Keychain
- Try manual mount: `mount_smbfs //user@host/share /Volumes/YachtNAS`
- Check firewall settings

### Files Not Uploading

**Symptoms:** Queue shows pending but nothing uploads

**Diagnosis:**
```bash
# Check queue
celesteos-agent queue

# Check errors
celesteos-agent errors

# Check API connectivity
ping api.celesteos.io

# Check logs
celesteos-agent logs | grep -i error
```

**Common fixes:**
- Verify internet connectivity
- Check yacht signature is valid
- Test API endpoint manually: `curl https://api.celesteos.io/v1/health`
- Retry failed uploads: `celesteos-agent retry`

### High CPU/Memory Usage

**Symptoms:** Mac becomes slow, fan noise

**Diagnosis:**
```bash
# Check agent process
ps aux | grep celesteos

# Monitor resources
top | grep python
```

**Common fixes:**
- Reduce scan frequency in config
- Reduce `max_concurrent_uploads` in config
- Check for very large files (>10GB)
- Increase `chunk_size_mb` for large files

### Database Corruption

**Symptoms:** "database is locked" or "database disk image is malformed"

**Recovery:**
```bash
# Stop daemon
launchctl unload ~/Library/LaunchAgents/com.celesteos.agent.plist

# Backup database
cp ~/.celesteos/celesteos.db ~/.celesteos/celesteos.db.backup

# Integrity check
sqlite3 ~/.celesteos/celesteos.db "PRAGMA integrity_check;"

# If corrupt, rebuild
mv ~/.celesteos/celesteos.db ~/.celesteos/celesteos.db.corrupt
python3 -c "from celesteos_agent.database import Database; Database().init()"

# Restart daemon
launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist
```

---

## Maintenance

### Daily Tasks (Automated)

- NAS scan every 15 minutes
- Upload processing every 5 minutes
- Deep hash verification every hour
- Chunk cleanup at 3 AM

### Weekly Tasks (Manual)

```bash
# Check for errors
celesteos-agent errors

# Review upload statistics
celesteos-agent status

# Check log size
du -sh ~/.celesteos/logs
```

### Monthly Tasks

```bash
# Vacuum database
sqlite3 ~/.celesteos/celesteos.db "VACUUM;"

# Review and archive old logs
cd ~/.celesteos/logs
tar -czf logs-$(date +%Y%m).tar.gz celesteos-agent.log.*
rm celesteos-agent.log.*
```

---

## Backup & Disaster Recovery

### What to Backup

1. **Configuration:** `~/.celesteos/config.json`
2. **Database:** `~/.celesteos/celesteos.db`
3. **Keychain:** NAS password (export from Keychain Access)

### Backup Script

```bash
#!/bin/bash
# backup-agent.sh

BACKUP_DIR="/Volumes/Backup/celesteos-agent"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Backup config
cp ~/.celesteos/config.json "$BACKUP_DIR/config-$DATE.json"

# Backup database (stop daemon first)
launchctl unload ~/Library/LaunchAgents/com.celesteos.agent.plist
cp ~/.celesteos/celesteos.db "$BACKUP_DIR/database-$DATE.db"
launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist

echo "Backup complete: $BACKUP_DIR"
```

### Restore from Backup

```bash
# Stop daemon
launchctl unload ~/Library/LaunchAgents/com.celesteos.agent.plist

# Restore config
cp /path/to/backup/config.json ~/.celesteos/config.json

# Restore database
cp /path/to/backup/database.db ~/.celesteos/celesteos.db

# Restart daemon
launchctl load ~/Library/LaunchAgents/com.celesteos.agent.plist
```

---

## Uninstallation

```bash
cd /Applications/local-agent
chmod +x scripts/uninstall.sh
./scripts/uninstall.sh
```

This will:
1. Stop the daemon
2. Remove launchd service
3. Remove command-line shortcuts
4. Optionally remove all data and configuration

---

## Security Considerations

### Credential Storage

- **NAS password:** Stored in macOS Keychain (encrypted)
- **Yacht signature:** Stored in config file (read-only)
- **API tokens:** Not stored locally

### Network Security

- **TLS 1.3:** All cloud communication encrypted
- **SHA256 verification:** All files and chunks verified
- **Read-only NAS:** Agent never writes to NAS

### Access Control

- **Config file:** 600 permissions (owner only)
- **Database:** 600 permissions (owner only)
- **Logs:** 600 permissions (owner only)
- **Temp chunks:** Deleted immediately after upload

---

## Performance Tuning

### For Small Yachts (<1000 files)

```json
{
  "scan_interval_minutes": 15,
  "max_concurrent_uploads": 2,
  "chunk_size_mb": 64,
  "hasher_workers": 2
}
```

### For Large Yachts (>10,000 files)

```json
{
  "scan_interval_minutes": 30,
  "max_concurrent_uploads": 5,
  "chunk_size_mb": 128,
  "hasher_workers": 8
}
```

### For Slow Networks

```json
{
  "chunk_size_mb": 32,
  "max_concurrent_uploads": 1,
  "api_timeout": 600
}
```

---

## Support

**Documentation:** https://docs.celesteos.io/local-agent

**Issues:** Report to yacht's CelesteOS administrator

**Logs:** Always include `celesteos-agent.log` when reporting issues

---

## Changelog

### Version 1.0.0 (2024)
- Initial release
- NAS scanning with SMB/NFS support
- SHA256 hashing and change detection
- File chunking and compression
- Cloud upload with retry logic
- macOS Keychain integration
- Scheduled scanning and uploading
- CLI and daemon management
