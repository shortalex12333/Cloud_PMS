celeste/
  api/
    app.py
    config/
      settings.py
      feature_flags.py

    contracts/
      search_response.py          # Pydantic: final response contract (orientation, lanes, rows, actions)
      action_payloads.py          # Pydantic: execute payloads + diff preview schema
      audit_events.py             # Pydantic: audit log event schema

    search/
      pipeline/
        __init__.py
        interpret.py              # intent + entity grounding + situation mapping
        candidate_generation.py   # SQL candidate fetch (by lane/domain)
        ranking.py                # scoring + ordering, outputs lane-ranked results
        attach_actions.py         # calls microactions engine to attach primary + dropdown actions
        assemble_response.py      # builds SearchResponse contract, stream-ready
      explain/
        trace.py                  # debug trace builder (scores, entities, assumptions)
        serializers.py

    actions/
      registry/
        __init__.py
        action_registry.json      # canonical action list (single source of truth)
        loader.py                 # load/validate registry into memory
        schema.py                 # ActionDefinition dataclass / pydantic
        validators.py             # collision checks, required_context checks

      gating/
        __init__.py
        permission_gate.py        # role/scope/yacht rules
        context_gate.py           # required_context present?
        risk_gate.py              # preview/signature required?
        contradiction_gate.py     # state contradictions / forbidden combos
        gate_result.py            # enable/disable + reason codes

      attachment/
        __init__.py
        primary_action_resolver.py  # choose 1 visible action per row (usually READ)
        dropdown_builder.py         # build "v" menu items (verbs)
        action_packager.py          # output actions in UI-ready format

      execution/
        __init__.py
        execute_router.py         # dispatch by action_id
        read_handlers/            # READ actions
          open_item.py
          view_document_section.py
          print_item.py
          share_item.py
          compare_items.py
        mutate_handlers/          # MUTATE actions
          update_inventory.py
          create_work_order.py
          add_work_order_note.py
          sign_hours_of_rest.py
        preview/
          diff_builder.py         # compute exact delta pre-commit
          dry_run.py              # optional: simulate mutations safely

      signatures/
        __init__.py
        signature_service.py      # create/verify signatures (stub MVP)
        device_fingerprint.py     # client fingerprint validation rules

      audit/
        __init__.py
        audit_logger.py           # append-only write to action_log
        audit_reader.py
        models.py                 # action_log + signatures models

    renderers/
      __init__.py
      registry.py                # which renderer per lane/domain
      inventory_table.py         # returns UI blocks for inventory view
      manuals_viewer.py          # returns UI blocks anchored to manual section
      maintenance_timeline.py    # returns UI blocks for history
      hor_ledger.py              # returns UI blocks for hours-of-rest

    db/
      migrations/
        001_init.sql
        002_action_log.sql
        003_signatures.sql
        004_mutation_columns.sql
      models/
        inventory.py
        work_orders.py
        manuals.py
        hor.py
      queries/
        inventory_queries.py
        wo_queries.py
        manuals_queries.py
        hor_queries.py
      connection.py

    observability/
      logging.py                 # structured logs
      metrics.py                 # counters: action_clicks, cancels, fails, latency
      tracing.py                 # request_id / correlation id plumbing

    tests/
      unit/
        test_action_registry.py
        test_gating.py
        test_primary_action_resolver.py
        test_diff_builder.py
      integration/
        test_search_pipeline.py
        test_execute_mutations.py
        test_audit_log_append_only.py
      golden/
        queries.json             # messy real queries
        expected_actions.json    # expected microactions + gating
        expected_lanes.json      # expected primary lane + ordering

  client/
    shared/
      contracts/                 # shared TypeScript types (mirrors api/contracts)
      state_machine/
        states.ts                # idle/interpreting/rendering/row_open/etc
        transitions.ts
      components/
        SearchBar.tsx
        UnderstoodLine.tsx       # entity extraction visible beneath bar
        ResultsList.tsx
        RowActions.tsx           # primary action + dropdown arrow
        DropdownMenu.tsx         # Contact Us pattern
        StatusLine.tsx           # "Loading..." / "Saving..." / "Cancelled"
        MutationDiffPreview.tsx  # shows exact delta before signature
      renderers/
        InventoryTable.tsx
        ManualsViewer.tsx
        MaintenanceTimeline.tsx
        HorLedger.tsx

    mobile/
      screens/
        SearchScreen.tsx
      navigation/

    desktop/
      pages/
        SearchPage.tsx

  docs/
    ARCHITECTURE.md
    ACTIONS.md                   # registry rules, read vs mutate, gating
    UX_STATE_MACHINE.md          # states + transitions
    SECURITY.md                  # signature + audit + permissions

  scripts/
    seed_test_data.py
    run_golden_tests.py

