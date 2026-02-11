# Day 3: Image Operations Perfection

**Date:** 2026-02-10
**Status:** STARTING NOW ⏳

---

## Goal

**100% success rate on ALL image operations**

Test image upload/update/delete exhaustively:
- Various sizes (1KB to 10MB)
- Various formats (PNG, JPEG, WebP, HEIC)
- Edge cases (duplicate uploads, missing files, corrupted data)
- Concurrent uploads (10+ simultaneous)
- Performance under load

---

## Known Issues from Day 1

### Issue: Database Trigger Constraint
**Symptom:** HTTP 500 "duplicate key value violates unique constraint 'ix_spq_source_object'"

**Context:**
- Occurs when uploading image to part that already has an image
- Database trigger tries INSERT instead of UPSERT
- Workaround: Use parts without images

**Root Cause:** Trigger logic in database needs to handle existing records

**Expected Location:** Database migrations or trigger definitions

---

## Hours 1-4: Exhaustive Image Testing

### Test Matrix:

**Endpoints:**
- [ ] POST /v1/parts/upload-image
- [ ] POST /v1/parts/update-image
- [ ] POST /v1/parts/delete-image

**Test Cases per Endpoint:**

1. **Size Variants:**
   - [ ] 1KB image (minimum)
   - [ ] 100KB image (typical)
   - [ ] 1MB image (large)
   - [ ] 5MB image (very large)
   - [ ] 10MB image (maximum)
   - [ ] 11MB image (over limit - should reject)

2. **Format Variants:**
   - [ ] PNG (lossless)
   - [ ] JPEG (lossy)
   - [ ] WebP (modern)
   - [ ] HEIC (iOS)
   - [ ] GIF (animated - should reject?)
   - [ ] SVG (vector - should reject?)
   - [ ] Invalid format (should reject)

3. **Edge Cases:**
   - [ ] Empty file
   - [ ] Corrupted image data
   - [ ] Missing required fields
   - [ ] Invalid part_id
   - [ ] Part from different yacht (RBAC violation)
   - [ ] No authentication
   - [ ] Invalid JWT

4. **Concurrent Operations:**
   - [ ] 10 simultaneous uploads to different parts
   - [ ] 10 simultaneous uploads to same part
   - [ ] Upload + Update + Delete in parallel

5. **State Transitions:**
   - [ ] Upload → Upload (duplicate)
   - [ ] Upload → Update → Delete → Upload (lifecycle)
   - [ ] Update without prior Upload (should fail?)
   - [ ] Delete without prior Upload (should fail?)

---

## Hours 5-8: Fixes

### Expected Fixes:

1. **Database Trigger Fix:**
   - Location: Database migration or trigger definition
   - Change: INSERT → UPSERT (ON CONFLICT DO UPDATE)
   - Test: Upload twice to same part → both succeed

2. **File Size Validation:**
   - Add max size check (10MB)
   - Return 400 with clear error message
   - Test: Upload 11MB image → 400 "File too large"

3. **Format Validation:**
   - Validate MIME type
   - Reject unsupported formats
   - Test: Upload SVG → 400 "Unsupported format"

4. **RBAC Enforcement:**
   - Verify yacht isolation
   - Test: Upload image for part in different yacht → 403

---

## Success Criteria

- [ ] 100% success rate on valid inputs
- [ ] All edge cases handled gracefully (400/403, not 500)
- [ ] Zero 500 errors on any input
- [ ] Concurrent uploads work correctly
- [ ] Database trigger constraint fixed
- [ ] All endpoints documented
- [ ] Test coverage >90%

---

**Starting:** Now
**Target Completion:** 8 hours
