⏺ Education: What I Was Working On, The Faults, and What I Learned

  ---
  What This Sprint Was

  The codebase has an E2E (end-to-end) test suite. Many tests had "advisory" assertions — instead of expect(result.status).toBe(200)
  (exact), they said expect([200, 409, 500]).toContain(result.status) (any of these is fine). That loose tolerance existed because the
  backend had known bugs. The sprint goal: fix the backend bugs, then tighten the assertions back to exact values.

  Comments in the tests read:
  // REMOVE THIS ADVISORY WHEN: [condition describing the fix needed]
  Those were the roadmap.

  ---
  The Bugs — Why They Occurred and What I Learned

  ---
  Bug 1: HTTPException Swallowing (4 handlers)

  Files: hours_of_rest_handlers.py, document_handlers.py

  What was happening:
  try:
      # ... some logic ...
      raise HTTPException(status_code=404, detail="Not found")  # ← THIS
  except Exception as e:      # ← catches HTTPException!
      builder.set_error("INTERNAL_ERROR", str(e))  # ← wrong error
      return builder.build()   # ← returns 500 or 200+success:false instead of 404

  Why it occurs: In Python, HTTPException (the FastAPI/Starlette error class) inherits from Python's base Exception class. So except
  Exception catches everything, including deliberately raised HTTP errors. The developer intended HTTPException(404) to propagate up to
  FastAPI and become an HTTP 404 response. Instead, the outer try/except intercepted it and converted it to a generic 500 error.

  What I wish I knew: The route dispatch layer (the code that calls these handlers) already has:
  except HTTPException:
      raise  # re-raises properly
  except Exception as e:
      raise HTTPException(status_code=500, ...)
  So if HTTPException escapes the handler, it propagates correctly. The bug was that the try/except Exception inside the handler itself
  swallowed it before it could escape.

  The fix: Replace every raise HTTPException(404) inside a try block with builder.set_error("NOT_FOUND") + return builder.build(). The
  ResponseBuilder uses a lookup table to convert NOT_FOUND → HTTP 404 correctly via a different path.

  Concern: This is a systemic pattern. Any handler that raises HTTPException inside a broad try/except has this bug. I fixed four
  specific handlers but there could be others.

  ---
  Bug 2: Supabase INSERT Returns Empty Data (1 handler)

  File: part_handlers.py — add_to_shopping_list

  What was happening:
  result = self.db.table("pms_shopping_list_items").insert(item_data).execute()
  if not result.data:           # ← result.data is [] even on success!
      raise Exception("Failed to add to shopping list")

  Why it occurs: The Supabase Python client changed behavior in newer versions. Previously, .execute() after .insert() returned the
  inserted row. In newer versions, it returns an empty list [] unless you chain .select() to explicitly request the row back. The code
  was written against the old behavior.

  The fix: Chain .select("id") to explicitly request the row:
  result = self.db.table("pms_shopping_list_items").insert(item_data).select("id").execute()

  What I wish I knew: This is a silent breaking change. The INSERT succeeds in the database — data IS written — but the Python code
  thinks it failed because the response is empty. Very easy to miss.

  ---
  Bug 3: RPC Returning 204 No-Content (1 handler)

  File: shopping_list_handlers.py — create_shopping_list_item

  What was happening: When creating a shopping list item for a known part (one that already exists in the parts catalog), the database
  function (RPC) would sometimes return HTTP 204 (No Content) instead of HTTP 200 with the created row. The handler then treated empty
  data as failure and returned an error.

  Why it occurs: PostgREST (the Supabase REST layer) mediates between the Python client and the database. When it calls a database
  function, it sometimes returns 204 instead of the row data. The exact cause is complex — possibly related to how the authentication
  context interacts with the function's return path. The database function itself works fine (direct SQL queries confirm this). The
  issue is in the REST API layer.

  The fix: Added a fallback: if the RPC returns no data (204), do a direct SELECT on the table to find the just-inserted item, using
  creation time and part name as a filter.

  Unanswered question: Was this bug still actively occurring, or had it been silently fixed in a PostgREST version update? We couldn't
  run the tests to confirm. The fallback is defensive — it handles both "was broken, now works via fallback" and "was broken, is now
  fixed by PostgREST version" without harm.

  ---
  Bug 4: Data Model Split — consume_part (stale advisory)

  Files: Test files shard-35, shard-44

  What was thought to be happening: The advisory said consume_part was checking stock from an old "legacy column"
  (pms_parts.quantity_on_hand) while receives were writing to a new "transaction log" (pms_inventory_transactions). This would mean a
  receive would add stock to the transaction log but consume would check the legacy number (which never updated), always seeing zero.

  What I discovered: By reading the actual handler code, the fix had already been applied. The handler was already reading from the
  correct source (pms_part_stock.on_hand — which is a database view summing the transaction log). The advisory annotation in the test
  just hadn't been updated. Additionally, the "DRIFT" I found in the database (407/457 stock records where the cached quantity differs
  from the transaction sum) is from historical data predating the new system, not a current runtime bug.

  What I wish I knew: Advisory comments in tests can become stale if the underlying code is fixed but the test isn't updated. Always
  check the current code before assuming the advisory is still valid.

  ---
  Bug 5: Missing Workflow Gate — sign_monthly_signoff

  File: hours_of_rest_handlers.py

  What was happening: The maritime compliance signoff process requires sequential signatures: crew member signs first, then Head of
  Department (HOD), then the master/captain. The handler wasn't enforcing this sequence — any level could sign regardless of what
  happened before.

  The fix: Added validation: check the current signoff status before accepting a signature. HOD can only sign if status is crew_signed.
  Master can only sign if status is hod_signed. Otherwise, return HTTP 400 (validation error).

  ---
  Confusing Items

  1. Two dispatch paths: The codebase has two completely different ways actions get routed to handlers — _ACTION_HANDLERS (the new Phase
   4 system) and internal_dispatcher (the old system). Some actions use one, some use the other. I initially patched internal_dispatcher
   for add_to_shopping_list, then discovered it actually routes through _ACTION_HANDLERS. Had to revert and re-approach.
  2. Three stock number sources: There are three different places in the database that can tell you "how much stock does this part have"
   — the legacy cached column (pms_parts.quantity_on_hand), the live cache column (pms_inventory_stock.quantity), and the transaction
  sum view (pms_part_stock.on_hand = sum of all transaction rows). They can disagree with each other. Understanding which one each
  function reads from required tracing across multiple files and database views.
  3. The ResponseBuilder pattern: All handlers are supposed to use a ResponseBuilder class that converts error codes (NOT_FOUND,
  VALIDATION_ERROR) to HTTP status codes via a lookup table. This is the correct way to return errors. raise HTTPException is the wrong
  way inside handlers. This pattern wasn't obvious until I traced the full dispatch path.

  ---
  Concerns and Unanswered Questions

  1. Systemic HTTPException swallowing: I fixed four specific instances, but the pattern may exist in other handlers. A full audit of
  all try/except Exception blocks containing raise HTTPException across all handlers would be valuable.
  2. Shard-47 handover tests remain advisory with very broad status code ranges [200, 400, 404, 405, 422, 500]. These depend on
  "module-level handlers" — objects initialized when the server starts that depend on a default database connection. If that connection
  isn't configured in the test environment, they always return 500. These can't be tightened without either (a) confirming the test
  environment always has that connection, or (b) refactoring those routes to use per-tenant handlers like the Phase 4 routes do.
  3. 407 drifted stock records in production: Historical stock data has quantity cache values that don't match the transaction log sums.
   These don't break current tests (because tests always do a fresh receive before consuming), but they represent a data integrity
  problem for the live system. A one-time backfill SQL query could fix this, but it wasn't in scope.
  4. consume_part with multiple stock locations: If a part has stock in multiple locations and you receive into one location but consume
   from another (or the system picks an arbitrary location with .limit(1)), the pre-check and the actual deduction can see different
  stock levels. The test works around this by always pre-receiving, but the underlying handler behavior is fragile for production use.

  ------
  CEO Summary: What Was Built, Why, and What's Next

  ---
  The Business Context

  Celeste PMS is the software platform that manages yacht crew operations — work orders, parts inventory, crew rest hours (regulatory
  compliance), document management, shopping/procurement lists, and operational handovers. The platform has a web frontend used by crew,
   backed by a Python API that handles all business logic.

  This work was a reliability sprint focused on making the automated test suite trustworthy. Trustworthy tests mean: when a test passes,
   you genuinely know the feature works. When it fails, you know something broke. Right now, many tests accept a range of outcomes
  ("this could succeed or fail, both are fine"). That's not a real safety net — it's theater.

  ---
  The Core Problem We Were Solving

  The automated test suite had a pattern called "advisory assertions." Instead of saying "this must return success," tests said "this
  can return success, or failure, or error — all are acceptable." This exists because the backend had real bugs that caused features to
  fail. Rather than leave tests failing (which looks alarming), the tests were written to accept broken behavior as valid, with comments
   marking what needed to be fixed.

  The goal: Fix the underlying backend bugs, then tighten the tests to require exactly the right behavior. A tightened test is a
  permanent quality gate — if anyone breaks that feature in future, the test will now catch it.

  ---
  What Was Actually Done

  Six backend defects were fixed across four files:

  ---
  1. "Wrong Error Type" Bug — Four places in Hours of Rest and Document handlers

  What it is in plain English: When a user asked for something that didn't exist (a document without a physical file, a compliance
  signoff record that wasn't there, a warning that had been deleted), the system was supposed to say "not found" (a clean, predictable
  error). Instead, it was saying "server error" — a much more alarming and harder-to-handle response. Any code connecting to this API
  would treat these differently.

  Why it matters: The frontend needs to distinguish "not found" from "server crashed." "Not found" is routine and handled gracefully
  (show a friendly message). "Server crashed" triggers alarm states and retry logic. When the backend sends the wrong error type, the
  frontend can behave unpredictably.

  Root cause: A Python programming pattern where a deliberate "not found" signal was accidentally caught by error-handling code meant
  for unexpected crashes. The signal was swallowed and re-classified as a crash.

  Files changed: hours_of_rest_handlers.py, document_handlers.py

  Tests tightened: Shard-46 (Hours of Rest extended) and Shard-43 (Documents/Certificates) — six assertions changed from "accept a
  range" to "must be exactly this."

  ---
  2. "Parts Receiving Update Not Reflected" Bug — Shopping list handler

  What it is in plain English: When a crew member added a part to the shopping list (procurement request), the system successfully saved
   it to the database but then immediately said "it failed." The part was genuinely added — it was in the database — but the system
  returned an error anyway, confusing crew and potentially causing duplicate procurement requests.

  Why it matters: A crew member would try to add a part, see an error, and try again. This would create duplicate shopping list entries.
   The procurement officer would then see apparent duplicate orders and have to manually deduplicate.

  Root cause: A library version change. The Supabase database client changed its behavior — after a successful database write, it
  previously returned the saved record as confirmation. In the newer version, it returns nothing (empty response). The code was checking
   for that confirmation and treating "no confirmation" as "failure."

  Files changed: part_handlers.py

  Tests tightened: Shard-35 and Shard-44 shopping actions — assertions changed from "accept success or failure" to "must succeed."

  ---
  3. "Parts Cannot Be Consumed" Bug — Parts consumption handler

  What it is in plain English: When crew tried to consume (use up) a part for a maintenance job, the system would sometimes refuse with
  "insufficient stock" even when stock clearly existed. Parts had been received and were physically present, but the system couldn't see
   them when checking if a consumption was allowed.

  Why it matters: Crew are blocked from logging part consumption against work orders, creating a gap between physical reality (part
  used) and the digital record (system says stock still there). This leads to inventory inaccuracies.

  What was discovered: This bug had already been fixed by a previous developer — the handler code was reading stock correctly. The
  test's advisory comment was stale. No backend change was needed; only the test assertion needed tightening to reflect the actual
  working state.

  Files changed: Test files only (Shard-35 and Shard-44)

  ---
  4. "Creating Shopping Items Returns False Error" Bug — Shopping list RPC

  What it is in plain English: When creating a shopping list item for a part that was already known to the system (versus an "unknown"
  candidate part), the database operation succeeded but the API layer returned an error. The same "the write worked but we got no
  confirmation" category as Bug 2, but via a different technical path (a database stored procedure rather than direct table access).

  Root cause: The database's REST interface sometimes returns "204 No Content" (a valid HTTP response meaning "done, nothing to return")
   instead of returning the created record. The code treated "nothing returned" as "it failed."

  Fix: Added a safety net — if the database returns nothing, fall back to directly querying the database for the just-created item, then
   return that.

  Files changed: shopping_list_handlers.py, test Shard-35

  ---
  5. "Anyone Can Sign Anything" Bug — Monthly signoff workflow

  What it is in plain English: Maritime regulations (MLC 2006, STCW) require that monthly crew rest hour records are signed in a
  specific sequence: the crew member signs first, then their department head, then the captain. This sequential requirement was not
  enforced — any level of officer could sign regardless of what stage the process was at.

  Why it matters: This is a regulatory compliance issue. Incorrectly ordered signatures could invalidate the compliance record,
  potentially exposing the vessel to flag state inspections, port state control detentions, or crew welfare violations.

  Files changed: hours_of_rest_handlers.py

  Tests tightened: Shard-37 (Hours of Rest core actions)

  ---
  Files Changed — Summary

  ┌─────────────────────────────────────────────────────────────────────┬──────────┬────────────────────────────────────────────────┐
  │                                File                                 │ Type of  │                 Why It Matters                 │
  │                                                                     │  Change  │                                                │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │                                                                     │          │ Fixed 4 defects: wrong error codes for missing │
  │ apps/api/handlers/hours_of_rest_handlers.py                         │ Edited   │  records, missing workflow sequence            │
  │                                                                     │          │ enforcement                                    │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/api/handlers/part_handlers.py                                  │ Edited   │ Fixed parts shopping add: false failure on     │
  │                                                                     │          │ successful database write                      │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/api/handlers/shopping_list_handlers.py                         │ Edited   │ Added database fallback when REST layer        │
  │                                                                     │          │ returns no data after successful write         │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/api/handlers/document_handlers.py                              │ Edited   │ Fixed wrong error code when document file not  │
  │                                                                     │          │ in storage                                     │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/web/e2e/shard-35-shopping-parts/part-mutation-actions.spec.ts  │ Edited   │ Tightened consume_part and                     │
  │                                                                     │          │ add_to_shopping_list assertions                │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/web/e2e/shard-35-shopping-parts/shopping-list-actions.spec.ts  │ Edited   │ Tightened create_shopping_list_item assertion  │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/web/e2e/shard-37-hours-of-rest/hor-actions.spec.ts             │ Edited   │ Tightened sign_monthly_signoff assertion       │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/web/e2e/shard-43-docs-certs/docs-certs-actions.spec.ts         │ Edited   │ Tightened get_document_url assertion           │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │ apps/web/e2e/shard-44-parts-shopping/parts-shopping-actions.spec.ts │ Edited   │ Tightened consume_part and                     │
  │                                                                     │          │ add_to_shopping_list assertions                │
  ├─────────────────────────────────────────────────────────────────────┼──────────┼────────────────────────────────────────────────┤
  │                                                                     │          │ Tightened acknowledge_warning,                 │
  │ apps/web/e2e/shard-46-hor-extended/hor-extended-actions.spec.ts     │ Edited   │ dismiss_warning, get_monthly_signoff           │
  │                                                                     │          │ assertions                                     │
  └─────────────────────────────────────────────────────────────────────┴──────────┴────────────────────────────────────────────────┘

  ---
  Risks and Open Issues

  1. Untested Fixes
  None of these fixes have been run through the full test suite yet. The code changes are logically sound based on reading the source,
  but automated test execution is required to confirm. This is the single highest-priority next step.

  2. Systemic Pattern May Affect Other Features
  The "wrong error code" bug (where a deliberate error signal gets swallowed by generic error handling) was found in four places. The
  same coding pattern may exist in other handlers across the codebase that weren't examined in this sprint. A systematic audit of all
  API handlers would provide confidence there are no more lurking instances.

  3. Handover Feature Tests Still Advisory
  The handover management feature (shard-47) still has very broad advisory tests. These couldn't be tightened because they depend on
  initialization conditions that vary by environment. The handover feature's reliability as measured by automated tests remains
  uncertain.

  4. Historical Stock Data Inconsistency
  407 out of 457 stock records in the production database have a mismatch between their cached quantity and their transaction history.
  This is from data predating the current inventory system. It doesn't break current tests (which always do fresh operations), but it
  means the inventory displayed to crew for these parts may be inaccurate. A one-time data correction query would resolve this — it
  should be scheduled.

  5. Procurement Duplicate Risk Remains
  The false-error-on-shopping-list-add bug was fixed, but any duplicates already created in the database from before the fix are still
  there. A data cleanup may be warranted.

  ---
  What Should Happen Next

  1. Run the full test suite — deploy the backend changes to the test environment and execute all affected shards (35, 37, 43, 44, 46)
  to confirm the tightened assertions pass.
  2. Audit remaining handlers — systematically check all API handlers for the "HTTPException inside try/except Exception" pattern and
  fix any instances found.
  3. Fix handover tests — investigate and resolve the initialization dependency that prevents the handover tests from being reliable.
  4. Stock data backfill — run a corrective query to synchronize the 407 drifted inventory records, ensuring crew see accurate stock
  levels.
  5. Commit and deploy — once tests confirm green, merge and deploy these backend fixes to production to resolve the user-facing issues
  (false failures on shopping list adds, wrong errors on document/compliance lookups).

