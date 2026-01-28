# Receiving Lens - Root Cause: Build Path Mismatch

**Date**: 2026-01-28 19:30 UTC
**Status**: 🔴 CRITICAL - Build configuration broken
**Root Cause**: build.sh and render.yaml reference wrong directory paths

---

## The Real Problem

The deployment failure isn't about security middleware or env vars - it's a **fundamental path mismatch** in the build configuration.

### Path Mismatch Analysis

**Actual Repository Structure**:
```
/repo-root/
  ├── apps/
  │   └── api/
  │       ├── pipeline_service.py
  │       ├── requirements.txt
  │       ├── handlers/
  │       └── ...
  └── build.sh
```

**What build.sh Expects** (line 9):
```bash
pip install -r api/requirements.txt  # ❌ WRONG - this file doesn't exist
```

**What Actually Exists**:
```bash
apps/api/requirements.txt  # ✅ CORRECT path
```

**What render.yaml Says**:
```yaml
services:
  - name: celeste-pipeline-v1
    buildCommand: chmod +x build.sh && ./build.sh  # Uses broken build.sh
    startCommand: uvicorn api.pipeline_service:app  # Expects api/ not apps/api/
```

**What the Worker Service Does** (correctly):
```yaml
  - name: celeste-email-watcher
    buildCommand: cd apps/api && pip install -r requirements.txt  # ✅ CORRECT
    startCommand: cd apps/api && python -m workers.email_watcher_worker  # ✅ CORRECT
```

---

## Why This Causes "no-server"

1. **Build Phase Fails**:
   - Render runs `./build.sh`
   - build.sh tries to `pip install -r api/requirements.txt`
   - File doesn't exist → **pip install fails**
   - Build fails → No server binary to run

2. **OR Start Phase Fails**:
   - Even if build somehow passed, startCommand tries:
   - `uvicorn api.pipeline_service:app`
   - This expects `api/pipeline_service.py` in current directory
   - File doesn't exist → **uvicorn fails to import**
   - Server fails to start → Render shows "no-server"

---

## Evidence

**File does NOT exist**:
```bash
$ ls ../../api/requirements.txt
ls: ../../api/requirements.txt: No such file or directory
```

**File DOES exist here**:
```bash
$ ls ../../apps/api/requirements.txt
-rw-r--r--@ 1 celeste7  staff  625 16 Jan 06:27 ../../apps/api/requirements.txt
```

**Pipeline service location**:
```bash
$ ls ../../apps/api/pipeline_service.py
-rw-r--r--@ 1 celeste7  staff  47424 27 Jan 20:48 pipeline_service.py
```

---

## Why This Wasn't Caught Earlier

This suggests either:
1. **Render has been broken for a while** and nobody noticed
2. **There was a symlink** `api -> apps/api` that got removed
3. **Render was using different configuration** (dashboard overrides?)
4. **Recent change broke previously working setup**

---

## Fix Options

### Option 1: Fix build.sh and render.yaml (RECOMMENDED)

**Update build.sh** to use correct paths:
```bash
#!/bin/bash
set -e

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r apps/api/requirements.txt  # FIX: apps/api not api

echo "=== Downloading spaCy English model ==="
python -m spacy download en_core_web_sm

echo "=== Verifying spaCy installation ==="
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy model loaded successfully')"

echo "=== Build complete ==="
```

**Update render.yaml** to use correct start command:
```yaml
services:
  - type: web
    name: celeste-pipeline-v1
    runtime: python
    plan: starter
    region: oregon
    branch: main
    buildCommand: chmod +x build.sh && ./build.sh
    startCommand: cd apps/api && uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT  # FIX: cd into apps/api first
    healthCheckPath: /health
    # ... rest unchanged
```

### Option 2: Inline Commands (Like Worker Service)

**Update render.yaml** to not use build.sh at all:
```yaml
services:
  - type: web
    name: celeste-pipeline-v1
    runtime: python
    plan: starter
    region: oregon
    branch: main
    buildCommand: cd apps/api && pip install --upgrade pip && pip install -r requirements.txt && python -m spacy download en_core_web_sm
    startCommand: cd apps/api && uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    # ... rest unchanged
```

### Option 3: Create Symlink (Quick Hack)

**Create symlink** from root:
```bash
ln -s apps/api api
git add api
git commit -m "fix: Add symlink api -> apps/api for Render compatibility"
git push origin main
```

This makes `api/` and `apps/api/` both work.

---

## Recommended Action

**Fix both files** (Option 1):

```bash
# Update build.sh
cat > build.sh <<'EOF'
#!/bin/bash
set -e

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r apps/api/requirements.txt

echo "=== Downloading spaCy English model ==="
python -m spacy download en_core_web_sm

echo "=== Verifying spaCy installation ==="
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy model loaded successfully')"

echo "=== Build complete ==="
EOF

# Make executable
chmod +x build.sh

# Update render.yaml startCommand (line 10)
# Change from: uvicorn api.pipeline_service:app --host 0.0.0.0 --port $PORT
# Change to:   cd apps/api && uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT

# Commit and push
git add build.sh render.yaml
git commit -m "fix(deploy): Correct paths for apps/api structure in build and start commands"
git push origin main
```

---

## Impact on Receiving Lens

**Current Status**: ALL API endpoints down due to build/start failure

**After Fix**: API should come back online within 3-5 minutes

**Then Resume**:
- Test view_history fix
- Test prepare mode fix
- Debug RLS enforcement
- Complete Checkpoint 2

---

## Summary

**Problem**: build.sh and render.yaml reference `api/` but actual structure is `apps/api/`
**Impact**: Build fails → Server never starts → "no-server" routing error
**Fix**: Update paths in build.sh and render.yaml to use `apps/api/`
**Time to Fix**: 5 minutes + 3-5 minute redeploy
**Confidence**: 99% this is the root cause
