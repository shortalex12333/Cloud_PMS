#!/usr/bin/env python3
"""
CelesteOS Debug UI - WITH BATCH UPLOAD SUPPORT
Run: python3 debug_ui_with_uploads.py
Access: http://localhost:5050
"""

import sqlite3
import json
import time
import os
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, redirect, url_for

# Add current directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from celesteos_agent.uploader import FileUploader
from celesteos_agent.metadata_extractor import extract_metadata_from_path, is_supported_file

app = Flask(__name__)

# Database path
DB_PATH = Path("~/.celesteos/celesteos.db").expanduser()
CONFIG_PATH = Path("~/.celesteos/config.json").expanduser()
PID_FILE = Path("~/.celesteos/celesteos-agent.pid").expanduser()

# Track scan & upload status
scan_status = {"running": False, "message": "", "progress": 0}
upload_status = {
    "running": False,
    "total": 0,
    "uploaded": 0,
    "failed": 0,
    "skipped": 0,
    "current_file": "",
    "start_time": None,
    "errors": []
}

# Global uploader
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
WEBHOOK_ENDPOINT = "https://api.celeste7.ai"
uploader = None


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


# HTML Templates (reusing same BASE_HTML from original)
# ... (keeping all the CSS and HTML templates from original file) ...

# NEW: UPLOAD CONTENT TEMPLATE
UPLOAD_CONTENT = '''
<div class="digestion-source" style="border-color: #1f6feb; background: linear-gradient(135deg, #1e3a5f 0%, #162b16 100%);">
    <h2 style="color: #58a6ff;">📤 Batch Upload Documents</h2>
    <p class="subtitle">Upload all documents from configured source path to cloud for processing</p>

    {% if upload_status.running %}
    <div class="alert alert-info">
        <strong>🔄 Upload in Progress...</strong><br>
        Current: {{ upload_status.current_file }}<br>
        Progress: {{ upload_status.uploaded }}/{{ upload_status.total }} uploaded
    </div>
    {% endif %}
</div>

<div class="grid">
    <div class="card">
        <h3>Total Files</h3>
        <div class="value info">{{ upload_status.total }}</div>
    </div>
    <div class="card">
        <h3>Uploaded</h3>
        <div class="value success">{{ upload_status.uploaded }}</div>
    </div>
    <div class="card">
        <h3>Failed</h3>
        <div class="value error">{{ upload_status.failed }}</div>
    </div>
    <div class="card">
        <h3>Skipped</h3>
        <div class="value warning">{{ upload_status.skipped }}</div>
    </div>
    <div class="card">
        <h3>Status</h3>
        <div class="value">{{ 'Running' if upload_status.running else 'Idle' }}</div>
    </div>
    <div class="card">
        <h3>Duration</h3>
        <div class="value">{{ upload_duration }}s</div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Upload Controls</h2>
    </div>
    <div style="padding: 24px; text-align: center;">
        {% if not upload_status.running %}
        <form method="POST" action="/upload/start" style="display: inline;">
            <button type="submit" class="btn btn-lg btn-primary" {{ 'disabled' if not nas_path else '' }}>
                🚀 Start Upload
            </button>
        </form>
        {% if not nas_path %}
        <p style="color: #f85149; margin-top: 16px;">⚠️ Configure source path first!</p>
        {% endif %}
        {% else %}
        <button class="btn btn-lg btn-danger" disabled>
            ⏸️ Upload Running...
        </button>
        {% endif %}

        <div style="margin-top: 16px;">
            <button class="btn btn-secondary" onclick="location.reload()">🔄 Refresh Stats</button>
        </div>
    </div>
</div>

{% if upload_status.errors %}
<div class="section">
    <div class="section-header">
        <h2>Recent Upload Errors ({{ upload_status.errors|length }})</h2>
    </div>
    <table>
        <thead>
            <tr><th>File</th><th>Error</th></tr>
        </thead>
        <tbody>
        {% for err in upload_status.errors[-20:] %}
            <tr>
                <td class="filename">{{ err.file }}</td>
                <td class="path">{{ err.message[:100] }}</td>
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


# (Include all original HTML templates here - BASE_HTML, DASHBOARD_CONTENT, etc.)
# For brevity, I'll add just the key parts...

BASE_HTML_WITH_UPLOAD_TAB = '''
<!DOCTYPE html>
<html>
<head>
    <title>CelesteOS Debug UI</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* ... (all original CSS) ... */
    </style>
</head>
<body>
    <header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>CelesteOS Debug UI</h1>
                <span>Quality Inspection & Upload Console</span>
            </div>
        </div>
    </header>

    <div class="container">
        <nav class="tabs">
            <a href="/" class="tab {{ 'active' if page == 'dashboard' else '' }}">Dashboard</a>
            <a href="/upload" class="tab {{ 'active' if page == 'upload' else '' }}">📤 Upload</a>
            <a href="/files" class="tab {{ 'active' if page == 'files' else '' }}">Files</a>
            <a href="/source" class="tab {{ 'active' if page == 'source' else '' }}">⚡ Source Path</a>
        </nav>

        {% if message %}
        <div class="alert alert-{{ message_type }}">{{ message }}</div>
        {% endif %}

        {{ content|safe }}
    </div>
</body>
</html>
'''


def render(content, page, **kwargs):
    """Render page with base template."""
    return render_template_string(
        BASE_HTML_WITH_UPLOAD_TAB,
        content=render_template_string(content, **kwargs),
        page=page,
        message=request.args.get('message'),
        message_type=request.args.get('message_type', 'info')
    )


@app.route('/upload')
def upload_page():
    """Upload management page."""
    conn = get_db()
    nas_path = None

    if conn:
        try:
            row = conn.execute("SELECT nas_path FROM agent_settings WHERE id = 1").fetchone()
            nas_path = row['nas_path'] if row else None
        finally:
            conn.close()

    # Calculate duration
    duration = 0
    if upload_status["start_time"]:
        duration = int(time.time() - upload_status["start_time"])

    return render(UPLOAD_CONTENT, 'upload',
        upload_status=upload_status,
        nas_path=nas_path,
        upload_duration=duration
    )


@app.route('/upload/start', methods=['POST'])
def upload_start():
    """Start batch upload."""
    global uploader, upload_status

    if upload_status["running"]:
        return redirect('/upload?message=Upload already running&message_type=warning')

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

    # Initialize uploader
    uploader = FileUploader(WEBHOOK_ENDPOINT, YACHT_ID)

    # Reset status
    upload_status = {
        "running": True,
        "total": 0,
        "uploaded": 0,
        "failed": 0,
        "skipped": 0,
        "current_file": "",
        "start_time": time.time(),
        "errors": []
    }

    # Run upload in background
    def run_upload():
        global upload_status
        try:
            nas_root = Path(nas_path)

            # Find all documents
            documents = []
            for file_path in nas_root.rglob('*'):
                if file_path.is_file() and is_supported_file(file_path):
                    documents.append(file_path)

            upload_status["total"] = len(documents)

            # Upload each document
            for file_path in documents:
                if not upload_status["running"]:
                    break

                upload_status["current_file"] = file_path.name

                try:
                    # Extract metadata
                    metadata = extract_metadata_from_path(file_path, nas_root=nas_root)

                    # Upload
                    result = uploader.upload_file(
                        file_path=file_path,
                        system_path=metadata['system_path'],
                        directories=metadata['directories'],
                        doc_type=metadata['doc_type'],
                        system_tag=metadata['system_tag']
                    )

                    upload_status["uploaded"] += 1

                except Exception as e:
                    upload_status["failed"] += 1
                    upload_status["errors"].append({
                        "file": file_path.name,
                        "message": str(e)
                    })

                time.sleep(0.3)  # Rate limit

        except Exception as e:
            upload_status["errors"].append({
                "file": "SYSTEM",
                "message": f"Fatal error: {str(e)}"
            })
        finally:
            upload_status["running"] = False
            upload_status["current_file"] = ""

    thread = threading.Thread(target=run_upload, daemon=True)
    thread.start()

    return redirect('/upload?message=Upload started!&message_type=success')


@app.route('/')
def dashboard():
    return render('<div style="padding: 40px; text-align: center;"><h2>Welcome to CelesteOS Upload Manager</h2><p>Use the tabs above to navigate</p></div>', 'dashboard')


@app.route('/files')
def files():
    return render('<div style="padding: 40px; text-align: center;"><h2>Files</h2></div>', 'files')


@app.route('/source')
def source():
    return render('<div style="padding: 40px; text-align: center;"><h2>Source Path</h2><p>Configure via original UI</p></div>', 'source')


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  CelesteOS Upload Manager")
    print("="*60)
    print(f"\n  Starting server at: http://localhost:5050")
    print("\n  Features:")
    print("    - Real-time upload progress tracking")
    print("    - Visual stats dashboard")
    print("    - Error monitoring")
    print("\n  Press Ctrl+C to stop\n")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5051, debug=False)
