# New Client Onboarding — Team Cheat Sheet

## Overview

```
SQL insert → Build DMG → Upload → Send link + 2FA → Customer installs → Agent runs
   You          You        Auto       Auto/Manual         Customer        Auto
```

---

## Step 1: Create Client Record

**Where:** Master Supabase SQL Editor — https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/sql

**File:** `docs/NEW_BUYER/new_client.sql`

Edit the 5 marked values:
1. Yacht name (e.g. `M/Y Horizon`)
2. Model (e.g. `Benetti Oasis 40M`)
3. Buyer name (captain or owner)
4. Buyer email (**must be valid** — this is where 2FA codes go)
5. Tenant Supabase URL (always `https://vzsohavtuotocgrfkfyd.supabase.co`)

Run it. **Save these from the output:**
- `yacht_id` (UUID)
- `yacht_id_hash` (SHA-256)
- `2FA code` (6-digit)

---

## Step 2: Build the DMG

### Option A: GitHub Actions (recommended)

1. Go to: **GitHub → celesteos-agent → Actions → "Build DMG"**
2. Click **"Run workflow"**
3. Paste the `yacht_id` from Step 1
4. Click **Run**

Build takes ~5 minutes. When done:
- DMG is auto-uploaded to Supabase Storage
- DMG is available as a GitHub artifact (download from the run page)
- Build summary shows SHA-256 hash

**One-time setup:** Add these as GitHub repo secrets (Settings → Secrets → Actions):
- `MASTER_SUPABASE_SERVICE_KEY` — master Supabase service role key
- `TENANT_SUPABASE_SERVICE_KEY` — tenant Supabase service role key

### Option B: Local build (your Mac only)

```bash
cd ~/Documents/celesteos-agent/installer/build

export SUPABASE_SERVICE_KEY='<master supabase service role key>'
export TENANT_SUPABASE_SERVICE_KEY='<tenant supabase service role key>'

python3 build_dmg.py <yacht_id>
```

### What the build does

1. Fetches yacht metadata from fleet_registry (name, email)
2. Generates `install_manifest.json` with yacht_id + service key baked in
3. Bundles Python agent via PyInstaller (~32-37MB)
4. Embeds manifest in `CelesteOS.app/Contents/Resources/` (read-only)
5. Creates `CelesteOS-<yacht_id>.dmg` via `hdiutil`
6. Uploads DMG to Supabase Storage at `dmg/<yacht_id>/`
7. Updates `fleet_registry.dmg_storage_path` + `dmg_sha256`

**Important:** The DMG is macOS-only. The agent uses macOS Keychain, launchd, menu bar (rumps), and native window APIs. Windows/Linux would require a separate agent build.

---

## Step 3: Send to Customer

**Two things the customer needs:**
1. The DMG download link
2. The 2FA activation code

### Option A: Email delivery (production — Azure configured)

When the customer opens the DMG and clicks "Begin Registration", the registration API automatically:
- Sends a branded email to `buyer_email` with a fresh 6-digit 2FA code
- Email comes from `noreply@celeste7.ai` via Microsoft Graph API

**Requires Azure env vars on the registration API:**
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_SENDER_EMAIL=noreply@celeste7.ai`

### Option B: Manual delivery (current state — Azure not configured)

Send the customer:
1. **DMG file** — either via direct file transfer, or via the download portal
2. **2FA code** — the one from Step 1 output (e.g. via WhatsApp, separate email)

### Download Portal (optional)

If you want the customer to self-serve the download:
1. Customer visits `https://registration.celeste7.ai` (or `localhost:8001` locally)
2. Enters their email → receives a download verification code
3. Enters code → gets a signed download URL (1 hour expiry, max 3 downloads)

This is a **separate flow** from the installation 2FA. The download portal has its own 2FA for the download, then the installer has another 2FA for activation.

---

## Step 4: Customer Installs

**What the customer does (no tech knowledge needed):**

1. Open the DMG → drag CelesteOS to Applications
2. Launch CelesteOS → installer wizard opens
3. **Step 1 — Welcome:** Shows yacht name, click "Begin Registration"
4. **Step 2 — 2FA:** Enter the 6-digit code (from email or manual delivery)
5. **Step 3 — NAS Folder:** Select the yacht's document folder on the NAS
6. **Step 4 — Done:** Confirmation screen, daemon starts automatically

**What happens behind the scenes:**
- Installer calls `POST /api/register` → triggers 2FA email (or uses pre-seeded code)
- Installer calls `POST /api/verify-2fa` → receives `shared_secret` (one-time)
- `shared_secret` stored in macOS Keychain + encrypted recovery file
- `~/.celesteos/.env.local` written with tenant credentials
- Launchd plist installed → auto-starts on boot

---

## Step 5: Verify Activation

**Check in master Supabase:**

```sql
SELECT yacht_id, yacht_name, active, activated_at, last_seen_at
FROM fleet_registry
WHERE yacht_id = '<yacht_id>';
```

Should show `active = true` and `activated_at` populated.

**Check agent is running (on customer's Mac):**
- Tray icon in menu bar (green dot = idle, blue arrow = syncing)
- Click tray → "Open Status Window" shows file counts

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Yacht not found" in installer | fleet_registry row missing | Re-run Step 1 SQL |
| "Invalid yacht identity" | yacht_id_hash mismatch | DMG was built for a different yacht_id |
| "Invalid code" | Wrong 2FA code or expired | Check installation_2fa_codes table; re-seed if needed |
| "Too many attempts" | 5+ wrong code entries | Insert a new 2FA code row in DB |
| DMG build fails "TENANT_SUPABASE_SERVICE_KEY required" | Env var not set | `export TENANT_SUPABASE_SERVICE_KEY='...'` |
| Agent won't sync | NAS not mounted or .env.local wrong | Check `~/.celesteos/.env.local`, check NAS path |
| No email received | Azure creds not configured | Use manual 2FA delivery (Option B) |
| "Failed to send verification email" | Azure token expired or wrong creds | Check AZURE_* env vars on registration API |

---

## Quick Reference

| Item | Value |
|------|-------|
| Master Supabase | `qvzmkaamzaqxpzbewjxe` |
| Tenant Supabase | `vzsohavtuotocgrfkfyd` (shared, multi-tenant) |
| Registration API | `registration.celeste7.ai` (prod) / `localhost:8001` (local) |
| SQL template | `docs/NEW_BUYER/new_client.sql` |
| Build script | `celesteos-agent/installer/build/build_dmg.py` |
| Agent source | `~/Documents/celesteos-agent/` |
| Registration source | `~/Documents/celesteos-registration/` |
