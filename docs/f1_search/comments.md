
  ┌────────────────────┬─────────────────────────────────┬───────────────────────────────────────┬─────────────────────────────┐
  │        Fix         │              File               │                 What                  │           Impact            │
  ├────────────────────┼─────────────────────────────────┼───────────────────────────────────────┼─────────────────────────────┤
  │ 1. Preamble        │ cortex/rewrites.py              │ Strip "Show me the", "Find the", etc. │ HIGHEST — directly fixes L1 │
  │ stripping          │                                 │  before DB                            │  failures                   │
  ├────────────────────┼─────────────────────────────────┼───────────────────────────────────────┼─────────────────────────────┤
  │ 2. Embedding       │ f1_search_streaming.py:927-928  │ 150ms→500ms (L1), 800ms→2000ms (L2),  │ HIGH — enables vector       │
  │ budget             │                                 │ env-configurable                      │ search on local dev         │
  ├────────────────────┼─────────────────────────────────┼───────────────────────────────────────┼─────────────────────────────┤
  │ 3. try/except text │ f1_search_streaming.py:1061     │ Catch TimeoutError, continue with     │ MODERATE — prevents hard    │
  │  search            │                                 │ vector results                        │ failure                     │
  ├────────────────────┼─────────────────────────────────┼───────────────────────────────────────┼─────────────────────────────┤
  │ 4. Keyword         │ f1_search_streaming.py after    │ Use extracted entities as last resort │ MODERATE — safety net       │
  │ fallback           │ RRF                             │  when 0 results                       │                             │
  └────────────────────┴─────────────────────────────────┴───────────────────────────────────────┴─────────────────────────────

                                                                            
  ---                                                                                                                               
  1. Preamble stripping — is blacklisting words the focus?                                                                          
                                                                                                                                    
  No. And framing it as "blacklisting" reveals the weakness of this fix.
                                                                                                                                    
  The actual problem is signal-to-noise ratio at the DB layer. pg_trgm computes similarity as |intersection| / |union| of 3-grams.
  "Show me the" adds ~12 noise trigrams to the union denominator without adding any to the intersection numerator. That's not the
  words being "bad" — it's the algorithm being character-level, not semantic-level.

  But here's what I should have said in the plan: if Fix 2 (embeddings) works, Fix 1 becomes almost unnecessary. Vector similarity
  handles natural language natively. OpenAI's embedding model was trained ON full sentences — "Show me the fuel filter for the
  generator" produces a BETTER embedding than "fuel filter generator" because it captures intent. The vector signal doesn't care
  about preamble — it captures meaning.

  So the real dependency is:

  Fix 2 works (embeddings alive) → Fix 1 becomes belt-and-suspenders
  Fix 2 fails (embeddings dead) → Fix 1 is critical rescue

  Preamble stripping is a fallback for when the semantic layer (vectors) is unavailable, not the primary fix.

=======
                                                                                    
                                   
  The budget is a step function, not a bell curve. Lines 574-581 show it clearly:                                                   
                                                                                                                                    
  response = await asyncio.wait_for(                                                                                                
      client.embeddings.create(...),                                                                                                
      timeout=remaining_ms / 1000.0            
  )

  This is asyncio.wait_for — binary. Either OpenAI responds within remaining_ms and you get the exact same 1536-dimensional vector,
  or it doesn't and you get nothing. There is no "partial embedding." There is no "better embedding with more time." The vector for
  "fuel filter generator" is identical whether it returns at 80ms or 4000ms.

  So you're right — time is the wrong limiter. It's a metric, not a control. The question isn't "how much time should we allocate?"
  The question is: "what is the minimum network round-trip time to OpenAI from this deployment location?"

  ┌─────────────────────┬───────────────┬───────────────────┬─────────────────────┐
  │     Deployment      │ TCP to OpenAI │ Min viable budget │   Current budget    │
  ├─────────────────────┼───────────────┼───────────────────┼─────────────────────┤
  │ Render (us-east-1)  │ ~10ms         │ ~80ms             │ 150ms ✓ works       │
  ├─────────────────────┼───────────────┼───────────────────┼─────────────────────┤
  │ Mac Studio (Sydney) │ ~262ms        │ ~350ms            │ 150ms ✗ NEVER works │
  └─────────────────────┴───────────────┴───────────────────┴─────────────────────┘

  The 150ms budget was tuned for Render. It's not "too tight" — it's physically impossible on local dev. Light doesn't travel from
  Sydney to Virginia in 150ms.

  Parkinson's Law doesn't apply here because the embedding API isn't doing "work that expands." OpenAI's model runs in fixed time
  (~20-50ms compute). The rest is TCP. Setting 1s vs 500ms vs 2000ms returns the same result, same vector, same quality. The only
  difference is: at what point do you give up waiting?

  The correct fix isn't "increase budget" — it's:

  1. Set budget to max(TCP_RTT * 1.5, 150) — physics-aware, not arbitrary
  2. Cache aggressively — the in-memory cache (line 463, TTL 30min, max 500 entries) means the SECOND search for "fuel filter" is
  0ms. First search pays the TCP cost, everything after is free.

  The embedding is searching for truth (nearest vector in 1536-d space). Volume is irrelevant. You get the same truth at any budget
  — or you get nothing.


=======
                                                                                                        
  Phase 1: diagnostics (line 888)                                                                                                   
  Phase 2: Cortex rewrites + embedding generation (line 899)                                                                        
  Phase 2.5: Entity extraction — analytics only (line 954)                                                                          
  Phase 3: f1_search_cards RPC — trigram + TSV + vector in ONE SQL call (line 1004)
  Phase 3b: RRF fusion (line ~1200)
  Phase 4: result_batch emission (line ~1306)

  There aren't 5 independent workers with 5 independent chances to find results. There's one DB function (f1_search_cards) that runs
   3 signals internally (trigram, TSV, vector), and they all fail for the same reason: the input query is too noisy for trigram/TSV,
   and the embedding that would power vector search timed out.

  So the keyword fallback is compensating for a lack of signal diversity — it's a symptom of a single-query-in, single-RPC
  architecture. If Fix 1 cleans the input and Fix 2 ensures embeddings arrive, the 3 signals inside f1_search_cards should be
  sufficient. The keyword fallback becomes dead code.

  ---
  Revised Assessment

  Your questions reveal the plan should be reordered:

  ┌──────────┬─────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────┐
  │ Priority │           Fix           │                                       Rationale                                        │
  ├──────────┼─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ 1        │ Embedding budget =      │ Binary fix. Set to TCP_RTT × 1.5. Enables vector search. Identical output quality.     │
  │          │ physics-aware           │                                                                                        │
  ├──────────┼─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ 2        │ Preamble stripping      │ Belt-and-suspenders for when embeddings are unavailable (cache miss + API down).       │
  │          │                         │ Improves trigram/TSV signal-to-noise.                                                  │
  ├──────────┼─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ 3        │ try/except text search  │ Pure defensive coding. No quality change, prevents hard crash.                         │
  ├──────────┼─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ ~~4~~    │ ~~Keyword fallback~~    │ DROP IT. If fixes 1-2 work, the existing signals handle everything. Adding a 4th       │
  │          │                         │ fallback path adds complexity for a scenario that shouldn't happen.                    │
  └──────────┴─────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────┘
========


  The budget insight is the key one. The embedding is a step function: you either get the exact same 1536-d vector or you get
  nothing. Time doesn't improve quality — it only determines whether the API response arrives before the timeout. The right budget
  is f(network_latency), not f(desired_quality). Setting it to 150ms on a 262ms-RTT connection is like setting a 1-minute timer for
  a 2-minute egg — you'll always throw it away raw.

  Cache changes the economics entirely: First query pays TCP cost. All subsequent queries for the same text are 0ms (in-memory LRU,
  TTL 30min, max 500). The budget only matters for cache misses.

=====
                                                                                                           
  The Smoking Gun: Sequential Entity Extraction Blocking Search                                                                     
                                                                                                                                    
  Here's the exact execution waterfall for an L1 query like "Show me the fuel filter for the generator":                            
                                               
  KEYSTROKE
    │
    ├─ 80-140ms ── Frontend debounce (useCelesteSearch.ts:124-125)
    │
    ├─ 0-2000ms ── JWT token refresh if expired (useCelesteSearch.ts:142)
    │
    ▼ fetch() to API
    │
    ├─ ~5ms ───── Phase 1: diagnostics emit (instant)
    │
    ├─ ~5-150ms ─ Phase 2: generate_rewrites() (line 906) ← SEQUENTIAL await
    │
    ├─ ~0ms ───── Phase 2b: embedding_task fires in background ← GOOD
    │
    ├─ 3000-5000ms ── Phase 2.5: orchestrator.extract(q) (line 971) ← THE BOTTLENECK
    │                  │
    │                  └─ coverage_controller.decide() → needs_ai=True
    │                     └─ ai_extractor._call_openai() → GPT-4o-mini chat.completions
    │                        └─ Full LLM inference call, not an embedding
    │
    ├─ 500-3000ms ── Phase 3: run_text_search() (line 1061) ← SEQUENTIAL await
    │
    ├─ 0-800ms ──── L2 embedding escalation if needed (line 1094)
    │
    ├─ 200-500ms ── Vector search (line 1172)
    │
    ├─ ~50ms ────── RRF fusion + snippets
    │
    └─ emit result_batch + finalized

  TOTAL: 3800-9700ms backend
       + 80-2140ms frontend overhead
       = 3900-11,840ms user-perceived

  Phase 2.5 is the killer. It's:
  1. SEQUENTIAL — await orchestrator.extract(q) at line 971 blocks everything after it
  2. Calls GPT-4o-mini (chat.completions.create, line 148 of ai_extractor_openai.py) — a full LLM inference, not a cheap embedding
  3. Used for ANALYTICS ONLY — lines 955-958 explicitly say "ANALYTICS ONLY", "we do NOT use them to filter the search"
  4. Triggered BY L1 queries specifically — the coverage controller (line 45-53) flags needs_ai=True when it sees words like
  "please", "check", "see", "ensure" — exactly the words L1 articulate speakers use

  Look at coverage_controller.py:45-53:

  INSTRUCTION_PATTERNS = [
      r'\bplease\b',     # ← "Please show me the fuel filter"
      r'\bcheck\b',      # ← "Can you check the EPIRB battery"
      r'\bsee\b',        # ← "I need to see the work order"
      r'\bensure\b',
      r'\bmake\s+sure\b',
      r'\bverify\b',
      r'\bconfirm\b'
  ]

  Line 109: elif has_negation or has_instruction: needs_ai = True

  L1 queries (natural language) almost ALWAYS contain these words. So the system punishes articulate users with a 3-5 second LLM
  call that produces analytics data nobody looks at during the search.

  Meanwhile L2 ("fuel filter generator") has no instruction words, regex coverage is high → needs_ai=False → skips the LLM call →
  search starts immediately.

  ★ Insight ─────────────────────────────────────
  This is the inverse of what you'd expect. The entity extraction was designed to HELP complex queries by understanding them better.
   But because it's sequential and its results aren't used for search, it only adds latency. The more articulate your query, the
  more likely it triggers AI extraction, and the slower your search. The system literally penalizes good English.

  The fix isn't about budgets or preamble stripping. Those are symptoms. The root cause is: a 3-5 second sequential LLM call that
  blocks the search pipeline for analytics-only data.
  ─────────────────────────────────────────────────


=====

  ┌─────┬───────────────────────────────────────────┬──────────────────────────┬────────────────────────────────────────────────┐
  │  #  │                Root Cause                 │      Latency Impact      │                      Fix                       │
  ├─────┼───────────────────────────────────────────┼──────────────────────────┼────────────────────────────────────────────────┤
  │     │ Entity extraction blocks search pipeline  │                          │ Make it asyncio.create_task() —                │
  │ 1   │ (SEQUENTIAL await for ANALYTICS-ONLY      │ 3000-5000ms              │ fire-and-forget, collect results after search  │
  │     │ data)                                     │                          │ completes                                      │
  ├─────┼───────────────────────────────────────────┼──────────────────────────┼────────────────────────────────────────────────┤
  │ 2   │ Embedding budget below TCP RTT            │ 150-800ms (binary: works │ Set to max(TCP_RTT * 1.5, 150) via env var     │
  │     │                                           │  or doesn't)             │                                                │
  ├─────┼───────────────────────────────────────────┼──────────────────────────┼────────────────────────────────────────────────┤
  │ 3   │ No preamble stripping                     │ 0ms latency, but 0       │ Strip before DB signals                        │
  │     │                                           │ results from trigram/TSV │                                                │
  ├─────┼───────────────────────────────────────────┼──────────────────────────┼────────────────────────────────────────────────┤
  │ 4   │ No try/except on text search              │ 0ms unless failure, then │ Defensive wrap                                 │
  │     │                                           │  catastrophic            │                                                │
  └─────┴───────────────────────────────────────────┴──────────────────────────┴────────────────────────────────────────────────┘

  Fix 1 alone would cut 3-5 seconds from every L1 query. That's your 8-10s → 3-5s immediately.

  Your intuition was right: "we could literally run a basic SQL fetch command and get results in the time the pipeline wastes." The
  SQL is fast. The pipeline wrapping it is the problem — specifically, a sequential LLM call for data that doesn't affect results.
=====
                                                                                        
  The Extraction Pipeline: What Each Stage Does                                                                                     
                                                                                                                                    
  The extraction system is a 5-stage pipeline at apps/api/extraction/:                                                              
                                               
  Stage 0: Text Cleaner (text_cleaner.py)

  Pure CPU, ~0ms. Prepares text for pattern matching:

  Input:  "µA reading on 3512C is 45°c — activewarnings"
  Output: "uA reading on 3512C is 45°C — active warnings"

  What it does:
  - Unicode normalization (NFKC): µ→u, Ω→Ohm, ×→x, ±→+/-
  - Degree/unit standardization: 45 ° c → 45°C, 230VDC → 230 VDC
  - CamelCase splitting: activeWarnings → active Warnings
  - Known compound splits: fuelfilter → fuel filter, workorder → work order (28 hardcoded pairs, line 273-298)
  - Tokenization with stopword removal (the, a, is, for etc. stripped for coverage math)

  Stage 1: Regex Extractor (regex_extractor.py, ~2000 lines)

  The workhorse. Handles ~85% of all extraction. Pure CPU, ~5-10ms. Uses four layers:

  Layer A — 37 regex pattern types, applied in strict precedence order (lines 175-219):

  fault_code → location_on_board → certificate_type → voyage_type →
  work_order_type → equipment → work_order_status → approval_status →
  shopping_list_term → rest_compliance → warning_severity →
  delivery_date → receiving_status → stock_status → equipment_status →
  measurement → measurement_range → setpoint → limit → document_id →
  document_type → work_order_id → model → part_number_prefix →
  part_number → serial_number → po_number → ...

  Each type has 2-6 compiled regex patterns. For example equipment (line 276-283):
  r'\b(gen(?:erator)?\s*[#]?\s*[12])\b'  # "gen 1", "generator 2"
  r'\b(eng(?:ine)?\s*[#]?\s*[12])\b'     # "eng 1", "engine 1"
  r'\b(genset\s*[#]?\s*[12])\b'          # "genset 1"

  Layer B — Gazetteer matching (from loader.py):
  - CORE_BRANDS: ~200 manufacturer names (Caterpillar, Yanmar, Cummins, Fleetguard, Grundfos, Lewmar, Viking, Blue Sea Systems,
  Raymarine, MTU, etc.)
  - CORE_EQUIPMENT: ~300 equipment terms (pump, filter, generator, valve, compressor, heat exchanger, etc.)
  - CORE_FUZZY_TERMS: Stock/warning/compliance terms with entity type mapping
  - BRAND_ALIASES: Misspelling→canonical mappings

  Layer C — rapidfuzz (if installed): Fuzzy matching for brand typos. "Fleetgard" → "Fleetguard" at 90% similarity.

  Layer D — Context-aware confidence (lines 119-169): Each entity type has positive/negative context patterns that adjust
  confidence:
  'fault_code': {
      'positive': r'code|error|fault|alarm|warning|trip|dtc|spn|fmi...'
      'negative': r'HTTP|SMTP|IMAP|URL|JPEG|PDF...'  # Don't extract HTTP 404 as fault code
  }

  Layer E — Negation detection (lines 84-98): "do NOT start the engine" → Entity("start", action, negated=True)

  Layer F — Qualifier extraction (lines 107-116): "above 50°C" → Entity("50°C", measurement, qualifier="above")

  Stage 2: Coverage Controller (coverage_controller.py)

  Pure CPU, ~1ms. Decides: do we need GPT-4o-mini?

  coverage = (tokens matched by regex) / (total meaningful tokens)

  needs_ai = True when ANY of these fire:

  ┌────────────────────┬──────────────────────────────────────────────┬────────────┐
  │        Rule        │                   Trigger                    │ Threshold  │
  ├────────────────────┼──────────────────────────────────────────────┼────────────┤
  │ Low coverage       │ Regex matched < 85% of tokens                │ < 0.85     │
  ├────────────────────┼──────────────────────────────────────────────┼────────────┤
  │ High unknown ratio │ Important-looking uncovered terms            │ >= 0.10    │
  ├────────────────────┼──────────────────────────────────────────────┼────────────┤
  │ Instruction words  │ "please", "check", "see", "ensure", "verify" │ any match  │
  ├────────────────────┼──────────────────────────────────────────────┼────────────┤
  │ Negation words     │ "don't", "never", "without", "avoid"         │ any match  │
  ├────────────────────┼──────────────────────────────────────────────┼────────────┤
  │ Entity conflicts   │ Overlapping entities of different types      │ any        │
  ├────────────────────┼──────────────────────────────────────────────┼────────────┤
  │ Short + incomplete │ ≤3 tokens with < 90% coverage                │ short text │
  └────────────────────┴──────────────────────────────────────────────┴────────────┘

  Stage 3: AI Extractor (ai_extractor_openai.py)

  GPT-4o-mini via chat.completions.create (line 148). This is a full LLM inference — NOT an embedding. It sends a structured prompt
  with examples and gets back a JSON of extracted entities.

  Why 4o-mini specifically (line 21): self.model = os.getenv("AI_MODEL", "gpt-4o-mini") — it's the cheapest/fastest chat model.
  Originally this was qwen2.5:3b running locally on Ollama (line 4: "Cloud-optimized replacement for local Ollama qwen2.5:3b"). When
   deployment moved from local GPU to cloud, they switched to OpenAI's cheapest model.

  Cost per call: ~0.15¢ input + ~0.60¢ output per 1M tokens. For a 50-token query, that's ~$0.000003 per extraction. The cost isn't
  money — it's latency: 3-5 seconds per call.

  Stage 4: Entity Merger (entity_merger.py)

  Pure CPU, ~2ms. Combines regex + AI entities:
  - Adjacency stitching: "Main" (qualifier) + "Engine" (equipment) → "Main Engine" (equipment, confidence boosted +0.05)
  - Score-based dedup: When entities overlap, highest-scoring wins (confidence × source_multiplier × span_length)
  - AI hallucination grounding: If AI extracts an entity not present in the source text → rejected (line 440)
  - Domain validation: Equipment terms misclassified as ORG, invalid measurement ranges, fault code format validation
  - Normalization: Fault code canonicalization (SPN-1234-FMI-5 → SPN 1234 FMI 5)

  ---
  The Signal Router (signal_router.py)

  Maps entity types → search targets (shard + domain + budget). 0ms, pure CPU. Example:

  "part_number" → [exact/parts/40ms, exact/inventory/40ms, text/parts/40ms, vector/parts/120ms]
  "brand"       → [text/parts/40ms, vector/parts/120ms]
  "fault_code"  → [exact/work_orders/40ms, text/work_orders/40ms, vector/work_orders/120ms]

  ---
  Now: The Design vs The Implementation

  You said the system was designed for PARALLEL workers. You're right. Here's the intended architecture vs what's actually running:

  The Design (from DEPLOY.md)

  User types "pump"
         │
      ┌──┴──────────────────────────────────────┐
      │         PARALLEL WORKERS                 │
      │                                          │
      │  Worker 1: Intent (extraction)    ───┐   │
      │  Worker 2: Exact (ID lookup)      ───┤   │
      │  Worker 3: BM25/TSV (full-text)   ───┤   │
      │  Cortex: Query expansion          ───┤   │
      │  Embedding: Vector generation     ───┤   │
      │                                      ▼   │
      │              RRF Fusion (K=60)            │
      └──────────────────────────────────────────┘

  The Implementation (actual code, lines 866-1311)

                    SEQUENTIAL WATERFALL
                          │
  Phase 2:  await generate_rewrites()           ──── ~5-150ms  BLOCKS
                          │
  Phase 2b: asyncio.create_task(embedding)      ──── 0ms       PARALLEL ✓
                          │
  Phase 2.5: await orchestrator.extract()       ──── 3000-5000ms BLOCKS ✗✗✗
                          │
  Phase 3:  await run_text_search()             ──── 500-3000ms BLOCKS
                          │
            if text_hits < 3:
              await generate_embeddings(L2)     ──── 0-800ms   BLOCKS
                          │
  Phase 3c: await run_vector_search()           ──── 200-500ms  BLOCKS
                          │
  Phase 4:  reciprocal_rank_fusion()            ──── ~5ms       instant
                          │
            yield result_batch

  Only ONE thing runs in parallel: the embedding background task (line 940). Everything else is a sequential await chain.

  ★ Insight ─────────────────────────────────────
  The gap between design and implementation is where the 6-8 seconds lives. The architecture says "5 parallel workers." The code
  says await → await → await → await. The entity extraction alone (Phase 2.5) accounts for 3-5s and its output is stamped "ANALYTICS
   ONLY" at line 955. It's a parallel system built with sequential plumbing.

  The f1_search_cards SQL function IS internally parallel — PostgreSQL runs trigram, TSV, and exact match as three CTEs in one
  query. But from Python's perspective, it's one await conn.fetch(). The vector search is a SEPARATE await that runs AFTER text
  search completes, not alongside it.
  ─────────────────────────────────────────────────

  ---
  What Should Be Parallel (and isn't)

  ┌────────────────────────────┬──────────────────────┬─────────────────────┬──────────────────────────────────────────────────┐
  │         Operation          │       Current        │      Should Be      │                       Why                        │
  ├────────────────────────────┼──────────────────────┼─────────────────────┼──────────────────────────────────────────────────┤
  │ Cortex rewrites            │ Sequential           │ Sequential          │ Fast (~5ms), needed before everything else       │
  ├────────────────────────────┼──────────────────────┼─────────────────────┼──────────────────────────────────────────────────┤
  │ Embedding generation       │ Parallel ✓           │ Parallel            │ Already correct — asyncio.create_task            │
  ├────────────────────────────┼──────────────────────┼─────────────────────┼──────────────────────────────────────────────────┤
  │ Entity extraction          │ Sequential ✗         │ Fire-and-forget     │ Analytics-only. 3-5s for data nobody uses during │
  │                            │                      │                     │  search                                          │
  ├────────────────────────────┼──────────────────────┼─────────────────────┼──────────────────────────────────────────────────┤
  │ Text search                │ Sequential           │ Parallel with       │ Currently waits for extraction to finish first   │
  │ (f1_search_cards)          │                      │ vector              │                                                  │
  ├────────────────────────────┼──────────────────────┼─────────────────────┼──────────────────────────────────────────────────┤
  │ Vector search              │ Sequential (after    │ Parallel with text  │ Currently waits for text results + embedding     │
  │                            │ text)                │                     │                                                  │
  ├────────────────────────────┼──────────────────────┼─────────────────────┼──────────────────────────────────────────────────┤
  │ RRF fusion                 │ Sequential           │ Sequential          │ Must wait for all inputs — correct               │
  └────────────────────────────┴──────────────────────┴─────────────────────┴──────────────────────────────────────────────────┘


=====
 The fix that matches the original design:

  # CURRENT (sequential, 6-9s total)
  rewrites = await generate_rewrites(q, ctx)          # 5ms
  embedding_task = asyncio.create_task(embed(rewrites)) # 0ms (background)
  extraction = await orchestrator.extract(q)            # 3000-5000ms BLOCKING
  text_results = await run_text_search()                # 500-3000ms
  # ... L2 check ...
  vector_results = await run_vector_search()            # 200-500ms

  # CORRECT (parallel, 2-3s total)
  rewrites = await generate_rewrites(q, ctx)            # 5ms (needed first)
  embedding_task = asyncio.create_task(embed(rewrites))  # background
  extraction_task = asyncio.create_task(orchestrator.extract(q))  # background (analytics)
  text_task = asyncio.create_task(run_text_search())     # background

  # Wait for text results (needed for L2 decision)
  text_results = await text_task                         # 500-3000ms
  # L2 escalation if needed...
  vector_results = await run_vector_search()             # 200-500ms
  # Collect extraction for analytics (already done by now)
  extraction = await extraction_task                     # 0ms (finished while text ran)

  Time saved: 3-5 seconds — the entire entity extraction latency disappears because it runs alongside the text search instead of
  before it.

=====
❯ stage                                                                                                                             
0= good.                                                                                                                            
1 = great                                                                                                                           
2 = great                                                                                                                           
3 = great (just hceck outputs) see ltencya dn accuracy, gpt here does not need to add confidence, or weights. just literal          
seperation of terms etc.?                                                                                                           
4 = great, ensure this correctly add term types.                                                                                    
======                                                                                                                              
when we run sequutinal vs parallel, if we have 200ms overhead from stage 0+1+2+4, that is fine.                                     
"  Phase 2.5: await orchestrator.extract()       ──── 3000-5000ms BLOCKS ✗✗✗" i dont get how this is long altenyc? for gpt, fine.   
but then why is phase   Phase 3:  await run_text_search()             ──── 500-3000ms BLOCKS                                        
affected?                                                                                                                           
                                                                                                                                    
liek you suggestied articualed, wl2/l3 is trigger thrshold, not alays. hence latnecy drops immeditaltely. given we also employ the  
degrade gracefully not abrupty                                                     
=====
Stage 3 (GPT-4o-mini) does exactly what you said: literal separation of terms into typed buckets. No confidence 
  scores, no weights, no ranking. Just:        
                                                                                                                                    
  Input: "Show me the fuel filter for generator 2"                                                                                  
  Output: {"equipment": ["generator 2"], "subcomponent": ["fuel filter"], "action": [], ...}                                        
                                                                                                                                    
  Temperature 0.0, JSON mode, max 800 tokens. It's a classifier, not a scorer.

  Now to your core question:

  Why does Phase 2.5 blocking affect Phase 3?

  It doesn't affect Phase 3's execution time. It affects when Phase 3 can START.

  L1 query: "Please show me the fuel filter for generator 2"
                                      ↓
      ┌─ coverage_controller.decide() ─┐
      │  "please" matches INSTRUCTION  │
      │  needs_ai = True               │
      └────────────────────────────────┘
                                      ↓
      Phase 2.5: await GPT-4o-mini ───── 3500ms (just sitting here)
                                      ↓
      Phase 3:   await text_search ───── 800ms  (fast when it finally runs)
                                      ↓
      Total: 4300ms


  L2 query: "fuel filter generator 2"
                                      ↓
      ┌─ coverage_controller.decide() ─┐
      │  No instruction words          │
      │  Regex covers "generator 2"    │
      │  Coverage > 85%                │
      │  needs_ai = False              │
      └────────────────────────────────┘
                                      ↓
      Phase 2.5: regex only ──────────── 10ms
                                      ↓
      Phase 3:   await text_search ───── 800ms  (same speed)
                                      ↓
      Total: 810ms

  Phase 3 takes the same 500-800ms either way. The difference is the 3500ms of dead time before it's allowed to start. The await on
  line 971 is a traffic light — L1 queries sit at red for 3.5 seconds, L2 queries get green immediately.

  You said it: L2/L3 don't trigger the threshold. That's why L2 at 93.3% pass rate with fast latency, and L1 at 66.7% with 8-10s
  latency. The coverage controller is the gate.

  The Fix (one line, matches original design)

  Line 971 currently:
  extraction_result = await orchestrator.extract(q)

  Should be:
  extraction_task = asyncio.create_task(orchestrator.extract(q))

  Then collect it later (after search completes) for analytics:
  # After result_batch is emitted, collect analytics
  try:
      extraction_result = await asyncio.wait_for(extraction_task, timeout=0.1)
  except (asyncio.TimeoutError, Exception):
      extraction_result = None

  That's it. The GPT call still runs. The analytics still get collected. But the text search starts immediately instead of waiting
  3.5 seconds.

  BEFORE (sequential):
    Rewrites(5ms) → Extract(3500ms) → TextSearch(800ms) → Vector(300ms) = 4605ms

  AFTER (parallel):
    Rewrites(5ms) → TextSearch(800ms) → Vector(300ms) = 1105ms
                  ↘ Extract(3500ms, background, analytics only)

  Graceful degradation, not abrupt ending: If the extraction task finishes before the search completes, its results are available
  for the diagnostics event. If it doesn't finish in time, we skip analytics metadata — the search results are identical either way
  because extraction was never used for filtering.

  ★ Insight ─────────────────────────────────────
  The system penalizes polite English because "please" is an INSTRUCTION_PATTERN trigger (coverage_controller.py:46). A Filipino
  deckhand who types "please check EPIRB battery" waits 3.5 seconds longer than a British chief engineer who types "EPIRB battery".
  The irony: the more courteous the query, the slower the response. One asyncio.create_task fixes this — the extraction still
  happens, it just doesn't block the search.
  ─────────────────────────────────────────────────


=====
USER CONFIRMATIONS (2026-03-10):

1. Stage 0 = good
2. Stage 1 = great
3. Stage 2 = great
4. Stage 3 = great — just literal separation of terms, no confidence/weights needed
5. Stage 4 = great — ensure correctly adds term types
6. 200ms overhead from stages 0+1+2+4 is fine
7. Phase 2.5 blocking: the 3-5s GPT latency is understood. The question was WHY it affects Phase 3 — answer: it doesn't affect Phase 3's execution time, only when Phase 3 can START (traffic light analogy)
8. L2/L3 don't trigger the coverage threshold → latency drops immediately for non-L1 queries
9. Degrade gracefully, not abruptly — confirmed approach
10. Keyword fallback: DROPPED — 5 workers should be sufficient if fixes 1-2 work

=====
FINAL FIX PRIORITY (agreed):

Fix 1: Entity extraction → asyncio.create_task (fire-and-forget) — saves 3-5s on L1 queries
Fix 2: Embedding budget → env-var, physics-aware defaults (500ms L1, 2000ms L2) — enables vector search locally
Fix 3: Preamble stripping → belt-and-suspenders for trigram/TSV when vectors unavailable
Fix 4: try/except text search → graceful degradation, prevents hard crash

Plan written to tasks/todo.md — awaiting approval.
=====
