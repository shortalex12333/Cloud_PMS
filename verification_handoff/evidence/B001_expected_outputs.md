# B001 Deploy Gate Expected Outputs

**Blocker:** B001 - Pipeline JWT Signature Mismatch
**Fix Commit:** 57ce457
**Date:** 2026-01-19

---

## Pre-Deploy Output (BEFORE fix)

```json
{"detail":"Invalid token: Signature verification failed"}
```

**HTTP Status:** 401 Unauthorized

This error indicates:
- Supabase signs JWTs with tenant project JWT secret
- Render was looking for `MASTER_SUPABASE_JWT_SECRET` or `SUPABASE_JWT_SECRET`
- Render env vars had `TENANT_SUPABASE_JWT_SECRET` set instead
- Code didn't recognize `TENANT_SUPABASE_JWT_SECRET` env var name

---

## Post-Deploy Output (AFTER fix)

```json
{
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "yacht_name": "M/Y Test Vessel",
  "tenant_key_alias": "y85fe1119-b04c-41ac-80f1-829d23322598",
  "role": "captain",
  "status": "ACTIVE",
  "user_id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "email": "x@alex-short.com"
}
```

**HTTP Status:** 200 OK

This response confirms:
- JWT signature verification passed
- User lookup from MASTER DB succeeded
- Yacht context resolved correctly
- All fields populated with expected values

---

## Verification Checklist

### Before Deploy
- [ ] Run `B001_predeploy_curl.sh`
- [ ] Confirm output shows "Signature verification failed"
- [ ] Save output to `B001_predeploy_evidence.json`

### During Deploy
- [ ] Verify commit 57ce457 is being deployed
- [ ] Check Render logs for deployment success
- [ ] Wait for health check to pass

### After Deploy
- [ ] Run `B001_postdeploy_curl.sh`
- [ ] Confirm output shows yacht_id and user_id
- [ ] Save output to `B001_postdeploy_evidence.json`
- [ ] Mark B001 as RESOLVED in 03_KNOWN_BLOCKERS.md

---

## Troubleshooting

### If still failing after deploy:

1. **Verify deployment:**
   ```bash
   curl -s https://pipeline-core.int.celeste7.ai/health
   ```
   Should show `"status": "healthy"`

2. **Check Render env vars:**
   - Go to Render Dashboard → celeste-pipeline-v1 → Environment
   - Verify `TENANT_SUPABASE_JWT_SECRET` is set
   - Value should be: `ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==`

3. **Force redeploy:**
   - Click "Manual Deploy" in Render Dashboard
   - Or push a trivial commit to trigger auto-deploy

4. **Check logs:**
   - Render Dashboard → Logs
   - Look for `[Auth] TENANT_SUPABASE_JWT_SECRET loaded`

---

## Files in This Pack

- `B001_predeploy_curl.sh` - Script to verify error before fix
- `B001_postdeploy_curl.sh` - Script to verify fix works
- `B001_expected_outputs.md` - This file

