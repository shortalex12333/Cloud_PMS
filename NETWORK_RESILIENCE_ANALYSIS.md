# Network Resilience Analysis - Real-World Issues

## The Problem: Yachts Have Terrible Internet

### Reality Check
- **Satellite Internet** - 500-1000ms latency, expensive ($10-50/GB)
- **Spotty Coverage** - Drops when yacht moves, weather interference
- **Limited Bandwidth** - 1-5 Mbps typical (not 100 Mbps like shore)
- **Connection Drops** - Frequent, mid-transfer failures
- **Extended Offline** - Hours/days in remote areas
- **Cost Sensitive** - Crew won't waste bandwidth on failed uploads

---

## Current System Weaknesses

### Local Agent (Yacht Side)

❌ **Problem 1: No Upload Queue Persistence**
```python
# Current: In-memory queue
upload_queue = []  # Lost on crash/restart
```
**Impact:** If debug_ui.py crashes, all queued uploads are lost.

❌ **Problem 2: No Resumable Uploads**
```python
# Current: All-or-nothing
file_data = f.read()  # Read entire 500MB file
response = requests.post(url, files={'file': file_data})
# If connection drops at 90% → Start over from 0%
```
**Impact:** Large files waste bandwidth on retry.

❌ **Problem 3: No Connection Health Check**
```python
# Current: Blind upload attempt
response = requests.post(url, ...)  # Hope it works
```
**Impact:** Tries to upload even when offline, wastes time.

❌ **Problem 4: No Offline Mode**
```python
# Current: Upload now or fail
if upload_fails:
    return error  # Document not queued for later
```
**Impact:** Can't queue documents when yacht is offline.

❌ **Problem 5: No Bandwidth Management**
```python
# Current: Upload as fast as possible
timeout=120  # Just hope it finishes
```
**Impact:** Could saturate limited satellite bandwidth.

❌ **Problem 6: Synchronous Processing**
```python
# Current: Wait for cloud response
response = requests.post(...)  # Blocks for 30-120 seconds
```
**Impact:** UI freezes during upload.

---

### Cloud Side (Server)

❌ **Problem 1: Synchronous Indexing**
```python
# Current: Wait for indexing to complete
await handle_document_indexing(...)  # Can take 30+ seconds
return result  # Client waits
```
**Impact:** Yacht connection times out waiting for indexing.

❌ **Problem 2: No Retry Queue**
```python
# Current: If indexing fails, it's lost
try:
    trigger_indexing()
except:
    pass  # No retry, document stays unindexed
```
**Impact:** Failed indexing requires manual retry.

❌ **Problem 3: Large Upload Timeouts**
```python
# Current: Single POST with entire file
file_content = await file.read()  # 500MB in one go
```
**Impact:** Large files likely to timeout on slow connections.

---

## Real-World Failure Scenarios

### Scenario 1: Connection Drop During Upload
**What Happens:**
1. Yacht uploads 450MB of 500MB file
2. Satellite connection drops
3. `requests.post()` raises `ConnectionError`
4. Retry starts from 0% → Wastes another 450MB of bandwidth
5. Costs yacht $20+ in satellite data

**Solution Needed:** Resumable uploads (chunked transfer)

---

### Scenario 2: Extended Offline Period
**What Happens:**
1. Yacht enters remote area (no satellite coverage)
2. Engineer scans 50 new documents to NAS
3. Local Agent tries to upload → All fail
4. Documents not queued for later
5. Engineer manually retries each one when online

**Solution Needed:** Offline queue with persistence

---

### Scenario 3: Indexing Service Down
**What Happens:**
1. Document uploads successfully to Supabase Storage
2. Metadata inserted to `doc_metadata` table
3. Indexing service call fails (extraction service down)
4. Document marked as `indexed=false`
5. No automatic retry → Document never searchable
6. Engineer doesn't know it failed

**Solution Needed:** Background job queue with retry

---

### Scenario 4: Bandwidth Saturation
**What Happens:**
1. Local Agent uploads 10 large files simultaneously
2. Saturates yacht's 2 Mbps satellite connection
3. All other systems slow down (email, VoIP, navigation)
4. Captain gets angry at engineer

**Solution Needed:** Bandwidth throttling

---

### Scenario 5: Partial Upload Accepted
**What Happens:**
1. Upload times out at 80% complete
2. Server has partial file data in memory
3. No way to resume → Start over
4. Doubles bandwidth cost

**Solution Needed:** Chunked uploads with resume support

---

## Solutions: Making It Bulletproof

### Local Agent Improvements

#### 1. **Persistent Upload Queue (SQLite)**

```python
# New: SQLite-backed queue
class UploadQueue:
    def __init__(self, db_path="~/.celesteos/upload_queue.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS upload_queue (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL,
                yacht_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',  -- pending, uploading, completed, failed
                priority INTEGER DEFAULT 5,     -- 1=critical, 5=normal, 10=low
                attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def add(self, file_path, yacht_id, priority=5):
        """Add file to queue (survives restarts)"""
        self.conn.execute(
            "INSERT INTO upload_queue (file_path, yacht_id, priority) VALUES (?, ?, ?)",
            (str(file_path), yacht_id, priority)
        )
        self.conn.commit()

    def get_next(self):
        """Get next file to upload (highest priority first)"""
        cursor = self.conn.execute("""
            SELECT id, file_path FROM upload_queue
            WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """)
        return cursor.fetchone()

    def mark_completed(self, queue_id):
        self.conn.execute("UPDATE upload_queue SET status='completed' WHERE id=?", (queue_id,))
        self.conn.commit()

    def mark_failed(self, queue_id, error):
        self.conn.execute(
            "UPDATE upload_queue SET status='failed', attempts=attempts+1, error_message=? WHERE id=?",
            (error, queue_id)
        )
        self.conn.commit()
```

**Benefits:**
- ✅ Queue survives crashes/restarts
- ✅ Priority queuing (critical docs first)
- ✅ Retry tracking
- ✅ Error logging

---

#### 2. **Connection Health Check**

```python
class ConnectionMonitor:
    def __init__(self, test_url="https://celeste-digest-index.onrender.com/health"):
        self.test_url = test_url
        self.is_online = False
        self.last_check = None
        self.check_interval = 30  # seconds

    def check_connectivity(self) -> bool:
        """Test if internet connection is available"""
        try:
            response = requests.get(self.test_url, timeout=5)
            self.is_online = response.status_code == 200
            self.last_check = datetime.now()
            return self.is_online
        except:
            self.is_online = False
            return False

    def wait_for_connection(self, max_wait=300):
        """Wait for connection to come back online"""
        start = time.time()
        while time.time() - start < max_wait:
            if self.check_connectivity():
                return True
            time.sleep(30)  # Check every 30s
        return False
```

**Usage:**
```python
monitor = ConnectionMonitor()

if not monitor.is_online:
    print("⚠️  Offline - Queueing documents for later")
    queue.add(file_path, yacht_id)
    return

# Online - proceed with upload
uploader.upload(file_path)
```

---

#### 3. **Resumable Uploads (Chunked Transfer)**

```python
class ResumableUploader:
    CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks

    def upload_file_resumable(self, file_path, yacht_id):
        """Upload file in chunks, resume on failure"""
        file_size = file_path.stat().st_size
        num_chunks = (file_size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE

        # Check if partial upload exists
        upload_id = self._get_upload_id(file_path)
        completed_chunks = self._get_completed_chunks(upload_id)

        with open(file_path, 'rb') as f:
            for chunk_num in range(num_chunks):
                if chunk_num in completed_chunks:
                    print(f"⏭️  Chunk {chunk_num+1}/{num_chunks} already uploaded")
                    f.seek((chunk_num + 1) * self.CHUNK_SIZE)
                    continue

                # Read chunk
                f.seek(chunk_num * self.CHUNK_SIZE)
                chunk_data = f.read(self.CHUNK_SIZE)

                # Upload chunk with retry
                for attempt in range(3):
                    try:
                        response = requests.post(
                            f"{self.webhook_endpoint}/webhook/upload-chunk",
                            data={
                                'upload_id': upload_id,
                                'chunk_num': chunk_num,
                                'total_chunks': num_chunks,
                                'yacht_id': yacht_id
                            },
                            files={'chunk': chunk_data},
                            headers={'X-Yacht-Signature': self._generate_signature(yacht_id)},
                            timeout=30
                        )

                        if response.status_code == 200:
                            self._mark_chunk_completed(upload_id, chunk_num)
                            print(f"✅ Uploaded chunk {chunk_num+1}/{num_chunks} ({chunk_num/num_chunks*100:.1f}%)")
                            break
                    except:
                        if attempt == 2:
                            raise
                        time.sleep(2 ** attempt)

        # Finalize upload
        return self._finalize_upload(upload_id, yacht_id)
```

**Benefits:**
- ✅ Resume from where it left off
- ✅ Save bandwidth on retry
- ✅ Progress tracking
- ✅ Better timeout handling (30s per 10MB vs 120s for 500MB)

---

#### 4. **Bandwidth Throttling**

```python
class BandwidthThrottler:
    def __init__(self, max_bytes_per_second=500_000):  # 500 KB/s = ~4 Mbps
        self.max_bytes_per_second = max_bytes_per_second
        self.bytes_sent = 0
        self.window_start = time.time()

    def throttle(self, bytes_to_send):
        """Sleep if needed to stay under bandwidth limit"""
        self.bytes_sent += bytes_to_send
        elapsed = time.time() - self.window_start

        if elapsed >= 1.0:
            # Reset window
            self.bytes_sent = bytes_to_send
            self.window_start = time.time()
        else:
            # Calculate if we need to wait
            expected_time = self.bytes_sent / self.max_bytes_per_second
            if expected_time > elapsed:
                time.sleep(expected_time - elapsed)
```

**Usage:**
```python
throttler = BandwidthThrottler(max_bytes_per_second=500_000)  # 500 KB/s

for chunk in chunks:
    upload_chunk(chunk)
    throttler.throttle(len(chunk))
```

---

#### 5. **Async Upload with Progress**

```python
class AsyncUploader:
    def __init__(self):
        self.upload_thread = None
        self.progress = {"current": 0, "total": 0, "status": "idle"}

    def upload_async(self, file_path, yacht_id):
        """Upload in background thread, don't block UI"""
        def _upload():
            try:
                self.progress["status"] = "uploading"
                self.progress["total"] = file_path.stat().st_size

                # Upload with progress callback
                uploader.upload_with_progress(
                    file_path,
                    progress_callback=lambda bytes_sent: self._update_progress(bytes_sent)
                )

                self.progress["status"] = "completed"
            except Exception as e:
                self.progress["status"] = "failed"
                self.progress["error"] = str(e)

        self.upload_thread = threading.Thread(target=_upload, daemon=True)
        self.upload_thread.start()

    def _update_progress(self, bytes_sent):
        self.progress["current"] = bytes_sent

    def get_progress(self):
        return {
            "percent": (self.progress["current"] / self.progress["total"] * 100) if self.progress["total"] > 0 else 0,
            "status": self.progress["status"],
            "bytes_sent": self.progress["current"],
            "bytes_total": self.progress["total"]
        }
```

---

### Cloud Side Improvements

#### 1. **Async Processing with Job Queue**

```python
# New: Background job queue (Redis)
from rq import Queue
from redis import Redis

redis_conn = Redis(host='localhost', port=6379)
job_queue = Queue('document-indexing', connection=redis_conn)

@app.post("/webhook/ingest-docs-nas-cloud")
async def ingest_document(...):
    # ... upload to storage, insert metadata ...

    # Queue indexing job (don't wait)
    job = job_queue.enqueue(
        'workflows.document_indexing.handle_document_indexing',
        filename=filename,
        document_id=document_id,
        yacht_id=yacht_id,
        job_timeout='10m',
        retry=Retry(max=3, interval=[60, 300, 900])  # Retry with backoff
    )

    # Return immediately (yacht doesn't wait)
    return {
        "status": "queued_for_indexing",
        "document_id": document_id,
        "job_id": job.id
    }
```

**Benefits:**
- ✅ Yacht connection doesn't timeout waiting
- ✅ Automatic retry on failure
- ✅ Indexing happens asynchronously
- ✅ Can monitor job status separately

---

#### 2. **Chunked Upload Endpoint**

```python
# New: Support resumable chunked uploads
upload_sessions = {}  # In production: Redis

@app.post("/webhook/upload-chunk")
async def upload_chunk(
    request: Request,
    chunk: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_num: int = Form(...),
    total_chunks: int = Form(...),
    yacht_id: str = Form(...),
    x_yacht_signature: str = Header(None)
):
    """
    Accept chunked uploads for resumability

    Client uploads file in 10MB chunks.
    If connection drops, resume from last completed chunk.
    """
    # Verify signature
    verify_yacht_signature(yacht_id, x_yacht_signature)

    # Initialize session if first chunk
    if upload_id not in upload_sessions:
        upload_sessions[upload_id] = {
            "yacht_id": yacht_id,
            "chunks": {},
            "total_chunks": total_chunks
        }

    # Store chunk (in production: S3 or Supabase Storage)
    chunk_data = await chunk.read()
    upload_sessions[upload_id]["chunks"][chunk_num] = chunk_data

    # Check if all chunks received
    if len(upload_sessions[upload_id]["chunks"]) == total_chunks:
        # Reassemble file
        full_file = b"".join([
            upload_sessions[upload_id]["chunks"][i]
            for i in range(total_chunks)
        ])

        # Process as normal
        result = await handle_document_ingestion(...)

        # Cleanup
        del upload_sessions[upload_id]

        return {"status": "completed", **result}
    else:
        return {
            "status": "chunk_received",
            "chunk_num": chunk_num,
            "chunks_received": len(upload_sessions[upload_id]["chunks"]),
            "total_chunks": total_chunks
        }
```

---

#### 3. **Webhook Callbacks (Notify When Done)**

```python
# New: Notify yacht when indexing completes
async def handle_document_indexing(...):
    # ... process indexing ...

    # Notify yacht via webhook
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://yacht-{yacht_id}.celeste7.ai/webhook/indexing-complete",
                json={
                    "document_id": document_id,
                    "status": "indexed",
                    "chunks_created": chunks_created
                },
                timeout=10
            )
    except:
        # If yacht is offline, that's OK
        pass
```

---

## Architecture Changes

### Before (Fragile)
```
[Yacht] ---(500MB upload)---> [Cloud]
         ❌ If drops: Start over
         ❌ Waits for indexing (60s)
         ❌ No offline queue
```

### After (Resilient)
```
[Yacht]
  ├─ SQLite Queue (persists across restarts)
  ├─ Connection Monitor (detect offline)
  ├─ Chunked Upload (10MB at a time, resumable)
  └─ Background Thread (don't block UI)
       │
       ▼
[Cloud API]
  ├─ Accept chunk → Store → Respond immediately
  ├─ Queue indexing job → Redis/RQ
  └─ Worker processes job → Retry on failure
       │
       ▼
[Yacht Webhook] (when done)
  └─ Notification: "Document X indexed successfully"
```

---

## Implementation Priority

### Phase 1: Critical (Do Now)
1. ✅ **Persistent Upload Queue** - SQLite-backed queue
2. ✅ **Connection Health Check** - Don't attempt uploads when offline
3. ✅ **Async Upload** - Background thread, don't block UI
4. ✅ **Better Error Handling** - Exponential backoff, retry limits

### Phase 2: Important (Next Week)
5. ⏳ **Chunked Uploads** - 10MB chunks, resumable
6. ⏳ **Async Job Queue** - Redis/RQ for indexing
7. ⏳ **Bandwidth Throttling** - Configurable limits

### Phase 3: Nice to Have (Future)
8. ⏳ **Webhook Callbacks** - Notify yacht when done
9. ⏳ **Compression** - Gzip before upload
10. ⏳ **Delta Sync** - Only upload changed parts of files

---

## Cost Comparison

### Current System (Fragile)
```
Scenario: Upload 500MB file, connection drops at 90%
- Uploaded: 450 MB (wasted)
- Retry: 500 MB (full upload)
- Total: 950 MB
- Cost: $47.50 @ $50/GB satellite
```

### Improved System (Resilient)
```
Scenario: Upload 500MB file, connection drops at 90%
- Uploaded: 45 chunks × 10MB = 450 MB
- Retry: 5 chunks × 10MB = 50 MB (resume from chunk 45)
- Total: 500 MB
- Cost: $25.00 @ $50/GB satellite

SAVINGS: $22.50 per failed upload (47% savings)
```

---

## Testing Recommendations

### Simulate Real Conditions
```bash
# Test 1: Kill connection mid-upload
# Expectation: Upload resumes from last chunk

# Test 2: Leave yacht offline for 24 hours
# Expectation: Documents queue locally, upload when online

# Test 3: Saturate bandwidth with 10 simultaneous uploads
# Expectation: Throttling prevents saturation

# Test 4: Indexing service down
# Expectation: Jobs queue, retry automatically

# Test 5: Restart Local Agent mid-upload
# Expectation: Queue persists, resumes on restart
```

---

## Monitoring & Alerts

```python
# What to monitor
metrics = {
    "upload_queue_size": len(queue),  # Alert if > 1000
    "failed_uploads_24h": count_failed(),  # Alert if > 10%
    "avg_upload_time": calculate_avg(),  # Alert if > 5 minutes
    "bandwidth_usage": bytes_per_hour,  # Alert if > budget
    "indexing_backlog": job_queue.count,  # Alert if > 100
}
```

---

## Summary

**The Real Problem:** Yachts have terrible, expensive, unreliable internet.

**The Solution:** Build for intermittent connectivity:
- ✅ Queue everything (persist to SQLite)
- ✅ Check connectivity before upload
- ✅ Upload in small chunks (resumable)
- ✅ Process asynchronously (don't wait)
- ✅ Retry automatically (with backoff)
- ✅ Throttle bandwidth (don't saturate)
- ✅ Work offline (queue for later)

**Result:** System works reliably even on yacht's terrible internet. Engineer doesn't waste time or bandwidth on failed uploads.
