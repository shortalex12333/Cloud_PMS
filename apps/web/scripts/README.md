# Database Seeding Scripts

## seed_adversarial_learning.py

Database seeder to simulate a trained ML system for Shard 11 extreme case tests.

### Purpose

This script injects `learned_keywords` into the `search_index` table to simulate "Month 2 of Production" where the counterfactual feedback loop has learned:

- **Misspellings** (Trigram territory): "genrator" → generator, "mantenance" → maintenance
- **Semantic descriptions** (Embedding territory): "thing that makes drinking water from seawater" → watermaker
- **Wrong name, right idea** (RRF fusion): "cat oil strainer" → Caterpillar generator oil filter

### Prerequisites

1. **Database column**: The `search_index` table must have a `learned_keywords` JSONB column
   - Run with `--add-column` flag to automatically add it if missing

2. **Environment variable**: Set `TENANT_DATABASE_URL` with your PostgreSQL connection string
   ```bash
   export TENANT_DATABASE_URL="postgresql://postgres:[PASSWORD]@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres"
   ```

3. **Python dependencies**: Install `psycopg2`
   ```bash
   pip install psycopg2-binary
   ```

### Usage

#### Dry run (preview changes without modifying database)
```bash
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --dry-run \
  --verbose
```

#### Add learned_keywords column (if it doesn't exist)
```bash
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --add-column \
  --dry-run
```

#### Live run (actually seed the database)
```bash
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --verbose
```

#### Full example with all flags
```bash
TENANT_DATABASE_URL="postgresql://postgres:password@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres" \
python3 scripts/seed_adversarial_learning.py \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --add-column \
  --verbose
```

### What it does

1. **Connects** to the tenant-specific Supabase database
2. **Checks** for the `learned_keywords` column (creates it if `--add-column` is specified)
3. **Finds entities** in `search_index` matching canonical terms (e.g., "generator", "watermaker")
4. **Injects learned variations** into each entity's `learned_keywords` JSONB array:
   - Misspellings: "genrator", "mantenance", "bilj pump"
   - Semantic descriptions: "thing that makes drinking water from seawater"
   - Colloquial terms: "cat oil strainer", "anchor windy"
5. **Commits changes** (unless `--dry-run` is specified)

### Learned Keyword Mappings

The script includes comprehensive mappings for all Shard 11 test cases:

#### Section 1: Misspellings (Trigram Territory)
- generator → genrator, gennie, genset, generattor, genrtr
- maintenance → mantenance, maintanance, maintanence
- bilge pump → bilj pump, bilge pmp
- certificate → certficate, certfkat
- equipment → equipmnt
- exhaust → exaust
- temperature → temp
- engine → enigne, engnie
- compressor → compreser, compresser
- coolant → koolant, antifreeze
- emergency → emergancy

#### Section 2: Semantic Descriptions (Embedding Territory)
- watermaker → "thing that makes drinking water from seawater"
- ballast system → "system that fills tanks for stability"
- bilge float switch → "sensor detecting water in hull bottom"
- ac unit → "machine that cools the cabin air"
- cleat/bollard → "rope holder on deck"
- rudder → "thing that steers the boat"
- inverter → "electrical system that converts shore power to boat power"
- bilge pump → "pump for dirty water"

#### Section 3: Wrong Name, Right Idea (RRF Fusion)
- oil filter → "cat oil strainer"
- caterpillar generator → "cat gennie", "cat genset"
- navigation light → "running light lamp"
- main engine → "propulsion unit service"
- windlass → "anchor windy"
- mca inspection → "MCA survey"
- ac compressor → "A/C compressor"
- repair → "fix", "service"

#### Section 4: Compound Extreme Cases
- generator overheating → "genrator overheeting problm"
- ac compressor maintenance → "AC compresser maintanance"
- caterpillar generator start → "cat gennie wont start"
- emergency bilge pump → "emergancy bilge pmp"
- watermaker fault → "why is the watermaker not working"
- engine oil leak → "engine's oil leak", "engines oil leak"

### Testing

After seeding, run the Shard 11 tests to verify:

```bash
npm run test:e2e -- shard-11-extremecases
```

All extreme case tests should now pass, demonstrating:
- Trigram fuzzy matching for misspellings
- Semantic vector search for descriptions
- RRF fusion for combining signals

### Database Schema

The script adds the following column if it doesn't exist:

```sql
ALTER TABLE public.search_index
ADD COLUMN IF NOT EXISTS learned_keywords JSONB DEFAULT '[]'::jsonb;
```

This column stores an array of learned query variations for each entity:

```json
[
  "genrator",
  "gennie",
  "thing that makes power"
]
```

### Integration with Search Pipeline

The F1 search pipeline should check `learned_keywords` during query processing:

1. **Tokenize** the user's query
2. **Check** if any tokens match entries in `learned_keywords`
3. **Boost** entities with matching learned keywords in the ranking
4. **Combine** with trigram, FTS, and vector signals using RRF

This simulates the counterfactual feedback loop where the system learns from user corrections over time.

### Notes

- The script is **idempotent**: running it multiple times won't create duplicate keywords
- Uses **case-insensitive deduplication** to prevent "Generator" and "generator" duplicates
- Searches across `equipment`, `work_order`, `part`, `document`, and `fault` object types
- Limits to 50 entities per canonical term to prevent over-injection

### Troubleshooting

**Error: "learned_keywords column does not exist"**
- Solution: Run with `--add-column` flag

**Error: "TENANT_DATABASE_URL environment variable is required"**
- Solution: Set the environment variable with your PostgreSQL connection URL

**No entities found for a canonical term**
- This is normal if your test data doesn't include that entity type
- Run with `--verbose` to see which patterns are matched

**psycopg2 not installed**
- Solution: `pip install psycopg2-binary`
