background worker issues;

### nightly-feedback-loop
==> Running 'python -m workers.nightly_feedback_loop'
Traceback (most recent call last):
  File "<frozen runpy>", line 189, in _run_module_as_main
  File "<frozen runpy>", line 112, in _get_module_details
  File "/opt/render/project/src/apps/api/workers/__init__.py", line 7, in <module>
    from .email_watcher_worker import EmailWatcherWorker
  File "/opt/render/project/src/apps/api/workers/email_watcher_worker.py", line 27, in <module>
    from supabase import create_client
ModuleNotFoundError: No module named 'supabase'
❌ Your cronjob failed because of an error: Exited with status 1

=====
### projection_worker
2026-02-22 18:48:06,266 [INFO] projection_worker - Loaded 16 domain mappings: ['doc_metadata', 'pms_work_orders', 'pms_work_order_notes', 'pms_notes', 'pms_equipment', 'pms_faults', 'pms_parts', 'pms_inventory_stock', 'pms_vessel_certificates', 'pms_receiving', 'email_messages', 'pms_shopping_list_items', 'pms_warranty_claims', 'pms_purchase_orders', 'pms_suppliers', 'handover_items']
2026-02-22 18:48:06,322 [INFO] projection_worker - Starting worker loop...
2026-02-22 18:48:06,449 [INFO] projection_worker - Final metrics: {
  "processed": 0,
  "failed": 0,
  "skipped": 0,
  "last_batch": 0,
  "timings_ms": {
    "claim": 0,
    "process": 0,
    "upsert": 0,
    "chunk": 0,
    "notify": 0
  },
  "recent_errors": []
}
Traceback (most recent call last):
  File "/opt/render/project/src/apps/api/workers/projection_worker.py", line 900, in <module>
    run_worker()
    ~~~~~~~~~~^^
  File "/opt/render/project/src/apps/api/workers/projection_worker.py", line 771, in run_worker
    items = claim_batch(cur)
  File "/opt/render/project/src/apps/api/workers/projection_worker.py", line 642, in claim_batch
    cur.execute(query, params)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/psycopg2/extras.py", line 236, in execute
    return super().execute(query, vars)
           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
psycopg2.errors.UndefinedColumn: column "embedding_status" does not exist
LINE 7:             WHERE embedding_status IN ('pending', 'processin...
                          ^

=====
### embedding worker
Traceback (most recent call last):
  File "/opt/render/project/src/apps/api/workers/embedding_worker_1536.py", line 800, in <module>
    sys.exit(main())
             ~~~~^^
  File "/opt/render/project/src/apps/api/workers/embedding_worker_1536.py", line 735, in main
Menu
    sleep_time = min(BATCH_SLEEP_SEC * (2 ** empty_batches), 30)
                     ~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~~
OverflowError: int too large to convert to float
==> Running 'python embedding_worker_1536.py'
2026-02-23 12:22:42,976 [INFO] Embedding worker 1536 starting
2026-02-23 12:22:42,976 [INFO]   Worker ID:  worker-17afbcc7
2026-02-23 12:22:42,976 [INFO]   Model:      text-embedding-3-small
2026-02-23 12:22:42,976 [INFO]   Dimensions: 1536
2026-02-23 12:22:42,976 [INFO]   Version:    3
2026-02-23 12:22:42,976 [INFO]   Batch size: 100
2026-02-23 12:22:44,652 [INFO] Initializing OpenAI client (model=text-embedding-3-small, dims=1536)
2026-02-23 12:22:44,884 [INFO] Connecting to database...
2026-02-23 12:22:45,511 [INFO] Search index stats: total=12063, with_1536=12062, needs=2, coverage=100.0%
2026-02-23 12:22:45,616 [INFO] Job queue stats: queued=0, processing=59, done=4660, failed=0
2026-02-23 12:22:45,616 [INFO] Starting worker loop...



=====
###