---
phase: B-deploy-clean-codebase
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements:
  - DEPLOY-01
  - DEPLOY-02
  - DEPLOY-03
  - DEPLOY-04

must_haves:
  truths:
    - "Local branch merged to main"
    - "CI/CD pipeline passes (build, lint, type check)"
    - "Production deployment completes"
    - "Health check confirms services responding"
  artifacts: []
  key_links: []
---

<objective>
Deploy the clean local codebase (18+ commits including AbortError fix) to production.

Purpose: Push the overhauled codebase to production so post-deploy validation can measure search improvements.

The local branch `styling/complete-chatgpt-spec` is 18+ commits ahead of main with:
- AbortError fix at useCelesteSearch.ts:534-548
- Code cleanup (54% reduction)
- Search pipeline improvements
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Check current branch status</name>
  <files></files>
  <action>
Check git status and branch position:
```bash
git status
git log --oneline -5
git rev-list --count origin/main..HEAD 2>/dev/null || echo "No remote tracking"
```

Verify:
- Working tree is clean (no uncommitted changes)
- Current branch has commits ahead of main
  </action>
  <verify>
- `git status` shows clean working tree
- Commits exist ahead of origin/main
  </verify>
  <done>
- Working tree is clean
- Branch position confirmed
  </done>
</task>

<task type="auto">
  <name>Task 2: Push to main and trigger CI/CD</name>
  <files></files>
  <action>
Push the current branch to main:

Option A - Direct push (if allowed):
```bash
git push origin HEAD:main
```

Option B - Create PR (if branch protection):
```bash
gh pr create --base main --title "Deploy: Search pipeline hardening + code cleanup" --body "18+ commits including AbortError fix"
gh pr merge --merge --auto
```

Monitor CI/CD:
```bash
gh run list --limit 5
```
  </action>
  <verify>
- Push succeeded OR PR created
- CI/CD pipeline started
  </verify>
  <done>
- Code pushed to main
- CI/CD initiated
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify deployment health</name>
  <files></files>
  <action>
Wait for deployment and verify health:

1. Check Vercel deployment status (frontend):
```bash
vercel ls --prod 2>/dev/null || echo "Vercel CLI not configured"
```

2. Check API health:
```bash
curl -s https://pipeline-core.int.celeste7.ai/health | head -100
```

3. Verify search endpoint responds:
```bash
curl -s -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test","query_type":"free-text","limit":3,"auth":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"}}' | head -200
```
  </action>
  <verify>
- Health endpoint returns OK
- Search endpoint responds without error
  </verify>
  <done>
- Production services healthy
- Search endpoint operational
  </done>
</task>

</tasks>

<verification>
1. Git shows main is updated with local commits
2. CI/CD passed (check gh run view)
3. Production health check returns OK
4. Search endpoint responds to test query
</verification>

<success_criteria>
- Local branch merged to main
- CI/CD pipeline passes
- Production deployment completes
- Services responding to health checks
</success_criteria>

<output>
After completion, create `.planning/phases/B-deploy-clean-codebase/B-01-SUMMARY.md`
</output>
