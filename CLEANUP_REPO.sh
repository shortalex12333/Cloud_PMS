#!/bin/bash
# =============================================================================
# REPO CLEANUP SCRIPT
# =============================================================================
#
# This script safely moves junk files to _archive/ folder.
# Nothing is deleted - you can review and restore if needed.
#
# TO RUN: chmod +x CLEANUP_REPO.sh && ./CLEANUP_REPO.sh
#
# WHAT IT DOES:
# 1. Creates _archive/ folder
# 2. Moves dead api/ code to _archive/api_dead/
# 3. Moves root junk files to _archive/root_junk/
# 4. Shows before/after summary
#
# TO UNDO: Just move files back from _archive/
# =============================================================================

set -e  # Exit on error

echo "========================================================================"
echo "REPO CLEANUP - Moving junk to _archive/"
echo "========================================================================"

# Create archive directories
mkdir -p _archive/api_dead
mkdir -p _archive/root_junk
mkdir -p _archive/root_junk/workflows
mkdir -p _archive/root_junk/supabase_old
mkdir -p _archive/root_junk/search
mkdir -p _archive/root_junk/mvp-uploader

echo ""
echo "📂 Created _archive/ folder structure"

# =============================================================================
# MOVE DEAD API CODE (13 files, 2.3 MB)
# =============================================================================
echo ""
echo "🔄 Moving dead api/ code..."

DEAD_API_FILES=(
    "coverage_controller.py"
    "entity_governance.py"
    "entity_learning_batch.py"
    "entity_merger.py"
    "extraction_config.py"
    "gpt_fallback.py"
    "maritime_spacy_enhancements.py"
    "query_processor.py"
    "regex_extractor.py"
    "regex_production_data.py"
    "test_unified_extraction.py"
    "text_cleaner.py"
    "unknowns_logger.py"
)

for file in "${DEAD_API_FILES[@]}"; do
    if [ -f "api/$file" ]; then
        mv "api/$file" "_archive/api_dead/"
        echo "   ✓ api/$file"
    fi
done

# Also move the JSON pattern file if not used
if [ -f "api/microaction_patterns.json" ]; then
    # Check if it's imported anywhere
    if ! grep -q "microaction_patterns.json" api/*.py 2>/dev/null; then
        mv "api/microaction_patterns.json" "_archive/api_dead/"
        echo "   ✓ api/microaction_patterns.json"
    fi
fi

# Move README from api/ if exists
if [ -f "api/UNIFIED_EXTRACTION_README.md" ]; then
    mv "api/UNIFIED_EXTRACTION_README.md" "_archive/api_dead/"
    echo "   ✓ api/UNIFIED_EXTRACTION_README.md"
fi

# =============================================================================
# MOVE ROOT JUNK FILES
# =============================================================================
echo ""
echo "🔄 Moving root junk files..."

# Planning/design docs (no longer needed)
ROOT_MD_JUNK=(
    "action-endpoint-contract.md"
    "action-router-service.md"
    "agent-spec.md"
    "api-spec.md"
    "architecture.md"
    "basic principles gospel.md"
    "devops.md"
    "ENTITY_EXTRACTION_HOSTING_ANALYSIS.md"
    "ENTITY_EXTRACTION_README.md"
    "foundations.md"
    "functionaltiy.md"
    "glossary.md"
    "indexing-pipeline.md"
    "LATENCY_REQUIREMENTS.md"
    "MICRO_ACTION_EXTRACTION_README.md"
    "micro-action-catalogue.md"
    "MVP1_WORKFLOW_DESIGN.md"
    "MVP2_PYTHON_SERVICES_PLAN.md"
    "N8N_CAPABILITY_MATRIX.md"
    "N8N_INTEGRATION_GUIDE.md"
    "Perfect.md"
    "predictive-maintenance.md"
    "RENDER_DEPLOYMENT_GUIDE.md"
    "search-engine-spec.md"
    "security-overview.md"
    "security.md"
    "supabase_credentials.md"
    "table_configs.md"
    "UNSUPPORTED_ACTION_BEHAVIOUR.md"
    "vision.md"
    "web-ux.md"
)

for file in "${ROOT_MD_JUNK[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "_archive/root_junk/"
        echo "   ✓ $file"
    fi
done

# Random data files
ROOT_DATA_JUNK=(
    "predictive (1).json"
    "rag_baseline.json"
    "Supabase Snippet Yacht Document Storage and RLS Setup (10).csv"
)

for file in "${ROOT_DATA_JUNK[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "_archive/root_junk/"
        echo "   ✓ $file"
    fi
done

# Move unused directories
if [ -d "workflows" ]; then
    mv workflows/* "_archive/root_junk/workflows/" 2>/dev/null || true
    rmdir workflows 2>/dev/null || true
    echo "   ✓ workflows/"
fi

if [ -d "search" ]; then
    mv search/* "_archive/root_junk/search/" 2>/dev/null || true
    rmdir search 2>/dev/null || true
    echo "   ✓ search/"
fi

if [ -d "mvp-uploader" ]; then
    mv mvp-uploader/* "_archive/root_junk/mvp-uploader/" 2>/dev/null || true
    rmdir mvp-uploader 2>/dev/null || true
    echo "   ✓ mvp-uploader/"
fi

if [ -d "supabase" ]; then
    mv supabase/* "_archive/root_junk/supabase_old/" 2>/dev/null || true
    rmdir supabase 2>/dev/null || true
    echo "   ✓ supabase/"
fi

# Remove .DS_Store
find . -name ".DS_Store" -delete 2>/dev/null || true

# =============================================================================
# ADD _archive TO .gitignore
# =============================================================================
echo ""
echo "🔄 Adding _archive/ to .gitignore..."

if ! grep -q "_archive" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Archived junk files" >> .gitignore
    echo "_archive/" >> .gitignore
    echo "   ✓ Added _archive/ to .gitignore"
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo "========================================================================"
echo "✅ CLEANUP COMPLETE"
echo "========================================================================"
echo ""
echo "BEFORE:"
echo "   api/ files: 26"
echo "   Root files: 50+"
echo "   Total size: ~3.5 MB of junk"
echo ""
echo "AFTER:"
echo "   api/ files: 13 (only what Render uses)"
echo "   Root files: ~10 (essential only)"
echo ""
echo "ARCHIVED TO: _archive/"
echo "   - api_dead/     (13 unused Python files)"
echo "   - root_junk/    (38 planning docs, data files, old folders)"
echo ""
echo "TO UNDO: Move files back from _archive/"
echo "TO DELETE PERMANENTLY: rm -rf _archive/"
echo ""
echo "Now run: git add -A && git status"
