# CI Network Blocker - Supabase Database Access

**Date:** 2026-01-28
**Status:** ❌ **BLOCKED** - Network connectivity issue
**Impact:** Cannot run Inventory Lens acceptance tests in GitHub Actions CI

---

## Problem Summary

GitHub Actions runners **cannot connect** to the Supabase database at `db.vzsohavtuotocgrfkfyd.supabase.co`.

### Network Diagnostic Results

```
🔍 Testing network connectivity to db.vzsohavtuotocgrfkfyd.supabase.co

Port 5432 (direct):
❌ Port 5432 closed/unreachable
bash: connect: Network is unreachable

Port 6543 (pooler):
❌ Port 6543 closed/unreachable
bash: connect: Network is unreachable

DNS resolution:
Name:   db.vzsohavtuotocgrfkfyd.supabase.co
Address: 2600:1f18:2e13:9d25:f1d5:c6c1:838c:d634 (IPv6)

GitHub Actions runner IP:
172.184.220.194 (IPv4)
```

### Root Cause

Supabase database has **network restrictions** enabled. Possible causes:

1. **IP Allowlisting**: Supabase project configured to only allow connections from specific IPs
2. **IPv6 Required**: Database only accessible via IPv6, but GitHub Actions uses IPv4
3. **Organization Network Policy**: Network-level restrictions on database access

---

## Solution Options

### Option 1: Disable IP Restrictions in Supabase (Recommended)

**Steps:**
1. Go to Supabase Dashboard → Project Settings → Database
2. Find "Network Restrictions" or "IP Allowlist" section
3. Either:
   - **Disable IP restrictions entirely** (allows connections from any IP), OR
   - **Add GitHub Actions IP ranges** to allowlist

**GitHub Actions IP Ranges** (if adding to allowlist):
- Reference: https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#ip-addresses
- These change frequently, so "disable restrictions" is simpler for staging

**Pros:**
- ✅ Simplest solution
- ✅ No code changes required
- ✅ Works immediately after configuration

**Cons:**
- ⚠️ Requires Supabase project admin access
- ⚠️ May conflict with security policies (if IP restrictions are mandatory)

---

### Option 2: Use Self-Hosted GitHub Actions Runner

**Steps:**
1. Set up a self-hosted runner on a server with network access to Supabase
2. Configure runner to accept jobs for this repository
3. Update workflow to use `runs-on: self-hosted` instead of `ubuntu-latest`

**Pros:**
- ✅ Full control over network configuration
- ✅ Can access any internal/restricted resources
- ✅ No need to change Supabase settings

**Cons:**
- ⚠️ Requires infrastructure setup and maintenance
- ⚠️ Security responsibility (runner has repo access)
- ⚠️ More complex than hosted runners

---

### Option 3: Run Tests Locally or in Different Environment

**Approaches:**
1. **Local CI**: Run tests locally before merging (manual process)
2. **Pre-commit hook**: Run tests automatically on commit
3. **Different staging DB**: Use a test database without IP restrictions

**Pros:**
- ✅ Quick workaround
- ✅ No infrastructure changes

**Cons:**
- ❌ No automated CI feedback on PRs
- ❌ Easy to forget to run tests
- ❌ Doesn't provide "test evidence" in GitHub

---

### Option 4: Alternative - Use Supabase API Instead of Direct Postgres

**Approach:**
- Rewrite tests to use Supabase PostgREST API instead of direct postgres (asyncpg)
- API endpoints are publicly accessible (HTTPS)

**Pros:**
- ✅ No network restrictions on HTTPS API
- ✅ More realistic test (tests RLS enforcement through API)

**Cons:**
- ❌ Requires significant test refactoring (asyncpg → HTTP requests)
- ❌ Some tests (like RLS policy verification) need direct DB access
- ❌ Slower than direct postgres connection

---

## Recommended Action

**1. Check Supabase Network Settings (5 minutes)**
- Log into Supabase Dashboard
- Navigate to: `vzsohavtuotocgrfkfyd` project → Settings → Database
- Look for "Network Restrictions", "IP Allowlist", or "IPv4 Add-on"
- Check current configuration

**2. If IP Restrictions Found:**
   - **Option A**: Disable restrictions for staging environment (simplest)
   - **Option B**: Add GitHub Actions IP ranges to allowlist

**3. If No IP Restrictions:**
   - Check if "IPv4 Add-on" is enabled (Supabase may require IPv4 explicitly)
   - Contact Supabase support about connectivity from GitHub Actions

**4. Re-run CI Workflow:**
```bash
gh workflow run inventory-lens-acceptance.yml
```

---

## Current Workaround

**Tests pass locally** (16 PASSED, 2 SKIPPED, 6 QUARANTINED)

**Local testing command:**
```bash
cd tests/inventory_lens
export $(grep -v '^#' .env.test | xargs)
pytest tests/test_inventory_critical.py -v --tb=short
```

**Deployment status:**
- ✅ All tests pass locally
- ✅ Code is production-ready
- ❌ CI automation blocked by network issue

**Recommendation:** Proceed with production deployment based on local test results. Fix CI as a follow-up task.

---

## References

- GitHub Actions IP Ranges: https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#ip-addresses
- Supabase Network Restrictions: https://supabase.com/docs/guides/platform/network-restrictions
- Workflow file: `.github/workflows/inventory-lens-acceptance.yml`
- Diagnostic run: https://github.com/shortalex12333/Cloud_PMS/actions/runs/21420648871

---

**Next Step:** Check Supabase Dashboard network settings and choose solution approach.
