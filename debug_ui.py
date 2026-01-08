#!/usr/bin/env python3
"""
CelesteOS Debug UI - Localhost Quality Inspection Server
Run: python3 debug_ui.py
Access: http://localhost:5050
"""

import sqlite3
import json
import time
import os
import subprocess
import threading
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, redirect, url_for

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from celesteos_agent.uploader import FileUploader
from celesteos_agent.metadata_extractor import extract_metadata_from_path, is_supported_file
from celesteos_agent.async_uploader import create_async_uploader

app = Flask(__name__)

# Database path
DB_PATH = Path("~/.celesteos/celesteos.db").expanduser()
CONFIG_PATH = Path("~/.celesteos/config.json").expanduser()
PID_FILE = Path("~/.celesteos/celesteos-agent.pid").expanduser()

# Track scan status
scan_status = {"running": False, "message": "", "progress": 0}

# Uploader config
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
WEBHOOK_ENDPOINT = "https://celeste-digest-index.onrender.com"
YACHT_SALT = os.getenv("YACHT_SALT", "e49469e09cb6529e0bfef118370cf8425b006f0abbc77475da2e0cb479af8b18")

# Async upload manager (created on startup)
async_uploader = None


def get_db():
    """Get database connection."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_bytes(size):
    """Format bytes to human readable."""
    if size is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_timestamp(ts):
    """Format unix timestamp."""
    if not ts:
        return "Never"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def is_daemon_running():
    """Check if daemon is running."""
    if not PID_FILE.exists():
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # Check if process exists
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def get_directory_listing(path):
    """Get directory listing for browser."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return None, "Path does not exist"
        if not p.is_dir():
            return None, "Path is not a directory"

        items = []
        for item in sorted(p.iterdir()):
            if item.name.startswith('.'):
                continue  # Skip hidden
            items.append({
                'name': item.name,
                'path': str(item),
                'is_dir': item.is_dir(),
                'size': item.stat().st_size if item.is_file() else 0
            })
        return items, None
    except PermissionError:
        return None, "Permission denied"
    except Exception as e:
        return None, str(e)


def open_macos_folder_picker():
    """Open native macOS Finder folder picker dialog."""
    try:
        result = subprocess.run([
            'osascript', '-e',
            'POSIX path of (choose folder with prompt "Select the root folder for document ingestion:")'
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            path = result.stdout.strip()
            # Remove trailing slash if present
            if path.endswith('/'):
                path = path[:-1]
            return path, None
        else:
            # User cancelled
            return None, "cancelled"
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:
        return None, str(e)


# HTML Templates
BASE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>CelesteOS Debug UI</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.5;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #161b22 0%, #1a2332 100%);
            border-bottom: 1px solid #30363d;
            padding: 16px 20px;
            margin-bottom: 20px;
        }
        header h1 { color: #58a6ff; font-size: 1.5rem; }
        header span { color: #8b949e; font-size: 0.875rem; }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
        }
        .card h3 { color: #8b949e; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 8px; }
        .card .value { font-size: 1.75rem; font-weight: 600; color: #f0f6fc; }
        .card .value.success { color: #3fb950; }
        .card .value.warning { color: #d29922; }
        .card .value.error { color: #f85149; }
        .card .value.info { color: #58a6ff; }

        .section {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            margin-bottom: 24px;
            overflow: hidden;
        }
        .section-header {
            padding: 16px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .section-header h2 { font-size: 1rem; color: #f0f6fc; }

        /* IMPORTANT: Digestion Source Highlight */
        .digestion-source {
            background: linear-gradient(135deg, #1a2f1a 0%, #162b16 100%);
            border: 2px solid #238636;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .digestion-source h2 {
            color: #3fb950;
            font-size: 1.25rem;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .digestion-source h2::before {
            content: "📁";
            font-size: 1.5rem;
        }
        .digestion-source .subtitle {
            color: #8b949e;
            font-size: 0.875rem;
            margin-bottom: 16px;
        }
        .digestion-source .path-display {
            background: #0d1117;
            border: 1px solid #238636;
            border-radius: 8px;
            padding: 16px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 1.1rem;
            color: #3fb950;
            margin-bottom: 16px;
            word-break: break-all;
        }
        .digestion-source .path-display.not-set {
            color: #f85149;
            border-color: #f85149;
        }
        .digestion-source .actions {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        table { width: 100%; border-collapse: collapse; }
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #21262d;
        }
        th {
            background: #0d1117;
            color: #8b949e;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
        }
        tr:hover { background: #1c2128; }

        .status {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .status-pending { background: #1f2937; color: #9ca3af; }
        .status-uploading { background: #1e3a5f; color: #58a6ff; }
        .status-uploaded { background: #1a4731; color: #3fb950; }
        .status-error { background: #4a1e1e; color: #f85149; }
        .status-deleted { background: #2d1f1f; color: #8b949e; }
        .status-queued { background: #3d2f00; color: #d29922; }
        .status-running { background: #1e3a5f; color: #58a6ff; animation: pulse 2s infinite; }
        .status-stopped { background: #4a1e1e; color: #f85149; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .severity-info { color: #58a6ff; }
        .severity-warning { color: #d29922; }
        .severity-error { color: #f85149; }
        .severity-critical { color: #ff7b72; font-weight: bold; }

        .path {
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.875rem;
            color: #8b949e;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .filename { color: #58a6ff; }
        .timestamp { color: #8b949e; font-size: 0.875rem; }

        .form-group { margin-bottom: 16px; }
        .form-group label {
            display: block;
            color: #f0f6fc;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px 14px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #f0f6fc;
            font-size: 1rem;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #58a6ff;
            box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.3);
        }
        .form-help { color: #8b949e; font-size: 0.75rem; margin-top: 4px; }

        .btn {
            padding: 10px 20px;
            background: #238636;
            color: #fff;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.875rem;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #2ea043; }
        .btn-secondary { background: #21262d; }
        .btn-secondary:hover { background: #30363d; }
        .btn-danger { background: #da3633; }
        .btn-danger:hover { background: #f85149; }
        .btn-primary { background: #1f6feb; }
        .btn-primary:hover { background: #388bfd; }
        .btn-lg { padding: 14px 28px; font-size: 1rem; }

        .tabs { display: flex; border-bottom: 1px solid #30363d; margin-bottom: 0; }
        .tab {
            padding: 12px 20px;
            color: #8b949e;
            text-decoration: none;
            border-bottom: 2px solid transparent;
        }
        .tab:hover { color: #f0f6fc; }
        .tab.active { color: #f0f6fc; border-bottom-color: #f78166; }

        .empty { padding: 40px; text-align: center; color: #8b949e; }

        .progress-bar {
            height: 6px;
            background: #21262d;
            border-radius: 3px;
            overflow: hidden;
            width: 100px;
        }
        .progress-bar .fill {
            height: 100%;
            background: #58a6ff;
            transition: width 0.3s;
        }

        .alert {
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 16px;
        }
        .alert-success { background: #1a4731; border: 1px solid #238636; color: #3fb950; }
        .alert-error { background: #4a1e1e; border: 1px solid #da3633; color: #f85149; }
        .alert-info { background: #1e3a5f; border: 1px solid #1f6feb; color: #58a6ff; }
        .alert-warning { background: #3d2f00; border: 1px solid #9e6a03; color: #d29922; }

        .refresh-btn {
            background: none;
            border: 1px solid #30363d;
            color: #8b949e;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
        }
        .refresh-btn:hover { background: #21262d; color: #f0f6fc; }

        /* Directory Browser */
        .dir-browser {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
        }
        .dir-browser .current-path {
            padding: 12px 16px;
            background: #161b22;
            border-bottom: 1px solid #30363d;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.875rem;
            color: #58a6ff;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .dir-browser .items { padding: 8px; }
        .dir-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            color: #c9d1d9;
        }
        .dir-item:hover { background: #21262d; }
        .dir-item.selected { background: #1e3a5f; }
        .dir-item .icon { margin-right: 8px; width: 20px; }
        .dir-item .name { flex: 1; }
        .dir-item.folder .icon::before { content: "📁"; }
        .dir-item.file .icon::before { content: "📄"; }
        .dir-item.parent .icon::before { content: "⬆️"; }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            width: 90%;
            max-width: 700px;
            max-height: 80vh;
            overflow: hidden;
        }
        .modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-header h3 { color: #f0f6fc; }
        .modal-close {
            background: none;
            border: none;
            color: #8b949e;
            font-size: 1.5rem;
            cursor: pointer;
        }
        .modal-body { padding: 20px; overflow-y: auto; max-height: 60vh; }
        .modal-footer {
            padding: 16px 20px;
            border-top: 1px solid #30363d;
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }

        .daemon-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .daemon-status.running { background: #1a4731; color: #3fb950; }
        .daemon-status.stopped { background: #4a1e1e; color: #f85149; }
        .daemon-status .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }
        .daemon-status.running .dot { animation: pulse 1.5s infinite; }
    </style>
</head>
<body>
    <header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>CelesteOS Debug UI</h1>
                <span>Quality Inspection & Debugging Console</span>
            </div>
            <div class="daemon-status {{ 'running' if daemon_running else 'stopped' }}">
                <span class="dot"></span>
                Daemon: {{ 'Running' if daemon_running else 'Stopped' }}
            </div>
        </div>
    </header>

    <div class="container">
        <nav class="tabs">
            <a href="/" class="tab {{ 'active' if page == 'dashboard' else '' }}">Dashboard</a>
            <a href="/upload" class="tab {{ 'active' if page == 'upload' else '' }}" style="color: #58a6ff; font-weight: 600;">📤 UPLOAD</a>
            <a href="/files" class="tab {{ 'active' if page == 'files' else '' }}">Files</a>
            <a href="/queue" class="tab {{ 'active' if page == 'queue' else '' }}">Upload Queue</a>
            <a href="/errors" class="tab {{ 'active' if page == 'errors' else '' }}">Errors</a>
            <a href="/activity" class="tab {{ 'active' if page == 'activity' else '' }}">Activity</a>
            <a href="/source" class="tab {{ 'active' if page == 'source' else '' }}">⚡ Source Path</a>
        </nav>

        {% if message %}
        <div class="alert alert-{{ message_type }}">{{ message }}</div>
        {% endif %}

        {{ content|safe }}
    </div>

    <script>
        function openModal(id) {
            document.getElementById(id).classList.add('active');
        }
        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
'''

DASHBOARD_CONTENT = '''
<!-- Digestion Source - PROMINENT -->
<div class="digestion-source">
    <h2>Digestion Source Path</h2>
    <p class="subtitle">This is where ALL file ingestion begins. Files under this directory are scanned, hashed, and uploaded to the cloud.</p>
    <div class="path-display {{ 'not-set' if not nas_path else '' }}">
        {{ nas_path or '⚠️ NOT CONFIGURED - Click "Change Path" to set the source directory' }}
    </div>
    <div class="actions">
        <a href="/source" class="btn btn-lg btn-primary">📁 Change Path</a>
        <form method="POST" action="/scan/trigger" style="display:inline;">
            <button type="submit" class="btn btn-lg" {{ 'disabled' if not nas_path else '' }}>🔍 Run Scan Now</button>
        </form>
        {% if not daemon_running %}
        <span class="alert alert-warning" style="margin:0; padding:8px 12px;">Daemon not running - scans won't auto-process</span>
        {% endif %}
    </div>
</div>

<div class="grid">
    <div class="card">
        <h3>Total Files</h3>
        <div class="value info">{{ stats.total_files }}</div>
    </div>
    <div class="card">
        <h3>Uploaded</h3>
        <div class="value success">{{ stats.files_uploaded }}</div>
    </div>
    <div class="card">
        <h3>Pending</h3>
        <div class="value warning">{{ stats.files_pending }}</div>
    </div>
    <div class="card">
        <h3>Uploading</h3>
        <div class="value info">{{ stats.files_uploading }}</div>
    </div>
    <div class="card">
        <h3>Errors</h3>
        <div class="value error">{{ stats.files_error }}</div>
    </div>
    <div class="card">
        <h3>Bytes Uploaded</h3>
        <div class="value">{{ stats.bytes_uploaded }}</div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Sync State</h2>
    </div>
    <div style="padding: 16px;">
        <table>
            <tr><td style="width:200px; color:#8b949e;">Daemon Status</td><td><span class="status status-{{ sync_state.daemon_status }}">{{ sync_state.daemon_status }}</span></td></tr>
            <tr><td style="color:#8b949e;">Is Scanning</td><td>{{ '🔄 Yes' if sync_state.is_scanning else 'No' }}</td></tr>
            <tr><td style="color:#8b949e;">Is Uploading</td><td>{{ '📤 Yes' if sync_state.is_uploading else 'No' }}</td></tr>
            <tr><td style="color:#8b949e;">Last Scan</td><td class="timestamp">{{ sync_state.last_scan_completed }}</td></tr>
            <tr><td style="color:#8b949e;">Last Scan Duration</td><td>{{ sync_state.last_scan_duration_seconds or 0 }}s</td></tr>
        </table>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Recent Errors</h2>
        <a href="/errors" class="refresh-btn">View All</a>
    </div>
    {% if recent_errors %}
    <table>
        <thead>
            <tr><th>Type</th><th>Severity</th><th>Message</th><th>Time</th></tr>
        </thead>
        <tbody>
        {% for err in recent_errors %}
            <tr>
                <td>{{ err.error_type }}</td>
                <td class="severity-{{ err.severity }}">{{ err.severity }}</td>
                <td>{{ err.message[:80] }}...</td>
                <td class="timestamp">{{ err.created_at }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty">No errors - System healthy!</div>
    {% endif %}
</div>
'''

SOURCE_PATH_CONTENT = '''
<div class="digestion-source">
    <h2>Configure Digestion Source</h2>
    <p class="subtitle">Select the root folder containing all documents to ingest. This is typically done once during setup.</p>

    <div class="path-display {{ 'not-set' if not current_path else '' }}" id="current-path-display">
        Current: {{ current_path or 'Not configured' }}
    </div>
</div>

<!-- PRIMARY ACTION: Open Finder -->
<div class="section" style="border: 2px solid #1f6feb; background: linear-gradient(135deg, #1e3a5f 0%, #161b22 100%);">
    <div class="section-header" style="border-bottom: 1px solid #1f6feb;">
        <h2 style="color: #58a6ff;">📂 Select Folder in Finder</h2>
    </div>
    <div style="padding: 24px; text-align: center;">
        <p style="color: #8b949e; margin-bottom: 20px; font-size: 1rem;">
            Click the button below to open a native macOS Finder dialog and select your document root folder.
        </p>
        <button type="button" id="open-finder-btn" class="btn btn-lg btn-primary" style="font-size: 1.25rem; padding: 18px 40px;" onclick="openFinderPicker()">
            🗂️ Open Finder to Select Folder
        </button>
        <div id="picker-status" style="margin-top: 16px; color: #8b949e;"></div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Or Enter Path Manually</h2>
    </div>
    <div style="padding: 20px;">
        <form method="POST" action="/source/update">
            <div class="form-group">
                <label for="nas_path">Full Path to Source Directory</label>
                <input type="text" id="nas_path" name="nas_path" value="{{ current_path or '' }}"
                       placeholder="/Volumes/YachtNAS/Engineering" style="font-family: monospace; font-size: 1.1rem;">
                <p class="form-help">Enter the absolute path to the directory containing documents to ingest.</p>
            </div>

            <div class="form-group">
                <label>Quick Paths (click to use)</label>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
                    {% for p in common_paths %}
                    <button type="button" class="btn btn-secondary" style="font-family: monospace; font-size: 0.875rem;"
                            onclick="document.getElementById('nas_path').value='{{ p }}'">{{ p }}</button>
                    {% endfor %}
                </div>
            </div>

            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #30363d;">
                <button type="submit" class="btn btn-lg">💾 Save Path</button>
            </div>
        </form>
    </div>
</div>

<script>
async function openFinderPicker() {
    const btn = document.getElementById('open-finder-btn');
    const status = document.getElementById('picker-status');

    btn.disabled = true;
    btn.innerHTML = '⏳ Waiting for Finder selection...';
    status.innerHTML = '<span style="color: #58a6ff;">Finder dialog is open. Select a folder and click "Choose"...</span>';

    try {
        const response = await fetch('/api/pick-folder', { method: 'POST' });
        const data = await response.json();

        if (data.success && data.path) {
            status.innerHTML = '<span style="color: #3fb950;">✓ Selected: ' + data.path + '</span>';
            document.getElementById('nas_path').value = data.path;

            // Auto-save the path
            const saveResponse = await fetch('/source/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'nas_path=' + encodeURIComponent(data.path)
            });

            if (saveResponse.redirected) {
                window.location.href = saveResponse.url;
            } else {
                window.location.href = '/?message=Source path set to: ' + encodeURIComponent(data.path) + '&message_type=success';
            }
        } else if (data.error === 'cancelled') {
            status.innerHTML = '<span style="color: #d29922;">Selection cancelled</span>';
        } else {
            status.innerHTML = '<span style="color: #f85149;">Error: ' + (data.error || 'Unknown error') + '</span>';
        }
    } catch (err) {
        status.innerHTML = '<span style="color: #f85149;">Error: ' + err.message + '</span>';
    }

    btn.disabled = false;
    btn.innerHTML = '🗂️ Open Finder to Select Folder';
}
</script>

<div class="section">
    <div class="section-header">
        <h2>Browse Directories</h2>
    </div>
    <div style="padding: 20px;">
        <form method="GET" action="/source" style="margin-bottom: 16px;">
            <div style="display: flex; gap: 8px;">
                <input type="text" name="browse" value="{{ browse_path }}" placeholder="/Volumes"
                       style="flex:1; font-family: monospace;">
                <button type="submit" class="btn btn-secondary">Browse</button>
            </div>
        </form>

        {% if browse_items is not none %}
        <div class="dir-browser">
            <div class="current-path">
                📂 {{ browse_path }}
                {% if browse_path != '/' %}
                <a href="/source?browse={{ parent_path }}" style="color: #58a6ff; margin-left: auto;">⬆️ Up</a>
                {% endif %}
            </div>
            <div class="items">
                {% for item in browse_items %}
                {% if item.is_dir %}
                <div class="dir-item folder" onclick="window.location='/source?browse={{ item.path }}'">
                    <span class="icon"></span>
                    <span class="name">{{ item.name }}</span>
                    <form method="POST" action="/source/update" style="margin:0;" onclick="event.stopPropagation();">
                        <input type="hidden" name="nas_path" value="{{ item.path }}">
                        <button type="submit" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;">Select</button>
                    </form>
                </div>
                {% endif %}
                {% endfor %}

                {% for item in browse_items %}
                {% if not item.is_dir %}
                <div class="dir-item file">
                    <span class="icon"></span>
                    <span class="name" style="color: #8b949e;">{{ item.name }}</span>
                    <span style="color: #8b949e; font-size: 0.75rem;">{{ (item.size / 1024)|int }} KB</span>
                </div>
                {% endif %}
                {% endfor %}

                {% if not browse_items %}
                <div class="empty">Directory is empty</div>
                {% endif %}
            </div>
        </div>
        {% elif browse_error %}
        <div class="alert alert-error">{{ browse_error }}</div>
        {% endif %}
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Other Settings</h2>
    </div>
    <div style="padding: 20px;">
        <form method="POST" action="/source/settings">
            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div class="form-group">
                    <label for="scan_interval">Scan Interval (min)</label>
                    <input type="number" id="scan_interval" name="scan_interval_minutes"
                           value="{{ settings.scan_interval_minutes or 15 }}" min="1" max="1440">
                </div>
                <div class="form-group">
                    <label for="chunk_size">Chunk Size (MB)</label>
                    <input type="number" id="chunk_size" name="chunk_size_mb"
                           value="{{ settings.chunk_size_mb or 64 }}" min="1" max="256">
                </div>
                <div class="form-group">
                    <label for="max_concurrent">Max Uploads</label>
                    <input type="number" id="max_concurrent" name="max_concurrent_uploads"
                           value="{{ settings.max_concurrent_uploads or 3 }}" min="1" max="10">
                </div>
            </div>
            <button type="submit" class="btn">Save Settings</button>
        </form>
    </div>
</div>

{% if not daemon_running %}
<div class="alert alert-warning">
    <strong>Note:</strong> The daemon is not running. After changing the source path, start the daemon to begin scanning:
    <code style="background:#0d1117; padding:2px 6px; border-radius:4px; margin-left:8px;">python3 celesteos_daemon.py</code>
</div>
{% else %}
<div class="alert alert-info">
    <strong>Note:</strong> Changes to the source path will take effect on the next scan cycle, or restart the daemon for immediate effect.
</div>
{% endif %}
'''

FILES_CONTENT = '''
<div class="section">
    <div class="section-header">
        <h2>Files Registry ({{ total_files }} total)</h2>
        <div>
            <select id="statusFilter" onchange="window.location.href='?status='+this.value" style="padding:6px 12px; background:#0d1117; border:1px solid #30363d; border-radius:6px; color:#f0f6fc;">
                <option value="">All Statuses</option>
                <option value="pending" {{ 'selected' if filter_status == 'pending' else '' }}>Pending</option>
                <option value="queued" {{ 'selected' if filter_status == 'queued' else '' }}>Queued</option>
                <option value="uploading" {{ 'selected' if filter_status == 'uploading' else '' }}>Uploading</option>
                <option value="uploaded" {{ 'selected' if filter_status == 'uploaded' else '' }}>Uploaded</option>
                <option value="error" {{ 'selected' if filter_status == 'error' else '' }}>Error</option>
                <option value="deleted" {{ 'selected' if filter_status == 'deleted' else '' }}>Deleted</option>
            </select>
        </div>
    </div>
    {% if files %}
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Path</th>
                <th>Size</th>
                <th>Status</th>
                <th>SHA256</th>
                <th>Last Seen</th>
            </tr>
        </thead>
        <tbody>
        {% for f in files %}
            <tr>
                <td class="filename">{{ f.filename }}</td>
                <td class="path" title="{{ f.file_path }}">{{ f.file_path }}</td>
                <td>{{ f.file_size_fmt }}</td>
                <td><span class="status status-{{ f.status }}">{{ f.status }}</span></td>
                <td class="path">{{ f.sha256[:16] }}...</td>
                <td class="timestamp">{{ f.last_seen }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty">No files found</div>
    {% endif %}
</div>
'''

QUEUE_CONTENT = '''
<div class="section">
    <div class="section-header">
        <h2>Upload Queue</h2>
        <button class="refresh-btn" onclick="location.reload()">Refresh</button>
    </div>
    {% if uploads %}
    <table>
        <thead>
            <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Progress</th>
                <th>Status</th>
                <th>Retries</th>
                <th>Last Error</th>
            </tr>
        </thead>
        <tbody>
        {% for u in uploads %}
            <tr>
                <td class="filename">{{ u.filename }}</td>
                <td>{{ u.file_size_fmt }}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div class="progress-bar">
                            <div class="fill" style="width: {{ u.progress }}%;"></div>
                        </div>
                        <span>{{ u.uploaded_chunks }}/{{ u.total_chunks }}</span>
                    </div>
                </td>
                <td><span class="status status-{{ u.status }}">{{ u.status }}</span></td>
                <td>{{ u.retry_count }}/{{ u.max_retries }}</td>
                <td class="path" title="{{ u.last_error }}">{{ (u.last_error or '')[:40] }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty">No uploads in queue</div>
    {% endif %}
</div>
'''

ERRORS_CONTENT = '''
<div class="section">
    <div class="section-header">
        <h2>Errors ({{ total_errors }} unresolved)</h2>
        <form method="POST" action="/errors/resolve-all" style="display:inline;">
            <button type="submit" class="btn btn-danger" onclick="return confirm('Resolve all errors?')">Resolve All</button>
        </form>
    </div>
    {% if errors %}
    <table>
        <thead>
            <tr><th>Type</th><th>Severity</th><th>Message</th><th>File</th><th>Time</th></tr>
        </thead>
        <tbody>
        {% for e in errors %}
            <tr>
                <td>{{ e.error_type }}</td>
                <td class="severity-{{ e.severity }}">{{ e.severity }}</td>
                <td>{{ e.message }}</td>
                <td class="filename">{{ e.filename or '-' }}</td>
                <td class="timestamp">{{ e.created_at }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty">No errors - System healthy!</div>
    {% endif %}
</div>
'''

ACTIVITY_CONTENT = '''
<div class="section">
    <div class="section-header">
        <h2>Activity Log</h2>
        <button class="refresh-btn" onclick="location.reload()">Refresh</button>
    </div>
    {% if activities %}
    <table>
        <thead>
            <tr><th>Time</th><th>Type</th><th>Message</th></tr>
        </thead>
        <tbody>
        {% for a in activities %}
            <tr>
                <td class="timestamp">{{ a.created_at }}</td>
                <td><span class="status">{{ a.activity_type }}</span></td>
                <td>{{ a.message }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty">No activity recorded</div>
    {% endif %}
</div>
'''

UPLOAD_CONTENT = '''
<div class="digestion-source" style="border-color: #1f6feb; background: linear-gradient(135deg, #1e3a5f 0%, #162b16 100%);">
    <h2 style="color: #58a6ff;">📤 Batch Upload All Documents</h2>
    <p class="subtitle">Upload all discovered documents from configured source path to cloud for processing (ingestion, chunking, embedding, GraphRAG)</p>

    {% if upload_status.running %}
    <div class="alert alert-info" style="margin-top: 16px;">
        <strong>🔄 UPLOAD IN PROGRESS...</strong><br>
        Current File: <code>{{ upload_status.current_file }}</code><br>
        Progress: <strong>{{ upload_status.uploaded }}</strong> of <strong>{{ upload_status.total }}</strong> files uploaded
    </div>
    {% endif %}
</div>

<div class="grid">
    <div class="card">
        <h3>Total Files Found</h3>
        <div class="value info">{{ upload_status.total }}</div>
    </div>
    <div class="card">
        <h3>Successfully Uploaded</h3>
        <div class="value success">{{ upload_status.uploaded }}</div>
    </div>
    <div class="card">
        <h3>Failed</h3>
        <div class="value error">{{ upload_status.failed }}</div>
    </div>
    <div class="card">
        <h3>Upload Status</h3>
        <div class="value {{ 'warning' if upload_status.running else '' }}">{{ 'RUNNING' if upload_status.running else 'IDLE' }}</div>
    </div>
    <div class="card">
        <h3>Duration</h3>
        <div class="value">{{ upload_duration }}s</div>
    </div>
    <div class="card">
        <h3>Source Path</h3>
        <div class="value" style="font-size: 0.75rem; word-break: break-all;">{{ nas_path[:30] if nas_path else 'Not Set' }}...</div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Upload Controls</h2>
    </div>
    <div style="padding: 40px; text-align: center;">
        {% if not upload_status.running %}
            {% if nas_path %}
            <form method="POST" action="/upload/start" style="display: inline;">
                <button type="submit" class="btn btn-lg" style="background: #238636; font-size: 1.25rem; padding: 18px 40px;">
                    🚀 START BATCH UPLOAD
                </button>
            </form>
            <p style="color: #8b949e; margin-top: 16px;">This will upload ALL documents from: <code>{{ nas_path }}</code></p>
            {% else %}
            <div class="alert alert-error">
                ⚠️ <strong>Source path not configured!</strong><br>
                Go to <a href="/source" style="color: #58a6ff;">Source Path</a> tab to configure it first.
            </div>
            {% endif %}
        {% else %}
        <form method="POST" action="/upload/stop" style="display: inline;">
            <button type="submit" class="btn btn-lg btn-danger" style="font-size: 1.25rem; padding: 18px 40px;" onclick="return confirm('Stop upload and reset all progress?')">
                🛑 STOP UPLOAD & RESET
            </button>
        </form>
        <p style="color: #d29922; margin-top: 16px;">Upload in progress. Page will auto-refresh.</p>
        {% endif %}

        <div style="margin-top: 24px;">
            <button class="btn btn-secondary" onclick="location.reload()">🔄 Refresh Stats</button>
        </div>
    </div>
</div>

{% if upload_status.errors %}
<div class="section">
    <div class="section-header">
        <h2>Upload Errors ({{ upload_status.errors|length }} total)</h2>
    </div>
    <table>
        <thead>
            <tr><th>File</th><th>Error Message</th></tr>
        </thead>
        <tbody>
        {% for err in upload_status.errors[-30:] %}
            <tr>
                <td class="filename">{{ err.file }}</td>
                <td class="path" style="color: #f85149;">{{ err.message[:150] }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}

<script>
// Auto-refresh every 3 seconds when upload is running
{% if upload_status.running %}
setTimeout(() => location.reload(), 3000);
{% endif %}
</script>
'''


def render(content, page, **kwargs):
    """Render page with base template."""
    return render_template_string(
        BASE_HTML,
        content=render_template_string(content, **kwargs),
        page=page,
        daemon_running=is_daemon_running(),
        message=request.args.get('message'),
        message_type=request.args.get('message_type', 'info')
    )


@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to suppress 404."""
    return '', 204


@app.route('/')
def dashboard():
    conn = get_db()
    if not conn:
        return render('<div class="alert alert-error">Database not found at ~/.celesteos/celesteos.db<br>Run: <code>celesteos-agent setup</code></div>', 'dashboard')

    try:
        stats_row = conn.execute("SELECT * FROM v_sync_stats").fetchone()
        stats = dict(stats_row) if stats_row else {}

        sync_row = conn.execute("SELECT * FROM sync_state WHERE id = 1").fetchone()
        sync_state = dict(sync_row) if sync_row else {}

        settings_row = conn.execute("SELECT * FROM agent_settings WHERE id = 1").fetchone()
        nas_path = settings_row['nas_path'] if settings_row else None

        errors_rows = conn.execute("SELECT * FROM errors WHERE resolved = 0 ORDER BY created_at DESC LIMIT 5").fetchall()
        recent_errors = [dict(r) for r in errors_rows]

        formatted_stats = {
            'total_files': (stats.get('files_uploaded', 0) or 0) + (stats.get('files_pending', 0) or 0) +
                          (stats.get('files_uploading', 0) or 0) + (stats.get('files_error', 0) or 0),
            'files_uploaded': stats.get('files_uploaded', 0) or 0,
            'files_pending': stats.get('files_pending', 0) or 0,
            'files_uploading': stats.get('files_uploading', 0) or 0,
            'files_error': stats.get('files_error', 0) or 0,
            'bytes_uploaded': format_bytes(stats.get('total_bytes_uploaded', 0))
        }

        formatted_sync = {
            'daemon_status': sync_state.get('daemon_status', 'unknown'),
            'is_scanning': sync_state.get('is_scanning', 0),
            'is_uploading': sync_state.get('is_uploading', 0),
            'last_scan_completed': format_timestamp(sync_state.get('last_scan_completed')),
            'last_scan_duration_seconds': sync_state.get('last_scan_duration_seconds')
        }

        for e in recent_errors:
            e['created_at'] = format_timestamp(e['created_at'])

        return render(DASHBOARD_CONTENT, 'dashboard',
            stats=formatted_stats,
            sync_state=formatted_sync,
            nas_path=nas_path,
            recent_errors=recent_errors
        )
    finally:
        conn.close()


@app.route('/source')
def source_path():
    conn = get_db()
    settings = {}
    current_path = None

    if conn:
        try:
            row = conn.execute("SELECT * FROM agent_settings WHERE id = 1").fetchone()
            settings = dict(row) if row else {}
            current_path = settings.get('nas_path')
        finally:
            conn.close()

    # Directory browser
    browse_path = request.args.get('browse', '/Volumes')
    browse_items, browse_error = get_directory_listing(browse_path)
    parent_path = str(Path(browse_path).parent)

    # Common paths
    common_paths = [
        '/Volumes',
        '/Users',
        os.path.expanduser('~/Documents'),
        os.path.expanduser('~/Desktop'),
    ]
    # Add mounted volumes
    if Path('/Volumes').exists():
        for vol in Path('/Volumes').iterdir():
            if vol.is_dir() and not vol.name.startswith('.'):
                common_paths.append(str(vol))

    return render(SOURCE_PATH_CONTENT, 'source',
        current_path=current_path,
        settings=settings,
        browse_path=browse_path,
        browse_items=browse_items,
        browse_error=browse_error,
        parent_path=parent_path,
        common_paths=common_paths[:8]
    )


@app.route('/source/update', methods=['POST'])
def source_update():
    nas_path = request.form.get('nas_path', '').strip()

    if not nas_path:
        return redirect('/source?message=Path cannot be empty&message_type=error')

    # Validate path exists
    if not Path(nas_path).exists():
        return redirect(f'/source?message=Path does not exist: {nas_path}&message_type=error')

    if not Path(nas_path).is_dir():
        return redirect(f'/source?message=Path is not a directory: {nas_path}&message_type=error')

    conn = get_db()
    if not conn:
        return redirect('/source?message=Database not found&message_type=error')

    try:
        # Update database
        conn.execute("UPDATE agent_settings SET nas_path = ? WHERE id = 1", (nas_path,))
        conn.commit()

        # Also update config file
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                config['nas_path'] = nas_path
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not update config file: {e}")

        return redirect(f'/?message=Source path updated to: {nas_path}&message_type=success')
    except Exception as e:
        return redirect(f'/source?message=Error: {str(e)}&message_type=error')
    finally:
        conn.close()


@app.route('/source/settings', methods=['POST'])
def source_settings():
    conn = get_db()
    if not conn:
        return redirect('/source?message=Database not found&message_type=error')

    try:
        scan_interval = int(request.form.get('scan_interval_minutes', 15))
        chunk_size = int(request.form.get('chunk_size_mb', 64))
        max_concurrent = int(request.form.get('max_concurrent_uploads', 3))

        conn.execute("""
            UPDATE agent_settings SET
                scan_interval_minutes = ?,
                chunk_size_mb = ?,
                max_concurrent_uploads = ?
            WHERE id = 1
        """, (scan_interval, chunk_size, max_concurrent))
        conn.commit()

        return redirect('/source?message=Settings saved&message_type=success')
    finally:
        conn.close()


@app.route('/scan/trigger', methods=['POST'])
def trigger_scan():
    """Trigger a manual scan."""
    conn = get_db()
    if not conn:
        return redirect('/?message=Database not found&message_type=error')

    try:
        # Get NAS path
        row = conn.execute("SELECT nas_path FROM agent_settings WHERE id = 1").fetchone()
        if not row or not row['nas_path']:
            return redirect('/?message=Source path not configured&message_type=error')

        nas_path = row['nas_path']

        if not Path(nas_path).exists():
            return redirect(f'/?message=Source path does not exist: {nas_path}&message_type=error')

        # Log activity
        conn.execute("""
            INSERT INTO activity_log (activity_type, message)
            VALUES ('scan_started', 'Manual scan triggered from Debug UI')
        """)
        conn.commit()

        # Run scan in background thread
        def run_scan():
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent))
                from celesteos_agent.database import Database
                from celesteos_agent.scanner import FileScanner

                db = Database()
                ignore_patterns = db.get_ignore_patterns()
                scanner = FileScanner(db=db, nas_path=nas_path, ignore_patterns=ignore_patterns)
                stats = scanner.scan(full_scan=True, max_depth=50)
                print(f"Scan complete: {stats}")
            except Exception as e:
                print(f"Scan error: {e}")

        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()

        return redirect('/?message=Scan started - check activity log for progress&message_type=success')
    finally:
        conn.close()


@app.route('/files')
def files():
    conn = get_db()
    if not conn:
        return redirect('/')

    try:
        filter_status = request.args.get('status', '')

        if filter_status:
            rows = conn.execute("SELECT * FROM files WHERE status = ? ORDER BY last_seen DESC LIMIT 200", (filter_status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM files ORDER BY last_seen DESC LIMIT 200").fetchall()

        total_row = conn.execute("SELECT COUNT(*) as cnt FROM files").fetchone()
        total_files = total_row['cnt'] if total_row else 0

        files_list = []
        for r in rows:
            f = dict(r)
            f['file_size_fmt'] = format_bytes(f['file_size'])
            f['last_seen'] = format_timestamp(f['last_seen'])
            files_list.append(f)

        return render(FILES_CONTENT, 'files', files=files_list, total_files=total_files, filter_status=filter_status)
    finally:
        conn.close()


@app.route('/queue')
def queue():
    conn = get_db()
    if not conn:
        return redirect('/')

    try:
        rows = conn.execute("""
            SELECT * FROM upload_queue
            WHERE status IN ('pending', 'initializing', 'uploading', 'paused', 'error')
            ORDER BY created_at DESC LIMIT 100
        """).fetchall()

        uploads = []
        for r in rows:
            u = dict(r)
            u['file_size_fmt'] = format_bytes(u['file_size'])
            u['progress'] = (u['uploaded_chunks'] / u['total_chunks'] * 100) if u['total_chunks'] > 0 else 0
            uploads.append(u)

        return render(QUEUE_CONTENT, 'queue', uploads=uploads)
    finally:
        conn.close()


@app.route('/errors')
def errors():
    conn = get_db()
    if not conn:
        return redirect('/')

    try:
        rows = conn.execute("""
            SELECT e.*, f.filename
            FROM errors e
            LEFT JOIN files f ON e.file_id = f.id
            WHERE e.resolved = 0
            ORDER BY e.created_at DESC LIMIT 200
        """).fetchall()

        total_row = conn.execute("SELECT COUNT(*) as cnt FROM errors WHERE resolved = 0").fetchone()
        total_errors = total_row['cnt'] if total_row else 0

        errors_list = []
        for r in rows:
            e = dict(r)
            e['created_at'] = format_timestamp(e['created_at'])
            errors_list.append(e)

        return render(ERRORS_CONTENT, 'errors', errors=errors_list, total_errors=total_errors)
    finally:
        conn.close()


@app.route('/errors/resolve-all', methods=['POST'])
def resolve_all_errors():
    conn = get_db()
    if conn:
        try:
            conn.execute("UPDATE errors SET resolved = 1, resolved_at = ? WHERE resolved = 0", (int(time.time()),))
            conn.commit()
        finally:
            conn.close()
    return redirect('/errors?message=All errors resolved&message_type=success')


@app.route('/activity')
def activity():
    conn = get_db()
    if not conn:
        return redirect('/')

    try:
        rows = conn.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 100").fetchall()
        activities = []
        for r in rows:
            a = dict(r)
            a['created_at'] = format_timestamp(a['created_at'])
            activities.append(a)

        return render(ACTIVITY_CONTENT, 'activity', activities=activities)
    finally:
        conn.close()


@app.route('/api/stats')
def api_stats():
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database not found'}), 404

    try:
        stats_row = conn.execute("SELECT * FROM v_sync_stats").fetchone()
        sync_row = conn.execute("SELECT * FROM sync_state WHERE id = 1").fetchone()
        settings_row = conn.execute("SELECT nas_path FROM agent_settings WHERE id = 1").fetchone()

        return jsonify({
            'stats': dict(stats_row) if stats_row else {},
            'sync_state': dict(sync_row) if sync_row else {},
            'nas_path': settings_row['nas_path'] if settings_row else None,
            'daemon_running': is_daemon_running()
        })
    finally:
        conn.close()


@app.route('/api/pick-folder', methods=['POST'])
def api_pick_folder():
    """Open native macOS Finder folder picker and return selected path."""
    path, error = open_macos_folder_picker()

    if path:
        return jsonify({'success': True, 'path': path})
    else:
        return jsonify({'success': False, 'error': error or 'No folder selected'})


@app.route('/upload')
def upload_page():
    """Upload management page with real-time progress."""
    global async_uploader

    conn = get_db()
    nas_path = None

    if conn:
        try:
            row = conn.execute("SELECT nas_path FROM agent_settings WHERE id = 1").fetchone()
            nas_path = row['nas_path'] if row else None
        finally:
            conn.close()

    # Initialize async uploader if needed
    if async_uploader is None:
        async_uploader = create_async_uploader(
            webhook_endpoint=WEBHOOK_ENDPOINT,
            yacht_id=YACHT_ID,
            yacht_salt=YACHT_SALT,
            auto_start=True
        )

    # Get progress from async uploader
    progress = async_uploader.get_progress()
    queue_status = async_uploader.get_queue_status()

    # Convert to format expected by template
    upload_status = {
        "running": progress['is_uploading'] or progress['queue_pending'] > 0,
        "total": progress['queue_total'],
        "uploaded": progress['queue_completed'],
        "failed": progress['queue_failed'],
        "current_file": progress['current_file'] or "",
        "start_time": None,  # Not tracked in async uploader
        "errors": [{"file": item['filename'], "message": item['error']}
                   for item in queue_status.get('failed_items', [])]
    }

    return render(UPLOAD_CONTENT, 'upload',
        upload_status=upload_status,
        nas_path=nas_path,
        upload_duration=0  # Not tracked
    )


@app.route('/upload/start', methods=['POST'])
def upload_start():
    """Start batch upload of all documents from NAS using async uploader."""
    global async_uploader

    conn = get_db()
    if not conn:
        return redirect('/upload?message=Database not found&message_type=error')

    try:
        row = conn.execute("SELECT nas_path FROM agent_settings WHERE id = 1").fetchone()
        nas_path = row['nas_path'] if row else None
    finally:
        conn.close()

    if not nas_path or not Path(nas_path).exists():
        return redirect('/upload?message=Source path not configured or does not exist&message_type=error')

    # Initialize async uploader if needed
    if async_uploader is None:
        async_uploader = create_async_uploader(
            webhook_endpoint=WEBHOOK_ENDPOINT,
            yacht_id=YACHT_ID,
            yacht_salt=YACHT_SALT,
            auto_start=True
        )

    # Find all documents and add to queue
    nas_root = Path(nas_path)
    documents_added = 0

    print(f"[UPLOAD] Scanning {nas_root} for documents...")

    for file_path in nas_root.rglob('*'):
        if file_path.is_file() and is_supported_file(file_path):
            try:
                # Extract metadata
                metadata = extract_metadata_from_path(file_path, nas_root=nas_root)

                # Add to async upload queue (non-blocking)
                async_uploader.add_to_queue(
                    file_path=str(file_path),
                    system_path=metadata['system_path'],
                    directories=metadata['directories'],
                    doc_type=metadata['doc_type'],
                    system_tag=metadata['system_tag'],
                    priority=5
                )

                documents_added += 1

            except Exception as e:
                print(f"[UPLOAD] Failed to queue {file_path.name}: {e}")

    print(f"[UPLOAD] Added {documents_added} documents to upload queue")

    return redirect(f'/upload?message=Added {documents_added} documents to upload queue. Background processor will handle uploads.&message_type=success')


@app.route('/upload/stop', methods=['POST'])
def upload_stop():
    """Pause async upload processing."""
    global async_uploader

    if async_uploader:
        async_uploader.pause()
        return redirect('/upload?message=Upload processing paused (queue preserved)&message_type=success')

    return redirect('/upload?message=No uploader running&message_type=warning')


@app.route('/upload/resume', methods=['POST'])
def upload_resume():
    """Resume async upload processing."""
    global async_uploader

    if async_uploader:
        async_uploader.resume()
        return redirect('/upload?message=Upload processing resumed&message_type=success')

    return redirect('/upload?message=No uploader running&message_type=warning')


@app.route('/upload/retry-failed', methods=['POST'])
def upload_retry_failed():
    """Retry all permanently failed uploads."""
    global async_uploader

    if async_uploader:
        async_uploader.retry_all_failed()
        return redirect('/upload?message=Retrying all failed uploads&message_type=success')

    return redirect('/upload?message=No uploader running&message_type=warning')


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  CelesteOS Debug UI")
    print("="*60)
    print(f"\n  Database: {DB_PATH}")
    print(f"  Config:   {CONFIG_PATH}")
    print(f"\n  Starting server at: http://localhost:5050")
    print("\n  Key Features:")
    print("    - Dashboard: Overview + quick source path access")
    print("    - Source Path: SET WHERE DIGESTION STARTS")
    print("    - Files: Browse all discovered files")
    print("    - Trigger scans manually")
    print("\n  Press Ctrl+C to stop\n")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5050, debug=True)
