# Pull Request Strategy - Part Lens Integration

**Current Situation**: Multiple feature branches, Part Lens code in `feature/document-comments-mvp`

---

## Option 1: Create Dedicated Part Lens PR (RECOMMENDED)

**Best for**: Clean isolation, easy review, fast merge

### Steps:

```bash
# 1. Create clean Part Lens branch from main
git checkout main
git pull origin main
git checkout -b feature/part-lens-integration

# 2. Cherry-pick just the Part Lens commit
git cherry-pick da0dc0f  # "feat: Add Part Lens with microaction integration"

# 3. Push to new branch
git push -u origin feature/part-lens-integration

# 4. Create PR on GitHub
# Title: "feat: Add Part Lens with microaction integration"
# From: feature/part-lens-integration
# To: main
# Description: See PART_LENS_INTEGRATION_COMPLETE.md
```

**Pros**:
- ✅ Single focused PR (Part Lens only)
- ✅ Easy to review (~500 lines, 9 files)
- ✅ Fast approval/merge
- ✅ No conflicts with other features
- ✅ Clear commit history

**Cons**:
- Need to create new branch

---

## Option 2: Use Existing feature/document-comments-mvp

**Best for**: If you want all those changes together

### Steps:

```bash
# Already done - branch is pushed
# Just create PR on GitHub:
# From: feature/document-comments-mvp
# To: main
```

**Pros**:
- ✅ Already pushed
- ✅ All work in one PR

**Cons**:
- ✗ PR includes 14 commits (Part Lens + other work)
- ✗ Harder to review (mixed concerns)
- ✗ May require more approvals
- ✗ Riskier merge

---

## Option 3: Rebase/Squash on Main

**Best for**: Clean up multiple small commits

### Steps:

```bash
# 1. Create new branch from main
git checkout main
git checkout -b feature/part-lens-clean

# 2. Cherry-pick and squash
git cherry-pick da0dc0f
# Or manually copy files from feature/document-comments-mvp

# 3. Push
git push -u origin feature/part-lens-clean
```

---

## Recommendation: Option 1 (Dedicated PR)

**Why**: Part Lens is:
- Self-contained (9 files, no modifications to existing code except graphrag_query.py)
- Well-tested (all tests passing)
- Production-ready
- High-value feature (enables microaction buttons)

**Action Plan**:

1. **Create clean Part Lens PR** (Option 1 above)
2. **Merge Part Lens first** (fastest path to production)
3. **Handle other branches separately**:
   - Review existing feature branches
   - Close stale branches
   - Create individual PRs for active work
   - Keep PRs small and focused

---

## Managing Other Branches

### Current Feature Branches:
```
feature/document-comments-mvp       ← Part Lens is here (mixed with other work)
feature/email-ui-phase6
feature/equipment-lens-v2-handlers
feature/inventory-lens-v1.2-fixes
feature/inventory-lens-v1.2-signoff
feature/p1-show-related-v1
feature/part-lens-microactions      ← Old Part Lens branch?
feature/phase7-outlook-refresh
feature/receiving-lens-e2e-performance
feature/receiving-lens-v1-hardening
feature/situational-continuity-mvp
feature/work-order-lens-p1-related-notifications
```

### Cleanup Strategy:

1. **Audit each branch**:
   ```bash
   git checkout <branch>
   git log --oneline main..<branch>  # See what's different
   ```

2. **Categorize**:
   - **Active**: Create PR
   - **Merged**: Delete branch
   - **Obsolete**: Delete branch
   - **Needs work**: Park for later

3. **Delete merged/obsolete branches**:
   ```bash
   git branch -d feature/branch-name
   git push origin --delete feature/branch-name
   ```

---

## Immediate Next Steps

### For Part Lens (NOW):

```bash
# Option 1: Create dedicated PR
git checkout main
git checkout -b feature/part-lens-integration
git cherry-pick da0dc0f
git push -u origin feature/part-lens-integration

# Then on GitHub:
# 1. Create PR: feature/part-lens-integration → main
# 2. Add label: "Security Reviewer Required"
# 3. Add description from PART_LENS_INTEGRATION_COMPLETE.md
# 4. Request review
```

### For Other Work (LATER):

1. Review `feature/document-comments-mvp` - what else is in there?
2. Audit other feature branches - still relevant?
3. Create individual PRs for active work
4. Delete stale branches

---

## PR Best Practices Going Forward

1. **One feature per branch**
   - ✅ feature/part-lens-integration
   - ✗ feature/everything-i-worked-on-today

2. **Small, focused PRs**
   - Target: < 500 lines changed
   - Single concern
   - Easy to review

3. **Clear naming**
   - feature/specific-feature-name
   - fix/specific-bug-description

4. **Regular cleanup**
   - Delete merged branches
   - Archive obsolete work
   - Keep < 5 active feature branches

---

## Summary

**Recommended**: Create clean `feature/part-lens-integration` branch with just Part Lens commit

**Why**: Fast review, clean history, high-value feature, ready for production

**Then**: Audit and clean up other feature branches separately
