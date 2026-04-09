  Worker Infrastructure — CEO Briefing

  Prepared for: Independent Engineering Review
  Date: 2026-03-18
  Subject: Background services that keep the Celeste search system alive — what they do, what's wrong, and what needs attention

  ---
  1. Business Context (One Paragraph)

  Celeste is a digital operations platform for yacht crew. Its most important capability is search — crew members type natural language
  commands ("order hydraulic oil for port thruster", "show me overdue work orders") and the system finds the right records instantly.
  For that to work, every record in the system — maintenance jobs, equipment, parts, documents, emails — must be continuously indexed
  behind the scenes. That indexing is the job of the background workers described in this document. Without them, search degrades
  silently: results go stale, new records become invisible, and the AI-powered "Also Related" feature returns nothing useful. These
  workers are not visible to users, but they are the engine that makes the product function.

  ---
  2. The Five Workers — What Each Does

  Worker 1 — projection-worker

  Source file: apps/api/workers/projection_worker.py

  What it does: Whenever a crew member creates or updates a record (a fault report, a work order, a parts order), a database trigger
  places that record into a queue. The projection worker watches this queue continuously. For each new or changed record, it extracts
  the meaningful text — the title, status, equipment name, severity, manufacturer, and so on — and combines it into a single searchable
  text description. It then writes that description back to the central search index table (search_index). This text is what gets
  searched.

  Why it matters: It is the first step in making any record findable. If this worker stops, new records silently disappear from search.
  There is no error message to the user — results simply become incomplete.

  Relationship to other workers: Its output feeds directly into Worker 2. It does not generate embeddings itself — it only writes the
  text. Worker 2 picks up from there.

  Run location: Docker (local testing only). Not currently deployed on Render (the cloud platform). This is a significant gap — see
  Section 3.

  ---
  Worker 2 — embedding-worker

  Source file: apps/api/workers/embedding_worker_1536.py

  What it does: Reads the text descriptions written by Worker 1, sends them to OpenAI's text embedding API, and receives back a
  numerical "fingerprint" of the meaning of that text (a vector of 1,536 numbers). It stores these fingerprints in the database. When a
  user searches, the system converts their query into the same kind of fingerprint and finds the records whose fingerprints are most
  similar. This is what makes semantic search work — finding "port thruster oil leak" even when the record says "hydraulic fluid loss on
   P thruster".

  Why it matters: Without this worker, search falls back to keyword matching only. Semantic understanding — the part that makes the
  product feel intelligent — is disabled.

  Relationship to other workers: Depends entirely on Worker 1 having populated the text first. Also depends on the cache listener
  (Worker 4) to clear stale search results from the cache after indexing completes.

  Cost note: Every embedding call costs money (OpenAI API). The worker has a circuit breaker — if OpenAI fails 5 times in a row, it
  pauses for 60 seconds to avoid runaway spend.

  Run location: Docker only. Not currently deployed on Render.

  ---
  Worker 3 — email-watcher

  Source file: apps/api/workers/email_watcher_worker.py

  What it does: Every 30 seconds, this worker connects to Microsoft Exchange/Outlook on behalf of each crew member who has linked their
  email account. It pulls in new emails, stores them in the database, and makes them available inside Celeste alongside other
  operational records. It also quietly refreshes authentication tokens in the background so email access does not expire.

  Why it matters: Email is the primary channel through which third-party vendors, brokers, and port agents communicate with yacht crews.
   If this worker stops, the email section of Celeste goes dark — no new messages appear, and the crew has no visibility from within the
   product.

  Relationship to other workers: The emails it pulls in are also indexed by Workers 1 and 2, making email content searchable alongside
  maintenance records and parts.

  Run location: Deployed on Render as celeste-email-watcher. This is the only background worker currently in Render's
  infrastructure-as-code file (render.yaml).

  ---
  Worker 4 — cache-listener

  Source file: apps/api/cache/invalidation_listener.py

  What it does: The API caches search results in Redis (an in-memory database) so that repeated searches return instantly without
  hitting the main database. When a record is updated and re-indexed by Worker 1, the database sends a real-time signal (via a Postgres
  feature called pg_notify). The cache listener receives that signal and immediately deletes the relevant cached results, so the next
  search fetches fresh data.

  Why it matters: Without this, a crew member could update a fault report and search results would show the old version for an unknown
  period (until the cache naturally expires). On a yacht, stale maintenance data is a safety concern.

  Relationship to other workers: It is downstream of Worker 1. It receives signals from the same database that Workers 1 and 2 write to.

  Run location: Docker only. Not currently deployed on Render.

  ---
  Worker 5 — nightly-feedback-loop

  Source file: apps/api/workers/nightly_feedback_loop.py

  What it does: Runs once per night (3 AM UTC). It looks at what crew members searched for over the past 30 days and which results they
  actually clicked on. From this, it learns yacht-specific vocabulary — for example, that this particular yacht's crew uses the word
  "Desali" to mean "Watermaker Unit 2". It stores these learned associations alongside each record (in a learned_keywords field). The
  next time anyone searches "Desali", that record ranks higher.

  Why it matters: Search relevance improves over time without manual tuning. The learning is isolated per yacht — what one yacht's crew
  searches never affects another's results. This is the product's self-improving quality layer.

  Relationship to other workers: It writes learned_keywords but never touches search_text. This boundary is deliberate — Workers 1 and 2
   own search_text. The separation prevents one worker from overwriting another's data.

  Run location: Deployed on Render as a scheduled cron job (nightly-feedback-loop).

  ---
  3. The Pipeline — How They Connect

  The five workers form a chain:

  Record created/updated in DB
          ↓
  Worker 1 (projection-worker)
    — builds text description
    — writes to search_index
          ↓
  Worker 2 (embedding-worker)
    — converts text to vector fingerprint
    — writes to search_index
          ↓ (simultaneously)
  Worker 4 (cache-listener)
    — receives signal from DB
    — evicts stale Redis cache
          ↓
  Record is now findable by semantic search

  Worker 3 (email-watcher) feeds new emails into the same pipeline at the top.
  Worker 5 (nightly feedback) adds learned vocabulary at the bottom, after indexing completes.

  ---
  4. Known Issues — Prioritised

  Critical: Workers 1, 2, and 4 are not on Render

  The projection worker, embedding worker, and cache listener are defined in docker-compose.f1-workers.yml (a local development file)
  but are absent from render.yaml (the file that controls what runs in production). This means either:
  - They were added to Render manually via the dashboard (not tracked, not reproducible, not auditable), or
  - They are not running in production at all.

  Business impact: If not running, every record created in production since launch has no search text and no vector fingerprint. The
  product's search is working from a frozen snapshot.

  Immediate action required: Confirm with the infrastructure team whether these three services are live on Render. If they are, add them
   to render.yaml immediately. If they are not, this is a production incident.

  ---
  Moderate: Source version guard caused 226 records to be stranded

  The projection worker has a write-protection rule: it will not overwrite a record in the search index if the record's version number
  has not changed. This was designed to prevent race conditions. However, when the indexing system was upgraded, 226 shopping list items
   already had a version number stored that matched what the worker was trying to write — so the worker silently skipped them. Those 226
   records had no searchable text and no vector. A one-time data patch has been prepared (see reference notes) and should be applied to
  production.

  ---
  Low: Stale configuration table (search_projection_map)

  Before the recent upgrade, the projection worker used a database table called search_projection_map to decide how to build search text
   for each entity type. As of 2026-03-17, that logic was replaced by Python code (entity_serializer_sync.py). The database table still
  exists and is still read by the worker for other purposes (filter_map, payload_map), but its search_text_cols column is now unused. It
   is dead configuration. Future engineers will be confused by it unless it is documented or the dead column is removed.

  ---
  Low: Abandoned deployment file

  The file apps/api/render.yaml is an old blueprint for a different worker ("email-rag-worker") that references a worker.py file that
  does not exist. This file is not referenced anywhere and is not deployed. It is misleading noise in the repository. It should be
  deleted.

  ---
  5. Wastefulness and Pollution

  Item: Dead Render blueprint
  Location: apps/api/render.yaml
  Problem: References non-existent worker.py. Never deployed. Confuses engineers.
  Action: Delete
  ────────────────────────────────────────
  Item: search_projection_map.search_text_cols
  Location: Database table
  Problem: Column is vestigial after the Piece B upgrade. Still queried at startup but ignored.
  Action: Document or drop the column
  ────────────────────────────────────────
  Item: Dual env var names
  Location: embedding_worker_1536.py lines 57–58
  Problem: Both EMBED_MODEL / EMBEDDING_MODEL and EMBED_DIMS / EMBED_DIM are accepted. This is harmless but creates documentation debt —

    engineers cannot know which is canonical.
  Action: Pick one, remove the other
  ────────────────────────────────────────
  Item: Poll interval mismatch
  Location: email_watcher_worker.py line 46
  Problem: Code says "Changed from 60 to 30 seconds" as an inline comment but render.yaml still documents 60 as the default. Actual
    behaviour and documented configuration disagree.
  Action: Align render.yaml env var to 30s
  ────────────────────────────────────────
  Item: Two ops health monitors
  Location: render.yaml lines 69, 101
  Problem: documents-health-worker and shopping-list-health-worker are two separate Render workers that do essentially the same thing —
    call the API every 15 minutes and check a specific endpoint. They cost $7/month each on Render's starter plan.
  Action: Consolidate into one generic health monitor

  ---
  6. Files Involved — Status Summary

  ┌─────────────────────────────────────────────┬─────────────────┬─────────────────────────────────────────────────────────────────┐
  │                    File                     │     Status      │                             Purpose                             │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │                                             │ Modified        │ Builds searchable text for every entity type. Now calls         │
  │ apps/api/workers/projection_worker.py       │ (2026-03-17)    │ entity_serializer_sync.py instead of DB table. Critical         │
  │                                             │                 │ production dependency.                                          │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ apps/api/workers/embedding_worker_1536.py   │ Unchanged       │ Converts searchable text to AI vectors. Pure infrastructure —   │
  │                                             │                 │ no business logic.                                              │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ apps/api/workers/email_watcher_worker.py    │ Unchanged       │ Pulls email into Celeste from Microsoft Exchange. Only worker   │
  │                                             │                 │ confirmed live on Render.                                       │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ apps/api/cache/invalidation_listener.py     │ Unchanged       │ Clears stale search cache when data changes. Docker-only —      │
  │                                             │                 │ Render status unknown.                                          │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ apps/api/workers/nightly_feedback_loop.py   │ Unchanged       │ Learns crew vocabulary from search behaviour. Runs nightly on   │
  │                                             │                 │ Render.                                                         │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ apps/api/services/entity_serializer_sync.py │ Created         │ The text-building logic that Worker 1 now calls. Covers 14      │
  │                                             │ (2026-03-17)    │ entity types. Has 20 unit tests.                                │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ docker-compose.f1-workers.yml               │ Unchanged       │ Local testing only. Defines Workers 1, 2, and 4 as Docker       │
  │                                             │                 │ containers.                                                     │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ render.yaml (root)                          │ Unchanged       │ Production deployment config. Missing Workers 1, 2, 4.          │
  ├─────────────────────────────────────────────┼─────────────────┼─────────────────────────────────────────────────────────────────┤
  │ apps/api/render.yaml                        │ Unchanged       │ Stale/dead. Should be deleted.                                  │
  └─────────────────────────────────────────────┴─────────────────┴─────────────────────────────────────────────────────────────────┘

  ---
END OF DOCUMENT