# Test Plan

## Acceptance Criteria and Test Cases

This document defines the test scenarios for validating the Handover Export System.

---

## Test Categories

1. **Unit Tests** - Individual service methods
2. **Integration Tests** - Service interactions
3. **RLS Tests** - Multi-tenant isolation
4. **E2E Tests** - Full user journeys
5. **Edge Cases** - Error handling

---

## Unit Tests

### Draft Generator Service

```python
class TestDraftGeneratorService:

    async def test_generate_draft_creates_record(self):
        """Draft generation creates handover_drafts record."""
        service = DraftGeneratorService(db)
        draft_id = await service.generate_draft(
            yacht_id="test-yacht",
            user_id="test-user",
            period_start=datetime(2026, 2, 1),
            period_end=datetime(2026, 2, 1)
        )
        assert draft_id is not None

        draft = await db.table("handover_drafts").select("*").eq("id", draft_id).single().execute()
        assert draft.data["state"] == "DRAFT"
        assert draft.data["yacht_id"] == "test-yacht"

    async def test_generate_draft_groups_by_bucket(self):
        """Items are grouped into correct presentation buckets."""
        # Setup: Create items with different entity types
        # ...
        draft_id = await service.generate_draft(...)

        sections = await db.table("handover_draft_sections").select("*").eq("draft_id", draft_id).execute()
        assert len(sections.data) > 0

        # Verify Engineering items in Engineering section
        engineering_section = next(s for s in sections.data if s["bucket_name"] == "Engineering")
        assert engineering_section is not None

    async def test_generate_draft_returns_existing_if_draft_exists(self):
        """Returns existing draft instead of creating duplicate."""
        draft_id_1 = await service.generate_draft(yacht_id="test", user_id="user1", ...)
        draft_id_2 = await service.generate_draft(yacht_id="test", user_id="user1", ...)

        assert draft_id_1 == draft_id_2

    async def test_generate_draft_rejects_if_signed_exists(self):
        """Cannot generate new draft if SIGNED draft exists for period."""
        # Create and sign a draft
        draft_id = await service.generate_draft(...)
        await signoff_service.accept_draft(draft_id, user_id)
        await signoff_service.sign_draft(draft_id, other_user_id)

        # Attempt to generate new draft for same period should fail
        with pytest.raises(ValueError, match="SIGNED draft exists"):
            await service.generate_draft(...)
```

---

### Export Service

```python
class TestExportService:

    async def test_export_generates_html(self):
        """Export generates valid HTML document."""
        service = HandoverExportService(db)
        result = await service.generate_export(
            yacht_id="test-yacht",
            user_id="test-user",
            export_type="html"
        )

        assert result.html is not None
        assert "<html" in result.html
        assert "HANDOVER REPORT" in result.html
        assert result.document_hash is not None

    async def test_export_includes_hyperlinks(self):
        """Exported HTML contains hyperlinks to entities."""
        # Setup: Create items with entity references
        # ...
        result = await service.generate_export(...)

        assert 'href="https://app.celeste7.ai/faults/' in result.html
        assert 'class="entity-link"' in result.html

    async def test_export_creates_record(self):
        """Export creates handover_exports record."""
        result = await service.generate_export(...)

        export = await db.table("handover_exports").select("*").eq("id", result.export_id).single().execute()
        assert export.data is not None
        assert export.data["document_hash"] == result.document_hash

    async def test_export_empty_returns_no_items_message(self):
        """Export with no items returns appropriate message."""
        result = await service.generate_export(yacht_id="empty-yacht", ...)

        assert result.total_items == 0
        assert "No Handover Items" in result.html
```

---

### Signoff Service

```python
class TestSignoffService:

    async def test_accept_transitions_to_accepted(self):
        """Accept moves draft from IN_REVIEW to ACCEPTED."""
        draft_id = await create_draft_in_review()

        result = await signoff_service.accept_draft(draft_id, user_id)

        draft = await db.table("handover_drafts").select("*").eq("id", draft_id).single().execute()
        assert draft.data["state"] == "ACCEPTED"

    async def test_accept_requires_in_review_state(self):
        """Accept fails if draft not in IN_REVIEW state."""
        draft_id = await create_draft()  # In DRAFT state

        with pytest.raises(ValueError, match="Invalid state transition"):
            await signoff_service.accept_draft(draft_id, user_id)

    async def test_sign_requires_different_user(self):
        """Countersign must be different user from accept."""
        draft_id = await create_draft_in_review()
        await signoff_service.accept_draft(draft_id, user_id="user1")

        with pytest.raises(ValueError, match="different user"):
            await signoff_service.sign_draft(draft_id, user_id="user1")

    async def test_sign_creates_signoff_record(self):
        """Sign creates handover_signoffs record with hash."""
        draft_id = await create_accepted_draft(outgoing_user="user1")

        result = await signoff_service.sign_draft(draft_id, user_id="user2")

        signoff = await db.table("handover_signoffs").select("*").eq("draft_id", draft_id).single().execute()
        assert signoff.data["outgoing_user_id"] == "user1"
        assert signoff.data["incoming_user_id"] == "user2"
        assert signoff.data["document_hash"] is not None

    async def test_sign_locks_draft(self):
        """After sign, draft cannot be modified."""
        draft_id = await create_signed_draft()

        with pytest.raises(ValueError, match="Cannot modify signed draft"):
            await draft_service.edit_item(draft_id, item_id, "new text")
```

---

## Integration Tests

### Full Draft → Export Flow

```python
class TestFullWorkflow:

    async def test_add_to_handover_through_export(self):
        """
        Complete workflow:
        1. Add items via add_to_handover action
        2. Generate draft
        3. Review and edit
        4. Accept (outgoing)
        5. Sign (incoming)
        6. Export PDF
        """
        # 1. Add items
        await execute_action("add_to_handover", {
            "entity_type": "fault",
            "entity_id": fault_id,
            "summary_text": "Generator cooling issue"
        })

        # 2. Generate draft
        draft_id = await draft_service.generate_draft(yacht_id, user_id, ...)

        # 3. Review
        await draft_service.enter_review(draft_id)
        await draft_service.edit_item(draft_id, item_id, "Updated: Generator cooling issue resolved")

        # 4. Accept
        await signoff_service.accept_draft(draft_id, outgoing_user_id)

        # 5. Sign
        await signoff_service.sign_draft(draft_id, incoming_user_id)

        # 6. Export
        result = await export_service.export_draft(draft_id, "pdf")

        # Verify
        assert result.export_type == "pdf"
        assert result.storage_path.endswith(".pdf")

        # Download and verify PDF
        content = await storage.download(result.storage_path)
        assert content[:4] == b'%PDF'
```

---

### Import from Legacy

```python
class TestImportWorkflow:

    async def test_import_from_legacy_handover(self):
        """Import existing handovers + handover_items into draft."""
        # Setup: Create legacy handover with items
        handover_id = await create_legacy_handover_with_items(item_count=5)

        # Import
        draft_id = await import_service.import_from_legacy(
            handover_id=handover_id,
            yacht_id=yacht_id,
            user_id=user_id
        )

        # Verify
        draft = await db.table("handover_drafts").select("*").eq("id", draft_id).single().execute()
        assert draft.data["total_entries"] == 5
        assert "imported_from" in draft.data["metadata"]

        items = await db.table("handover_draft_items").select("*").eq("draft_id", draft_id).execute()
        assert len(items.data) == 5

    async def test_import_preserves_source_references(self):
        """Imported items retain source_entry_ids pointing to original."""
        draft_id = await import_service.import_from_legacy(handover_id, ...)

        items = await db.table("handover_draft_items").select("*").eq("draft_id", draft_id).execute()
        for item in items.data:
            assert len(item["source_entry_ids"]) > 0
```

---

## RLS Tests

### Multi-Tenant Isolation

```python
class TestRLSIsolation:

    async def test_user_cannot_see_other_yacht_handovers(self):
        """User A cannot see User B's handovers (different yachts)."""
        # Setup: Create handovers for yacht A and yacht B
        handover_a = await create_handover(yacht_id="yacht-a")
        handover_b = await create_handover(yacht_id="yacht-b")

        # Query as user from yacht A
        client_a = get_client_for_user("user-yacht-a")
        result = await client_a.table("handovers").select("*").execute()

        # Should only see yacht A handovers
        ids = [h["id"] for h in result.data]
        assert handover_a in ids
        assert handover_b not in ids

    async def test_user_cannot_see_other_yacht_drafts(self):
        """User cannot access drafts from another yacht."""
        draft_b = await create_draft(yacht_id="yacht-b")

        client_a = get_client_for_user("user-yacht-a")
        result = await client_a.table("handover_drafts").select("*").eq("id", draft_b).execute()

        assert len(result.data) == 0

    async def test_unified_view_respects_rls(self):
        """v_handover_export_items respects yacht isolation."""
        # Create items for both yachts
        await create_handover_item(yacht_id="yacht-a")
        await create_handover_item(yacht_id="yacht-b")
        await create_pms_handover(yacht_id="yacht-a")
        await create_pms_handover(yacht_id="yacht-b")

        # Query as user from yacht A
        client_a = get_client_for_user("user-yacht-a")
        result = await client_a.table("v_handover_export_items").select("*").execute()

        # All items should be from yacht A
        for item in result.data:
            assert item["yacht_id"] == "yacht-a"

    async def test_service_role_bypasses_rls(self):
        """Service role can access all yachts."""
        service_client = get_service_role_client()

        result = await service_client.table("handovers").select("*").execute()

        # Should see all yachts
        yacht_ids = set(h["yacht_id"] for h in result.data)
        assert len(yacht_ids) > 1
```

---

### Immutability Tests

```python
class TestImmutability:

    async def test_cannot_delete_signed_draft(self):
        """Signed drafts cannot be deleted."""
        draft_id = await create_signed_draft()

        with pytest.raises(Exception):  # Permission denied
            await db.table("handover_drafts").delete().eq("id", draft_id).execute()

    async def test_cannot_modify_signoff_record(self):
        """Signoff records are immutable."""
        signoff = await create_signoff()

        with pytest.raises(Exception):
            await db.table("handover_signoffs").update({"document_hash": "tampered"}).eq("id", signoff["id"]).execute()

    async def test_cannot_delete_edit_history(self):
        """Edit history cannot be deleted."""
        edit = await create_draft_edit()

        with pytest.raises(Exception):
            await db.table("handover_draft_edits").delete().eq("id", edit["id"]).execute()
```

---

## E2E Test Scenarios

### Scenario 1: Chief Engineer Day Handover

```gherkin
Feature: Chief Engineer Day Handover

Scenario: Complete day shift handover
    Given Chief Engineer "John" is logged in
    And there are 5 handover items from the day shift
    When John creates a handover draft for today
    Then the draft contains 5 items grouped by section

    When John reviews the draft and edits "Generator cooling" to "Generator cooling - resolved"
    Then the edit is recorded in draft history

    When John accepts the draft
    Then the draft state is "ACCEPTED"
    And John is recorded as outgoing officer

    Given 2nd Engineer "Jane" is logged in
    When Jane countersigns the draft
    Then the draft state is "SIGNED"
    And Jane is recorded as incoming officer
    And a document hash is generated

    When John exports the draft as PDF
    Then a PDF is generated with hyperlinks
    And the PDF is stored in Supabase Storage
    And an export record is created
```

---

### Scenario 2: Email-Sourced Handover

```gherkin
Feature: Email-Sourced Handover

Scenario: Handover from email classification
    Given emails have been processed by email pipeline
    And 3 emails are classified for handover
    When user generates handover draft
    Then draft includes email-sourced items
    And items contain Outlook deep links

    When exported as HTML
    Then email links are clickable
    And link to original Outlook messages
```

---

### Scenario 3: Multi-Department Handover

```gherkin
Feature: Multi-Department Handover

Scenario: Captain reviews all departments
    Given Captain is logged in
    And there are items in Engineering, Deck, and Interior
    When Captain generates handover draft
    Then draft contains all three sections
    And sections are ordered correctly

    When Captain exports the draft
    Then PDF contains all sections
    And section headers are visible
```

---

## Performance Tests

```python
class TestPerformance:

    async def test_export_performance_100_items(self):
        """Export with 100 items completes in < 5 seconds."""
        # Setup: Create draft with 100 items
        draft_id = await create_draft_with_items(item_count=100)

        start = time.time()
        result = await export_service.generate_export(draft_id=draft_id, ...)
        elapsed = time.time() - start

        assert elapsed < 5.0
        assert result.total_items == 100

    async def test_pdf_generation_performance(self):
        """PDF generation completes in < 10 seconds."""
        html = generate_large_html()

        start = time.time()
        pdf_path = await pdf_generator.generate(html, "/tmp/test.pdf")
        elapsed = time.time() - start

        assert elapsed < 10.0
        assert os.path.exists(pdf_path)
```

---

## Acceptance Criteria Summary

| Criterion | Test | Status |
|-----------|------|--------|
| Draft generation from items | `test_generate_draft_creates_record` | ⏳ |
| Items grouped by bucket | `test_generate_draft_groups_by_bucket` | ⏳ |
| State machine enforcement | `test_accept_requires_in_review_state` | ⏳ |
| Dual sign-off required | `test_sign_requires_different_user` | ⏳ |
| Document hash on sign | `test_sign_creates_signoff_record` | ⏳ |
| Export generates HTML | `test_export_generates_html` | ⏳ |
| Export includes hyperlinks | `test_export_includes_hyperlinks` | ⏳ |
| RLS yacht isolation | `test_user_cannot_see_other_yacht_handovers` | ⏳ |
| Signed drafts immutable | `test_cannot_delete_signed_draft` | ⏳ |
| Import preserves sources | `test_import_preserves_source_references` | ⏳ |

---
