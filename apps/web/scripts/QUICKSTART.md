# Quick Start: Seed Adversarial Learning Data

This guide will help you seed the database for Shard 11 extreme case tests in 3 steps.

## Step 1: Get Your Database Connection URL

### Option A: From Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to **Project Settings** > **Database**
3. Copy the **Connection string** under "Connection string"
4. Replace `[YOUR-PASSWORD]` with your actual database password

Example:
```
postgresql://postgres:your_password@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres
```

### Option B: Construct from .env.local

If you have `NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co`:

```bash
# Extract project ID (vzsohavtuotocgrfkfyd)
# Construct URL:
postgresql://postgres:[YOUR_PASSWORD]@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres
```

## Step 2: Export Database URL

```bash
export TENANT_DATABASE_URL="postgresql://postgres:your_password@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres"
```

Or create a `.env` file:

```bash
# .env
TENANT_DATABASE_URL=postgresql://postgres:your_password@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres
```

Then load it:
```bash
source .env
```

## Step 3: Run the Seeder

### First time: Add column and seed (dry run to preview)
```bash
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --add-column \
  --dry-run \
  --verbose
```

### If dry run looks good, run for real:
```bash
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --add-column \
  --verbose
```

### Subsequent runs (column already exists):
```bash
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --verbose
```

## Step 4: Verify with Tests

Run the Shard 11 tests to verify the seeding worked:

```bash
npm run test:e2e -- shard-11-extremecases
```

## Expected Output

```
================================================================================
ADVERSARIAL LEARNING SEEDER - SHARD 11 EXTREME CASES
================================================================================
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
Mode: LIVE UPDATE

Searching for entities matching: 'generator'
  → Found equipment: Main Generator (ID: ...)
  ✅ Injected 5 keywords into 1 entities

Searching for entities matching: 'watermaker'
  → Found equipment: Watermaker System (ID: ...)
  ✅ Injected 6 keywords into 1 entities

...

================================================================================
SUMMARY
================================================================================
Patterns matched:     45
Entities processed:   127
Keywords injected:    523

✅ Seeding complete! Shard 11 tests should now pass.
   The search index now simulates 'Month 2 of Production'
   with learned misspellings, semantic descriptions, and colloquial terms.
```

## Troubleshooting

### "psycopg2 not installed"
```bash
pip install psycopg2-binary
```

### "TENANT_DATABASE_URL environment variable is required"
Make sure you exported the variable (see Step 2)

### "learned_keywords column does not exist"
Add the `--add-column` flag

### "No entities found for <term>"
This is normal if your test data doesn't include that entity type. The script will skip it and continue.

### Permission denied
Make sure the script is executable:
```bash
chmod +x scripts/seed_adversarial_learning.py
```

## One-Liner (for convenience)

```bash
TENANT_DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT_ID.supabase.co:5432/postgres" \
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --add-column \
  --verbose
```

Replace `PASSWORD` and `PROJECT_ID` with your values.

## What This Does

This script simulates a trained ML system by injecting learned query variations into the `search_index` table:

| Query Type | Example User Query | Canonical Entity | How It Works |
|------------|-------------------|------------------|--------------|
| Misspelling | "genrator" | Generator | Trigram similarity (pg_trgm) |
| Semantic | "thing that makes drinking water from seawater" | Watermaker | Vector embedding (pgvector) |
| Wrong name, right idea | "cat oil strainer" | Generator oil filter | RRF fusion (K=60) |

After seeding, your search will handle these extreme cases as if the system has been learning from user feedback for months.
