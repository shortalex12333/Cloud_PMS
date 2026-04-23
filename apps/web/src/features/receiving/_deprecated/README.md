# Deprecated receiving code

These files were the data layer for an older `ReceivingDetail` component that
queried Supabase directly via `lib/supabaseClient.ts`. That client points at
the **MASTER** Supabase (auth-only) — the receiving tables live in **TENANT**
Supabase, so every detail-card open returned 404.

The fix (PR for `fix(receiving): wire detail view to tenant DB`) replaced
`ReceivingDetail` with `EntityLensPage + ReceivingContent`, which routes
through the Render backend (`/v1/entity/receiving/{id}`) using the tenant
client. That removed every external caller of these files.

## What was used by what

| File | Last caller | Notes |
|------|-------------|-------|
| `api.ts` (`fetchReceivingItem`) | `app/receiving/page.tsx::ReceivingDetail` | Removed in receiving wire-fix |
| `api.ts` (`fetchReceivingItems`) | none on record | Never wired to a list view |
| `api.ts` (`fetchReceivingAttachments`) | `ReceivingPhotos.tsx` only | Both deprecated together |
| `ReceivingPhotos.tsx` | `app/receiving/page.tsx::ReceivingDetail` | Removed in receiving wire-fix |

## Why kept (not deleted)

Default policy: **protect production over cleaning the repo.** Quarantining
keeps these importable at a different path if a regression surfaces, and
keeps the code visible without noise in the active feature folder.

## When to delete

Delete after one stable release (≥ 14 days on production with the new lens
pattern and zero `404 receiving` reports). At that point: `git rm -r _deprecated/`.
