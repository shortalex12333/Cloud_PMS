# Shopping List Entity Extraction Fixes - Patch Application Guide

**Scope**: 🛒 Shopping List Lens

## Overview

This directory contains patches for fixing the async entity extraction pipeline, **specifically addressing shopping list query failures**.

**Shopping List Impact**:
- ✅ Fixes `shopping_list_term` extraction ("pending shopping list items")
- ✅ Fixes `approval_status` extraction ("approved", "pending")
- ✅ Enables shopping list lens functionality

**Broader Impact**:
- ✅ Resolves 4 failing tests including shopping list test
- ✅ Improves fast path usage by ~50%
- ✅ Fixes equipment entity extraction

## Patches Included

1. **01_coverage_controller_conflict_detection.patch** - Smart conflict detection (enables fast path)
2. **02_entity_type_weights.patch** - **Add shopping_list_term and approval_status weights** ⭐
3. **03_ai_source_multiplier.patch** - Increase AI reliability multiplier
4. **04_test_assertion.patch** - Fix test assertion expectations

## Application Methods

### Method 1: Apply All Patches Automatically

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Apply all patches in order
for patch in shopping_list_patches/*.patch; do
    git apply "$patch" || echo "Failed to apply $patch"
done
```

### Method 2: Apply Individual Patches

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Most critical for shopping list: Patch 2 (entity weights)
git apply shopping_list_patches/02_entity_type_weights.patch

# Also recommended:
git apply shopping_list_patches/01_coverage_controller_conflict_detection.patch
git apply shopping_list_patches/03_ai_source_multiplier.patch
git apply shopping_list_patches/04_test_assertion.patch
```

### Method 3: Manual Application

See `PR_SHOPPING_LIST_ENTITY_EXTRACTION_FIXES.md` for detailed code changes to apply manually.

## Validation

After applying patches:

```bash
cd apps/api

# Run affected tests
python3 -m pytest tests/test_async_orchestrator.py -v

# Expected output:
# 14 passed, 1 skipped in ~1s
```

## Files Modified

- `apps/api/extraction/coverage_controller.py` (9 lines)
- `apps/api/entity_extraction_loader.py` (4 lines)
- `apps/api/extraction/extraction_config.py` (1 line)
- `apps/api/tests/test_async_orchestrator.py` (5 lines)

## Rollback

If needed, revert the patches:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Revert all patches
for patch in shopping_list_patches/*.patch; do
    git apply -R "$patch"
done
```

## Test Evidence

### Before Patches
```
FAILED test_fast_path_shopping_list       ← Shopping list broken ❌
FAILED test_fast_path_known_equipment
FAILED test_mock_ai_extraction
FAILED test_fast_path_latency

4 failures, 10 passing
```

### After Patches
```
PASSED test_fast_path_shopping_list       ← Shopping list working ✅
PASSED test_fast_path_known_equipment
PASSED test_mock_ai_extraction
PASSED test_fast_path_latency

14 passing, 1 skipped
```

### Shopping List Query Validation
```python
# Before: "pending shopping list items" → entities: {}
# After:  "pending shopping list items" → entities: {
#   'shopping_list_term': ['shopping list items']
# }
```

## Questions?

See detailed documentation in:
- `SHOPPING_LIST_ENTITY_EXTRACTION_PR_SUMMARY.md` - Quick summary
- `PR_SHOPPING_LIST_ENTITY_EXTRACTION_FIXES.md` - Full PR scope and rationale
- `ASYNC_ORCHESTRATOR_FIXES.md` - Detailed technical analysis
- `COMPREHENSIVE_TEST_VALIDATION_REPORT.md` - Full test results

---

**Created**: 2026-02-02
**Status**: Ready for Review
