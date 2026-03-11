# Structural Cleanup Migration Plan

> **Status**: READY FOR EXECUTION
> **Date**: 2026-02-27
> **Risk Level**: LOW (with parallel agent verification)
> **Rollback**: Git revert (all changes atomic per phase)

---

## Executive Summary

This plan removes structural debt while **protecting the F1 Cortex Search Engine**. All F1/Cortex files are explicitly protected and will not be modified.

**Operations:**
- 1 file DELETE (dead code)
- 1 file DELETE (duplicate, after migration)
- 2 files RENAME (clarity)
- 2 files MOVE (correct location)

**Protected Systems:**
- F1 Search Streaming (`f1_search_streaming.py`)
- Cortex Rewrites (`cortex/rewrites.py`)
- All 5 Workers (projection, embedding, nightly feedback, etc.)
- All database RPCs (`f1_search_cards`, `match_search_index`)
- Frontend hooks (`useCelesteSearch.ts`)

---

## F1/Cortex Protected File List (DO NOT TOUCH)

```
CRITICAL - ZERO MODIFICATIONS ALLOWED:

Backend F1 Core:
├── apps/api/routes/f1_search_streaming.py      # F1 SSE endpoint
├── apps/api/cortex/rewrites.py                 # Cortex intelligence
├── apps/api/cortex/__init__.py
├── apps/api/workers/projection_worker.py       # Worker 4
├── apps/api/workers/embedding_worker_1536.py   # Worker 5
├── apps/api/workers/nightly_feedback_loop.py   # Learning loop
├── apps/api/cache/invalidation_listener.py     # Cache coherence

Database F1 Core:
├── database/migrations/40_create_f1_search_cards.sql
├── database/migrations/41_f1_search_deterministic_ordering.sql
├── database/migrations/44_match_search_index_rpc.sql
├── database/migrations/45_f1_search_cards_with_search_text.sql
├── database/migrations/01_create_search_index.sql

Frontend F1:
├── apps/web/src/hooks/useCelesteSearch.ts
├── apps/web/src/components/spotlight/SpotlightSearch.tsx

Infrastructure:
├── docker-compose.f1-workers.yml
├── render.yaml
```

---

## Phase 1: DELETE Dead Code (Zero Risk)

### Target: `pipeline_v1.py`

**Evidence:**
- 0 imports across entire codebase
- Not in Procfile (uses `pipeline_service:app`)
- Not in Dockerfile (uses `microaction_service:app`)
- Superseded by `pipeline_service.py`

**Execution:**
```bash
# Single command - no dependencies
rm apps/api/pipeline_v1.py
git add -A && git commit -m "chore: remove dead pipeline_v1.py (superseded by pipeline_service.py)

- Zero imports found across codebase
- Not referenced in Procfile or Dockerfile
- Git history preserves if ever needed

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Verification:**
```bash
# Confirm no broken imports
cd apps/api && python -c "import pipeline_service" && echo "OK"
```

**Rollback:**
```bash
git revert HEAD
```

---

## Phase 2: RENAME Rate Limiters (Low Risk)

### Target 1: `services/rate_limit.py` → `services/search_rate_limiter.py`

**Import Chain:**
| File | Line | Current Import |
|------|------|----------------|
| `routes/search_streaming.py` | 60-70 | `from services.rate_limit import (...)` |

**Execution (Sub-Agent 1):**
```python
# Step 1: Rename file
mv apps/api/services/rate_limit.py apps/api/services/search_rate_limiter.py

# Step 2: Update import in search_streaming.py (line 60-70)
# FROM: from services.rate_limit import (...)
# TO:   from services.search_rate_limiter import (...)
```

### Target 2: `services/rate_limiter.py` → `services/graph_api_rate_limiter.py`

**Import Chain:**
| File | Line | Current Import |
|------|------|----------------|
| `services/__init__.py` | 7 | `from .rate_limiter import MicrosoftRateLimiter` |
| `services/email_sync_service.py` | 14 | `from .rate_limiter import MicrosoftRateLimiter` |
| `workers/email_watcher_worker.py` | 35 | `from services.rate_limiter import MicrosoftRateLimiter` |

**Execution (Sub-Agent 2):**
```python
# Step 1: Rename file
mv apps/api/services/rate_limiter.py apps/api/services/graph_api_rate_limiter.py

# Step 2: Update imports in 3 files
# services/__init__.py:7
# FROM: from .rate_limiter import MicrosoftRateLimiter
# TO:   from .graph_api_rate_limiter import MicrosoftRateLimiter

# services/email_sync_service.py:14
# FROM: from .rate_limiter import MicrosoftRateLimiter
# TO:   from .graph_api_rate_limiter import MicrosoftRateLimiter

# workers/email_watcher_worker.py:35
# FROM: from services.rate_limiter import MicrosoftRateLimiter
# TO:   from services.graph_api_rate_limiter import MicrosoftRateLimiter
```

**Verification:**
```bash
cd apps/api
python -c "from services.search_rate_limiter import get_rate_limiter; print('search OK')"
python -c "from services.graph_api_rate_limiter import MicrosoftRateLimiter; print('graph OK')"
python -c "from services import MicrosoftRateLimiter; print('init OK')"
```

**Commit:**
```bash
git add -A && git commit -m "refactor: rename rate limiters for clarity

- rate_limit.py → search_rate_limiter.py (streaming search)
- rate_limiter.py → graph_api_rate_limiter.py (MS Graph API)
- Updated 4 import sites

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: DELETE Duplicate Extractor (Low Risk)

### Target: `email_rag/entity_extractor.py`

**Evidence:**
- Documented as "copied from extraction/regex_extractor.py patterns"
- Duplicates `extraction/entity_extractor.py` functionality
- Only 2 importers - easy migration

**Import Chain:**
| File | Line | Current Import |
|------|------|----------------|
| `email_rag/query_parser.py` | 370 | `from email_rag.entity_extractor import extract_keywords_for_search` |
| `routes/email.py` | 783 | `from email_rag.entity_extractor import EmailEntityExtractor` |

**Migration Strategy:**
The canonical `extraction/entity_extractor.py` has `get_extractor()` returning `MaritimeEntityExtractor`. We need to:
1. Create a thin adapter in `extraction/` that provides `extract_keywords_for_search()` function
2. Update imports to use canonical extractor
3. Delete duplicate

**Execution (Sub-Agent 3):**
```python
# Step 1: Add adapter function to extraction/entity_extractor.py
# (or create extraction/email_adapter.py)
def extract_keywords_for_search(query: str) -> list[str]:
    """Adapter for email search - extracts keywords from query."""
    extractor = get_extractor()
    entities = extractor.extract_entities(query)
    return [e.value for e in entities]

# Step 2: Update email_rag/query_parser.py:370
# FROM: from email_rag.entity_extractor import extract_keywords_for_search
# TO:   from extraction.entity_extractor import extract_keywords_for_search

# Step 3: Update routes/email.py:783
# FROM: from email_rag.entity_extractor import EmailEntityExtractor
# TO:   from extraction.entity_extractor import get_extractor as get_email_extractor
# (usage change: EmailEntityExtractor() → get_email_extractor())

# Step 4: Delete duplicate
rm apps/api/email_rag/entity_extractor.py
```

**Verification:**
```bash
cd apps/api
python -c "from extraction.entity_extractor import extract_keywords_for_search; print('adapter OK')"
python -c "from email_rag.query_parser import *; print('query_parser OK')"
```

**Commit:**
```bash
git add -A && git commit -m "refactor: consolidate entity extractors to single source

- Removed duplicate email_rag/entity_extractor.py
- Added extract_keywords_for_search() adapter to canonical extractor
- Updated 2 import sites (query_parser.py, email.py)
- Single source of truth: extraction/entity_extractor.py

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: MOVE Root Orphans (Medium Risk)

### Target 1: `entity_extraction_loader.py` → `extraction/loader.py`

**Import Chain (uses try/except dual-path):**
| File | Lines | Current Import |
|------|-------|----------------|
| `extraction/entity_extractor.py` | 52, 62 | `from api.entity_extraction_loader import (...)` with fallback |
| `extraction/regex_extractor.py` | 27, 38 | `from api.entity_extraction_loader import (...)` with fallback |

**Execution (Sub-Agent 4):**
```python
# Step 1: Move file
mv apps/api/entity_extraction_loader.py apps/api/extraction/loader.py

# Step 2: Update extraction/entity_extractor.py (lines 52-68)
# FROM:
#   try:
#       from api.entity_extraction_loader import (...)
#   except ImportError:
#       from entity_extraction_loader import (...)
# TO:
#   from extraction.loader import (...)

# Step 3: Update extraction/regex_extractor.py (lines 27-46)
# FROM: try/except dual path
# TO:   from extraction.loader import (...)
```

### Target 2: `regex_production_data.py` → `extraction/data/patterns.py`

**Import Chain (uses try/except dual-path):**
| File | Lines | Current Import |
|------|-------|----------------|
| `extraction/loader.py` (after move) | 52, 65 | `from api.regex_production_data import (...)` with fallback |
| `extraction/regex_extractor.py` | 26, 37 | `from api.regex_production_data import (...)` with fallback |

**Execution (Sub-Agent 5):**
```python
# Step 1: Create directory and move file
mkdir -p apps/api/extraction/data
mv apps/api/regex_production_data.py apps/api/extraction/data/patterns.py
touch apps/api/extraction/data/__init__.py

# Step 2: Update extraction/loader.py (lines 52-78)
# FROM: try/except dual path to api.regex_production_data
# TO:   from extraction.data.patterns import (...)

# Step 3: Update extraction/regex_extractor.py (lines 26-46)
# FROM: try/except dual path
# TO:   from extraction.data.patterns import (...)
```

**Verification:**
```bash
cd apps/api
python -c "from extraction.loader import get_equipment_gazetteer; print('loader OK')"
python -c "from extraction.data.patterns import DIAGNOSTIC_PATTERNS; print('patterns OK')"
python -c "from extraction.entity_extractor import get_extractor; print('extractor OK')"
```

**Commit:**
```bash
git add -A && git commit -m "refactor: move extraction files to correct locations

- entity_extraction_loader.py → extraction/loader.py
- regex_production_data.py → extraction/data/patterns.py
- Removed try/except dual-path imports (now single canonical path)
- Updated 4 import sites

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Sub-Agent Execution Strategy

### Parallel Execution Groups

**Group A (can run in parallel):**
- Sub-Agent 1: Rename `rate_limit.py` → `search_rate_limiter.py`
- Sub-Agent 2: Rename `rate_limiter.py` → `graph_api_rate_limiter.py`

**Group B (sequential, depends on Group A completion):**
- Sub-Agent 3: Delete `email_rag/entity_extractor.py` (add adapter first)

**Group C (sequential, depends on Group B completion):**
- Sub-Agent 4: Move `entity_extraction_loader.py` → `extraction/loader.py`
- Sub-Agent 5: Move `regex_production_data.py` → `extraction/data/patterns.py`

### Agent Instructions Template

Each sub-agent receives:
1. **Protected files list** (F1/Cortex - DO NOT TOUCH)
2. **Specific file operations** (rename/move/delete)
3. **Import updates** (exact file, line number, old→new)
4. **Verification command**
5. **Rollback instruction**

---

## Pre-Flight Checklist

```bash
# 1. Ensure clean working directory
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git status  # Should be clean

# 2. Create backup branch
git checkout -b backup/pre-structural-cleanup-$(date +%Y%m%d)
git checkout main

# 3. Run existing tests (baseline)
cd apps/api && pytest tests/ -v --asyncio-mode=auto

# 4. Verify F1 imports work (baseline)
python -c "from routes.f1_search_streaming import router; print('F1 OK')"
python -c "from cortex.rewrites import *; print('Cortex OK')"
```

---

## Post-Flight Verification

```bash
# 1. Run all tests
cd apps/api && pytest tests/ -v --asyncio-mode=auto

# 2. Verify F1 still works
python -c "from routes.f1_search_streaming import router; print('F1 OK')"
python -c "from cortex.rewrites import *; print('Cortex OK')"

# 3. Verify renamed imports
python -c "from services.search_rate_limiter import get_rate_limiter; print('search limiter OK')"
python -c "from services.graph_api_rate_limiter import MicrosoftRateLimiter; print('graph limiter OK')"

# 4. Verify moved files
python -c "from extraction.loader import get_equipment_gazetteer; print('loader OK')"
python -c "from extraction.data.patterns import DIAGNOSTIC_PATTERNS; print('patterns OK')"

# 5. Verify no broken imports
python -c "
import importlib
import pkgutil
import apps.api as api
for importer, modname, ispkg in pkgutil.walk_packages(api.__path__, api.__name__ + '.'):
    try:
        importlib.import_module(modname)
    except Exception as e:
        print(f'BROKEN: {modname} - {e}')
print('Import scan complete')
"
```

---

## Rollback Procedure

```bash
# If any phase fails:
git reset --hard HEAD~1  # Undo last commit

# If multiple phases fail:
git checkout backup/pre-structural-cleanup-$(date +%Y%m%d)

# Nuclear option:
git reflog  # Find commit before changes
git reset --hard <commit-sha>
```

---

## Summary

| Phase | Operation | Files | Risk | Sub-Agents |
|-------|-----------|-------|------|------------|
| 1 | DELETE | `pipeline_v1.py` | ZERO | Manual |
| 2 | RENAME | 2 rate limiters | LOW | 2 parallel |
| 3 | DELETE | `email_rag/entity_extractor.py` | LOW | 1 |
| 4 | MOVE | 2 root orphans | MEDIUM | 2 sequential |

**Total files modified:** 10 (excluding deleted)
**Total files deleted:** 2
**F1/Cortex files touched:** 0

---

## Approval Required

Before execution, confirm:
- [ ] Backup branch created
- [ ] Tests pass on current state
- [ ] F1 search verified working
- [ ] Ready to proceed with Phase 1

---

*Plan generated by Claude Opus 4.5 for Celeste OS structural cleanup.*
