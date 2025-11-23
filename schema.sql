-- CelesteOS Local Agent SQLite Database Schema
-- Version: 1.0
-- This database tracks all local state for the NAS ingestion agent

-- ============================================================
-- YACHT IDENTITY
-- ============================================================
CREATE TABLE yacht_identity (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Enforce single row
    yacht_signature TEXT NOT NULL UNIQUE,
    yacht_name TEXT,
    api_endpoint TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- ============================================================
-- AGENT SETTINGS
-- ============================================================
CREATE TABLE agent_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Enforce single row
    nas_path TEXT NOT NULL,
    nas_type TEXT NOT NULL CHECK (nas_type IN ('smb', 'nfs', 'local')),
    nas_username TEXT,
    nas_host TEXT,
    nas_share TEXT,
    scan_interval_minutes INTEGER NOT NULL DEFAULT 15,
    deep_scan_interval_hours INTEGER NOT NULL DEFAULT 1,
    max_concurrent_uploads INTEGER NOT NULL DEFAULT 3,
    chunk_size_mb INTEGER NOT NULL DEFAULT 64,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    last_full_scan INTEGER,
    last_deep_scan INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- ============================================================
-- FILES REGISTRY
-- Tracks all files discovered on NAS
-- ============================================================
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE, -- Relative to NAS root
    filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_extension TEXT,
    mime_type TEXT,
    sha256 TEXT NOT NULL,
    previous_sha256 TEXT, -- For detecting changes
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'uploading', 'uploaded', 'error', 'deleted')),
    first_seen INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    last_seen INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    last_modified INTEGER, -- File system modified time
    last_hashed INTEGER,
    upload_count INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_files_status ON files(status);
CREATE INDEX idx_files_sha256 ON files(sha256);
CREATE INDEX idx_files_path ON files(file_path);

-- ============================================================
-- UPLOAD QUEUE
-- Manages file upload state and chunking
-- ============================================================
CREATE TABLE upload_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    upload_id TEXT UNIQUE, -- UUID from cloud /v1/ingest/init
    file_sha256 TEXT NOT NULL,
    filename TEXT NOT NULL,
    local_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    uploaded_chunks INTEGER NOT NULL DEFAULT 0,
    chunk_size_mb INTEGER NOT NULL DEFAULT 64,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'initializing', 'uploading', 'completing', 'complete', 'error', 'paused')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,
    last_error TEXT,
    last_retry_at INTEGER,
    next_retry_at INTEGER,
    started_at INTEGER,
    completed_at INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX idx_upload_queue_status ON upload_queue(status);
CREATE INDEX idx_upload_queue_file_id ON upload_queue(file_id);
CREATE INDEX idx_upload_queue_upload_id ON upload_queue(upload_id);

-- ============================================================
-- UPLOAD CHUNKS
-- Tracks individual chunk upload status
-- ============================================================
CREATE TABLE upload_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_queue_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_sha256 TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,
    chunk_path TEXT, -- Temporary local path before upload
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploading', 'uploaded', 'error')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    uploaded_at INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (upload_queue_id) REFERENCES upload_queue(id) ON DELETE CASCADE,
    UNIQUE(upload_queue_id, chunk_index)
);

CREATE INDEX idx_upload_chunks_queue_id ON upload_chunks(upload_queue_id);
CREATE INDEX idx_upload_chunks_status ON upload_chunks(status);

-- ============================================================
-- ERROR LOG
-- Persistent error tracking
-- ============================================================
CREATE TABLE errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_type TEXT NOT NULL CHECK (error_type IN ('nas_scan', 'hash_compute', 'upload_init', 'upload_chunk', 'upload_complete', 'api_error', 'network_error', 'file_access', 'config_error', 'system_error')),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    message TEXT NOT NULL,
    details TEXT, -- JSON or detailed error info
    file_id INTEGER,
    upload_queue_id INTEGER,
    stack_trace TEXT,
    resolved BOOLEAN NOT NULL DEFAULT 0,
    resolved_at INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
    FOREIGN KEY (upload_queue_id) REFERENCES upload_queue(id) ON DELETE SET NULL
);

CREATE INDEX idx_errors_type ON errors(error_type);
CREATE INDEX idx_errors_severity ON errors(severity);
CREATE INDEX idx_errors_resolved ON errors(resolved);
CREATE INDEX idx_errors_created_at ON errors(created_at);

-- ============================================================
-- SYNC STATE
-- Tracks overall sync health and statistics
-- ============================================================
CREATE TABLE sync_state (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Enforce single row
    total_files_discovered INTEGER NOT NULL DEFAULT 0,
    total_files_uploaded INTEGER NOT NULL DEFAULT 0,
    total_files_pending INTEGER NOT NULL DEFAULT 0,
    total_files_error INTEGER NOT NULL DEFAULT 0,
    total_bytes_uploaded INTEGER NOT NULL DEFAULT 0,
    last_scan_started INTEGER,
    last_scan_completed INTEGER,
    last_scan_duration_seconds INTEGER,
    last_upload_at INTEGER,
    is_scanning BOOLEAN NOT NULL DEFAULT 0,
    is_uploading BOOLEAN NOT NULL DEFAULT 0,
    daemon_status TEXT NOT NULL DEFAULT 'stopped' CHECK (daemon_status IN ('stopped', 'starting', 'running', 'paused', 'error')),
    daemon_started_at INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- Initialize sync state
INSERT INTO sync_state (id) VALUES (1);

-- ============================================================
-- ACTIVITY LOG
-- High-level activity tracking for dashboard
-- ============================================================
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL CHECK (activity_type IN ('scan_started', 'scan_completed', 'file_discovered', 'file_changed', 'file_deleted', 'upload_started', 'upload_completed', 'upload_failed', 'daemon_started', 'daemon_stopped', 'config_changed', 'error_occurred')),
    message TEXT NOT NULL,
    details TEXT, -- JSON with additional context
    file_id INTEGER,
    upload_queue_id INTEGER,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
    FOREIGN KEY (upload_queue_id) REFERENCES upload_queue(id) ON DELETE SET NULL
);

CREATE INDEX idx_activity_log_type ON activity_log(activity_type);
CREATE INDEX idx_activity_log_created_at ON activity_log(created_at);

-- ============================================================
-- FILE IGNORE PATTERNS
-- Configurable patterns for files/folders to ignore
-- ============================================================
CREATE TABLE ignore_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL UNIQUE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('glob', 'regex', 'extension', 'folder')),
    description TEXT,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- Default ignore patterns
INSERT INTO ignore_patterns (pattern, pattern_type, description) VALUES
    ('.*', 'glob', 'Hidden files starting with dot'),
    ('~$*', 'glob', 'Office temporary files'),
    ('Thumbs.db', 'glob', 'Windows thumbnail cache'),
    ('.DS_Store', 'glob', 'macOS folder metadata'),
    ('desktop.ini', 'glob', 'Windows folder metadata'),
    ('$RECYCLE.BIN', 'folder', 'Windows recycle bin'),
    ('.Trash', 'folder', 'macOS trash'),
    ('.TemporaryItems', 'folder', 'macOS temporary items'),
    ('.Spotlight-V100', 'folder', 'macOS Spotlight index'),
    ('.fseventsd', 'folder', 'macOS file system events'),
    ('System Volume Information', 'folder', 'Windows system folder'),
    ('.tmp', 'extension', 'Temporary files'),
    ('.temp', 'extension', 'Temporary files'),
    ('.cache', 'extension', 'Cache files');

-- ============================================================
-- TOMBSTONES
-- Tracks deleted/moved files for cloud notification
-- ============================================================
CREATE TABLE tombstones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_sha256 TEXT, -- Last known hash
    file_size INTEGER,
    deleted_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    reason TEXT NOT NULL CHECK (reason IN ('deleted', 'moved', 'renamed', 'replaced')),
    new_path TEXT, -- If moved/renamed, the new path
    reported_to_cloud BOOLEAN NOT NULL DEFAULT 0,
    reported_at INTEGER,
    cloud_response TEXT, -- JSON response from cloud
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_tombstones_reported ON tombstones(reported_to_cloud);
CREATE INDEX idx_tombstones_deleted_at ON tombstones(deleted_at);
CREATE INDEX idx_tombstones_file_path ON tombstones(file_path);

-- ============================================================
-- TELEMETRY EVENTS
-- Local event storage for later batch upload
-- ============================================================
CREATE TABLE telemetry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'scan_started', 'scan_completed', 'scan_failed',
        'file_discovered', 'file_modified', 'file_deleted',
        'upload_started', 'upload_chunk_completed', 'upload_completed', 'upload_failed',
        'daemon_started', 'daemon_stopped', 'error_occurred',
        'resume_detected', 'hash_computed', 'tombstone_created'
    )),
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    yacht_id TEXT,
    file_path TEXT,
    file_sha256 TEXT,
    file_size INTEGER,
    chunk_index INTEGER,
    total_chunks INTEGER,
    duration_ms INTEGER,
    error_message TEXT,
    metadata TEXT, -- JSON for additional context
    uploaded_to_cloud BOOLEAN NOT NULL DEFAULT 0,
    uploaded_at INTEGER,
    batch_id TEXT -- For grouping uploads
);

CREATE INDEX idx_telemetry_uploaded ON telemetry_events(uploaded_to_cloud);
CREATE INDEX idx_telemetry_event_type ON telemetry_events(event_type);
CREATE INDEX idx_telemetry_timestamp ON telemetry_events(timestamp);

-- ============================================================
-- UPLOAD STATE (Lightweight per-file resume state)
-- ============================================================
CREATE TABLE upload_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_queue_id INTEGER NOT NULL UNIQUE,
    file_sha256 TEXT NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunks_completed TEXT NOT NULL DEFAULT '[]', -- JSON array of completed chunk indices
    last_chunk_uploaded INTEGER DEFAULT -1,
    bytes_uploaded INTEGER NOT NULL DEFAULT 0,
    state_version INTEGER NOT NULL DEFAULT 1, -- For optimistic locking
    last_activity INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (upload_queue_id) REFERENCES upload_queue(id) ON DELETE CASCADE
);

CREATE INDEX idx_upload_state_queue_id ON upload_state(upload_queue_id);
CREATE INDEX idx_upload_state_sha256 ON upload_state(file_sha256);

-- ============================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- ============================================================

CREATE TRIGGER update_yacht_identity_timestamp
    AFTER UPDATE ON yacht_identity
    FOR EACH ROW
BEGIN
    UPDATE yacht_identity SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER update_agent_settings_timestamp
    AFTER UPDATE ON agent_settings
    FOR EACH ROW
BEGIN
    UPDATE agent_settings SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER update_files_timestamp
    AFTER UPDATE ON files
    FOR EACH ROW
BEGIN
    UPDATE files SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER update_upload_queue_timestamp
    AFTER UPDATE ON upload_queue
    FOR EACH ROW
BEGIN
    UPDATE upload_queue SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER update_upload_chunks_timestamp
    AFTER UPDATE ON upload_chunks
    FOR EACH ROW
BEGIN
    UPDATE upload_chunks SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

CREATE TRIGGER update_sync_state_timestamp
    AFTER UPDATE ON sync_state
    FOR EACH ROW
BEGIN
    UPDATE sync_state SET updated_at = strftime('%s', 'now') WHERE id = NEW.id;
END;

-- ============================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================

-- Active uploads with file details
CREATE VIEW v_active_uploads AS
SELECT
    uq.id as upload_id,
    uq.upload_id as cloud_upload_id,
    uq.status,
    uq.uploaded_chunks,
    uq.total_chunks,
    CAST(uq.uploaded_chunks AS REAL) / uq.total_chunks * 100 as progress_percent,
    uq.file_size,
    uq.retry_count,
    uq.last_error,
    f.file_path,
    f.filename,
    f.sha256,
    uq.created_at,
    uq.updated_at
FROM upload_queue uq
JOIN files f ON uq.file_id = f.id
WHERE uq.status IN ('pending', 'initializing', 'uploading', 'completing');

-- Pending files ready for upload
CREATE VIEW v_pending_files AS
SELECT
    id,
    file_path,
    filename,
    file_size,
    sha256,
    status,
    upload_count,
    last_seen,
    created_at
FROM files
WHERE status = 'pending'
AND id NOT IN (SELECT file_id FROM upload_queue WHERE status NOT IN ('complete', 'error'));

-- Recent errors
CREATE VIEW v_recent_errors AS
SELECT
    e.id,
    e.error_type,
    e.severity,
    e.message,
    e.created_at,
    f.filename,
    f.file_path
FROM errors e
LEFT JOIN files f ON e.file_id = f.id
WHERE e.resolved = 0
ORDER BY e.created_at DESC
LIMIT 100;

-- Sync statistics
CREATE VIEW v_sync_stats AS
SELECT
    (SELECT COUNT(*) FROM files WHERE status = 'uploaded') as files_uploaded,
    (SELECT COUNT(*) FROM files WHERE status = 'pending') as files_pending,
    (SELECT COUNT(*) FROM files WHERE status = 'uploading') as files_uploading,
    (SELECT COUNT(*) FROM files WHERE status = 'error') as files_error,
    (SELECT COUNT(*) FROM upload_queue WHERE status = 'uploading') as active_uploads,
    (SELECT COUNT(*) FROM errors WHERE resolved = 0 AND severity IN ('error', 'critical')) as critical_errors,
    (SELECT SUM(file_size) FROM files WHERE status = 'uploaded') as total_bytes_uploaded,
    (SELECT SUM(file_size) FROM files WHERE status = 'pending') as total_bytes_pending;
