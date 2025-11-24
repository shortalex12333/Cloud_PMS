
# 🖥️ **local-agent-spec.md — CelesteOS Local Agent (DMG App) Specification**

**Version:** 1.0
**Owner:** Engineering
**Status:** Approved for MVP**

---

# # 🎯 **Purpose of the Local Agent**

The CelesteOS Local Agent is a **macOS application** installed on the yacht’s onboard Mac Studio/Mac Mini.
Its sole purpose is to:

1. **Read documents from NAS (read-only)**
2. **Hash, chunk, and prepare files**
3. **Upload them securely to the cloud**
4. **Retry, resume, and queue changes**
5. **Track modifications for incremental sync**

The agent **never performs heavy AI**, embeddings, or search.
All intelligence lives in the cloud.

The local agent = **secure ingestion gateway**, nothing more.

---

# # 🛠️ **1. System Components**

The Local Agent consists of:

### **1.1 macOS GUI App**

* Initial setup
* NAS connection wizard
* Status view (“Syncing”, “Idle”, “Errors detected”)
* Manual “Rescan NAS” button
* Logs & diagnostics

### **1.2 Background Daemon (LaunchAgent)**

Runs even when GUI is closed.

Responsibilities:

* Watch NAS
* Manage upload queue
* Verify hashes
* Chunk files
* Retry failed uploads
* Auto-update itself
* Persistent state

### **1.3 Python Worker (Embedded Runtime)**

Handles:

* SMB/NFS reading
* Hashing
* Chunk creation
* Compression
* Exif + metadata extraction
* Temporary file handling

Python is used because:

* reliable file handling
* cross-platform hashing
* easy for NAS operations

---

# # 📁 **2. NAS Integration**

NAS could be:

* Synology
* QNAP
* TrueNAS
* Windows SMB share
* Mac Samba share

### **2.1 NAS Mounting**

Credentials stored in macOS Keychain.

NAS mounted to:

```
/Volumes/CelesteOS_NAS/
```

### **2.2 Read-Only Access**

The agent will request **read-only** SMB credentials.

This enforces:

* zero modification of NAS files
* zero risk of accidental overwrites
* complete owner confidence

### **2.3 Directory Scope**

User selects:

* root NAS folder, OR
* multiple folders, OR
* full engineering drive

Example:

```
/Volumes/CelesteOS_NAS/Engineering
/Volumes/CelesteOS_NAS/Manuals
/Volumes/CelesteOS_NAS/TechDrawings
```

### **2.4 File Types to Include**

By default:

* pdf
* docx
* xlsx
* pptx
* msg/eml
* images
* txt
* csv
* json

Binary junk excluded automatically:

* iso
* dmg
* zip
* exe
* video files

(Still stored as metadata but not uploaded.)

---

# # 🔍 **3. Discovery & Hashing Engine**

### **3.1 Initial Scan**

On first install, the agent performs a full file-system walk:

* collect file paths
* size
* extension
* lastModified timestamp
* compute SHA256

Stored in:

```
~/Library/Application Support/CelesteOS/manifest.sqlite
```

### **3.2 SHA256 as Identity**

All dedupe + integrity uses:

```
sha256(file_contents)
```

Cloud re-hashes to confirm.

### **3.3 Incremental Sync**

Every 15 minutes (configurable):

* walk diffs
* compare SHA256 with manifest
* only changed/new files go into upload queue

---

# # 📦 **4. File Chunking & Compression**

### **4.1 Chunking**

Large files (ex: 500MB manuals) are split into:

```
8MB–32MB chunks
```

Chunk structure:

```json
{
  "chunk_number": 1,
  "total_chunks": 12,
  "sha256": "fileHash",
  "chunk_sha256": "chunkHash",
  "yacht_signature": "...",
  "timestamp": "...",
}
```

### **4.2 Compression**

Text-based files → gzipped
Images → optional
Binary PDFs → light compression

### **4.3 Resume Logic**

Failed chunks retry automatically.

---

# # 📤 **5. Upload Queue System**

### **5.1 Queue Design**

Queue stored in local sqlite:

Tables:

* `pending_files`
* `pending_chunks`
* `failed_chunks`
* `completed_uploads`

### **5.2 Upload Scheduler**

Upload batches:

* 5–10 parallel connections
* adaptive throttling (avoid saturating Starlink)
* pause/resume

### **5.3 Backpressure & Starlink Stability**

If connection drops:

* queue pauses
* retries with exponential backoff
* no corruption — safe chunk system

---

# # 🔐 **6. Authentication & Yacht Signature**

### **6.1 Yacht Signature**

During onboarding, cloud issues a **yacht_signature**:

* acts as root identity
* binds all uploads to that yacht
* prevents cross-yacht leakage
* included in every request header

### **6.2 Device Authentication**

Local agent uses:

* device_token
* yacht_signature
* HMAC timestamp signing

### **6.3 Storage of Secrets**

All secrets stored in:

* macOS Keychain (GUI credentials)
* encrypted file in Application Support

---

# # 🌩️ **7. Cloud Upload API**

Upload occurs via:

```
POST /v1/ingest/init
PATCH /v1/ingest/upload_chunk
POST /v1/ingest/complete
```

### **Payload Includes:**

* yacht_signature
* file metadata
* chunk metadata
* SHA256 for integrity
* timestamp
* HMAC signature

Cloud verifies:

* yacht identity
* chunk order
* chunk checksum
* duplicate file presence
* object storage write access

---

# # 🔄 **8. Auto-Updating Behaviour**

Agent must always stay current.

### **8.1 Update Delivery**

Agent checks every 6h:

* fetches manifest from cloud
* compares version
* downloads delta or full update

### **8.2 Update Types**

* background patch
* full app update (DMG)
* background Python worker patch

### **8.3 Silent Restart**

Daemon restarts itself gracefully after updates.

---

# # 🧪 **9. Error Handling & Recovery**

### **9.1 NAS Disconnect**

* retries every 30 seconds
* GUI shows “NAS unavailable”
* prevents upload attempts

### **9.2 Cloud Down**

* upload queue pauses
* retries with exponential backoff
* never drops chunks

### **9.3 Corrupted File**

Flags file with status:

```
corrupt_file
```

Skips it.

### **9.4 Manifest Corruption**

Recovery:

* rebuild manifest from NAS
* maintain SHA256 history

### **9.5 User Cancellation**

User can:

* pause syncing
* resume
* exclude folders

---

# # 🧭 **10. Onboarding UX Flow**

The first-time experience must be simple:

### **Step 1 — Launch App**

“Welcome to CelesteOS.”

### **Step 2 — Enter Yacht Signature**

Issued at provisioning.

### **Step 3 — Connect to NAS**

User enters:

* NAS IP
* Username
* Password

### **Step 4 — Select Folders to Sync**

Checkbox list of NAS directories.

### **Step 5 — Test Connection**

NAS mounted → success indicator.

### **Step 6 — Start Sync**

Initial scan + upload queue begins.

### **Step 7 — Quiet Operation**

Daemon handles everything thereafter.

---

# # 🔐 **11. Security Guarantees**

* NAS read-only
* All uploads encrypted
* All chunks integrity-checked
* All requests yacht-bound
* No local inference
* No document modification
* No cross-yacht data mixing

---

# # 🏁 **12. Summary**

The CelesteOS Local Agent is:

* lightweight
* secure
* fault-tolerant
* read-only
* cloud-synced
* self-updating
* zero-maintenance

It reliably synchronizes the yacht’s engineering data to the cloud, enabling the full CelesteOS intelligence engine.

---
