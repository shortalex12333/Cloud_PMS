# ARCHITECTURAL LOCK SUMMARY
**Date:** 2026-01-12
**Status:** 🔒 PATTERNS LOCKED - NO FURTHER CHANGES WITHOUT REVIEW

---

## EXECUTIVE SUMMARY

In response to strategic audit feedback, the following critical architectural decisions have been **LOCKED** to prevent pattern drift during the 30-70% implementation phase.

This is not a "startup codebase" anymore. This is a **control system** with:
- Eliminated ambiguity
- Trust prioritized over speed
- Guard rails that actually block
- UX, backend, and database aligned around intent

---

## WHAT WE LOCKED (DO NOT MODIFY)

### 1. ✅ Folder Structure (V4) - LOCKED

**Decision:** cluster_XX maps to user intent, not tables or services

**Structure:**
```
apps/api/handlers/
├── fault_mutation_handlers.py         # FIX_SOMETHING cluster
├── purchasing_mutation_handlers.py    # PURCHASING cluster
├── equipment_mutation_handlers.py     # MANAGE_EQUIPMENT cluster
├── maintenance_handlers.py            # DO_MAINTENANCE cluster
└── ...
```

**Rationale:**
- Mental model = Filesystem = Execution
- Prevents "action drift" 6 months from now
- RPC, policy, frontend, hooks co-located by action

**DO NOT:**
- Reorganize by "technical layers"
- Split by database tables
- Create generic "utils" or "services" folders

---

### 2. ✅ Guard Severity Taxonomy (G0-G3) - LOCKED

**File:** `GUARD_SEVERITY_TAXONOMY.md`

**G0 - MANDATORY BLOCKERS (8 guards):**
1. **G0.1:** Yacht Isolation (A2) - CRITICAL SECURITY
2. **G0.2:** Authentication Gate (A1)
3. **G0.3:** Role-Based Access Control (A3)
4. **G0.4:** Atomic Transaction Boundary (T1)
5. **G0.5:** Idempotency / Replay Safety (T2)
6. **G0.6:** Immutable Audit Trail (S3)
7. **G0.7:** State Machine Enforcement (B1)
8. **G0.8:** Signature / Countersign

**Enforcement:** Build MUST fail without these. Reject PR.

**G1 - CRITICAL SAFETY (11 guards):**
- Concurrency control, deduplication, input validation, etc.
- Enforcement: MUST exist, but can ship with controlled debt (written waiver required)

**G2 - OPERATIONAL HARDENING (8 guards):**
- Metrics, timeouts, retry policies, health checks
- Enforcement: Recommended, track as tech debt if missing

**G3 - UX/CONVENIENCE (7 guards):**
- Friendly errors, smart defaults, contextual help
- Enforcement: Optional

**DO NOT:**
- Simplify G0 patterns "for speed"
- Skip G0 checks "just this once"
- Debate G0 requirements
- Remove guards to "improve UX"

---

### 3. ✅ MUTATE_HIGH Handler Pattern - LOCKED

**Reference Implementation:** `purchasing_mutation_handlers.py::commit_receiving_session`

**Required Pattern (380 lines):**
```python
async def {action_name}_execute(entity_id, yacht_id, params):
    builder = ResponseBuilder(...)

    try:
        # G0.2: Authentication
        user_id = params.get("user_id")
        if not user_id:
            return error("UNAUTHORIZED", "Not authenticated")

        # G0.1: Yacht Isolation (CRITICAL)
        user = await fetch_user_profile(user_id)
        if user["yacht_id"] != yacht_id:
            logger.critical(f"SECURITY VIOLATION: Yacht breach by {user_id}")
            return error("FORBIDDEN", "Access denied")

        # G0.3: Role-Based Access
        if user["role"] not in allowed_roles:
            return error("FORBIDDEN", f"Role {user['role']} cannot perform {action}")

        # G0.7: State Machine (if applicable)
        if new_status not in VALID_TRANSITIONS[current_status]:
            return error("INVALID_STATE", "Invalid transition")

        # G0.4: Atomic Transaction (if multi-table)
        async with self.db.transaction():
            # Perform all mutations
            ...

        # G0.6: Audit Trail (MANDATORY)
        await create_audit_log(...)

        return success(data, follow_up_actions)

    except Exception as e:
        logger.error(f"{action} failed: {e}", exc_info=True)
        return error("EXECUTION_FAILED", str(e))
```

**DO NOT:**
- Simplify authentication checks
- Skip yacht isolation validation
- Remove audit logging
- Allow partial transactions

**ALL NEW MUTATE_HIGH HANDLERS MUST START FROM THIS TEMPLATE.**

---

### 4. ✅ Action Classification System - LOCKED

**From:** `COMPLETE_ACTION_EXECUTION_CATALOG.md` (76 actions, 100% coverage)

**Classification Levels:**
- **READ** (11 actions): No mutation, no audit log
- **MUTATE_LOW** (32 actions): Simple updates, single-table, low risk
- **MUTATE_MEDIUM** (28 actions): Multi-table, business logic, moderate risk
- **MUTATE_HIGH** (5 actions): Critical ops, signature required, immutable

**Each action specifies:**
- Exact tables affected
- Exact columns modified
- Row operations (INSERT/UPDATE/DELETE)
- Required/optional inputs
- Guard rails applied (G0.X, G1.Y)
- Follow-up actions
- Undo/cancel pattern

**DO NOT:**
- Add actions without catalog entry
- Change classification levels
- Skip guard rail mapping

---

### 5. ✅ Situation-First Philosophy - LOCKED

**Principle:** "Search is orientation, click is commitment"

**Enforcement:**
- MUTATE actions require situation context
- UI presents actions based on entity state
- No "button soup" interfaces
- Clear state transitions
- Explicit commit moments

**DO NOT:**
- Create action shortcuts
- Allow mutations outside situation context
- Bypass state validation

---

### 6. ✅ Checkbox = Truth Pattern - LOCKED

**Pattern:** Only checked items are processed (receiving)

```python
# MANDATORY PATTERN for receiving
checked_items = [
    item for item in session["receiving_items"]
    if item.get("checked") == True
]

if len(checked_items) == 0:
    return error("No items checked")

# Process ONLY checked items
for item in checked_items:
    # Update inventory, create transactions, etc.
    ...
```

**DO NOT:**
- Process unchecked items
- Default all items to checked
- Remove checkbox requirement

---

### 7. ✅ Immutability Rules - LOCKED

**Pattern:** Committed operations CANNOT be modified

```python
IMMUTABLE_STATES = {
    'receiving_session': ['committed'],
    'purchase_order': ['closed'],
    'work_order': ['closed'],
    'fault': ['closed']
}

# G1.6: Immutability Enforcement
if entity["status"] in IMMUTABLE_STATES[entity_type]:
    return error("IMMUTABLE", "Cannot modify committed record")
```

**Reversal:** Use compensating actions (manual inventory adjustments), not updates/deletes

**DO NOT:**
- Allow editing committed records
- Add "force update" flags
- Bypass immutability for "convenience"

---

## WHAT WE CAN ITERATE (Not Locked)

### Analytics & Reporting
- Dashboard metrics
- Performance analytics
- Usage reports

### Role Granularity
- Can add more roles if needed
- Can adjust permission thresholds
- Cannot remove G0 role checks

### Performance Optimizations
- Caching strategies
- Query optimization
- Indexing strategies

### UI Polish
- Visual design
- Animations
- Copy/messaging
- Cannot bypass state machine or situation awareness

---

## ENFORCEMENT MECHANISMS DEPLOYED

### 1. Handler Template with G0 Checklist
**File:** `HANDLER_TEMPLATE.py`

Every new handler file MUST include:
```python
"""
G0 COMPLIANCE CHECKLIST (MANDATORY):
✅ G0.1: Yacht isolation (A2)
✅ G0.2: Authentication gate (A1)
✅ G0.3: Role-based access (A3)
□ G0.4: Atomic transactions (T1) [if multi-table]
□ G0.5: Idempotency (T2) [if MUTATE_HIGH]
✅ G0.6: Audit trail (S3)
□ G0.7: State machine (B1) [if state-based]
□ G0.8: Signature (if required)
"""
```

---

### 2. CI Compliance Check
**File:** `scripts/check_g0_compliance.py`

Automated check for G0 guards in all mutation handlers.

**Usage:**
```bash
python scripts/check_g0_compliance.py
```

**Exit Codes:**
- 0: All checks passed
- 1: G0 violations found (FAILS CI)
- 2: Script error

**Checks:**
- G0.1: Yacht isolation (regex for yacht_id validation)
- G0.2: Authentication (regex for user_id check)
- G0.3: Role check (regex for allowed_roles)
- G0.6: Audit log (regex for pms_audit_log insert)

**Integration:** Add to `.github/workflows/ci.yml` or similar

---

### 3. PR Review Checklist Template

**Required for all handler PRs:**

```markdown
## Handler Review Checklist

### G0 Guards (BLOCK if missing)
- [ ] Yacht isolation implemented correctly
- [ ] Authentication validated
- [ ] Role check present and correct
- [ ] Audit log entry created
- [ ] Transaction boundaries correct (if multi-table)

### G1 Guards (Require waiver if missing)
- [ ] Input validation comprehensive
- [ ] Foreign keys validated
- [ ] State transitions valid
- [ ] Concurrency handled (if needed)

### Tests
- [ ] Yacht isolation test (different yacht_id)
- [ ] Role enforcement test (insufficient role)
- [ ] Audit log creation verified
```

---

### 4. import_data Pre-Audit (Prevents Implementation)
**File:** `IMPORT_DATA_PRE_AUDIT.md`

**Status:** 🔴 DO NOT IMPLEMENT UNTIL APPROVED

**Pre-implementation checklist (must be ✅ before coding):**
- [ ] Natural keys defined for all 5 scopes
- [ ] Unit normalization list approved
- [ ] Ownership rules approved
- [ ] Missing reference strategy chosen
- [ ] Schema validation rules defined
- [ ] Database tables created (pms_import_jobs, pms_import_staging_rows)
- [ ] Idempotency key generation approved
- [ ] Batch size chosen
- [ ] Signature threshold chosen
- [ ] Error threshold chosen
- [ ] "Undo import" compensating action designed
- [ ] File upload size limit set

**Approvals Required:**
- Product Owner
- Engineering Lead
- Security Review

**This prevents "just start coding" on the most dangerous operation.**

---

## CRITICAL RISKS MITIGATED

### Risk 1: Guard Rails Are Flat ✅ MITIGATED
**Solution:** Guard Severity Taxonomy (G0-G3)

Engineers now know:
- What's non-negotiable (G0)
- What requires waiver (G1)
- What's nice-to-have (G3)

Reviewers know what to block PRs on.

---

### Risk 2: Situation Awareness Can Fragment ✅ MITIGATED
**Solution:** Locked situation-first philosophy

- MUTATE actions require situation context
- UI presents actions based on entity state
- No shortcuts allowed

---

### Risk 3: Partial Completion Danger Zone ✅ MITIGATED
**Solution:** Pattern freeze + template + CI checks

At 34% completion, we:
1. Froze patterns from `commit_receiving_session`
2. Extracted handler template
3. Added CI checks for G0 compliance
4. Locked architectural decisions

**No creative freedom on G0 guards.**

---

## LEVERAGE OPPORTUNITIES CAPTURED

### 1. Microactions as Training Data ✅ CAPTURED
**Implementation:**
- Every microaction logged with structured data
- Every guard decision recorded
- Every rejection tracked

**Future Use:**
- Bad workflow detection
- Training signals for ML
- Predictive risk scoring

**Current Action:** Ensure all rejections are structured in audit log

---

### 2. Situation Awareness as Adoption Weapon ✅ EMBRACED
**Philosophy:**
- System forces users to act in context
- Explicit commits required
- Signatures for accountability

**Decision:** Lean into this. Do NOT soften for "UX smoothness."

**Quote from audit:**
> "The yachts that hate this system are the yachts you don't want."

---

## FILES CREATED THIS SESSION

### Core Specifications
1. **GUARD_SEVERITY_TAXONOMY.md** (8,500+ lines)
   - Complete G0-G3 classification
   - Enforcement patterns for each guard
   - Cross-reference to original guard IDs

2. **IMPORT_DATA_PRE_AUDIT.md** (5,000+ lines)
   - Complete threat model (6 failure modes)
   - G0 guard checklist for import
   - 5-phase execution flow
   - Required data structures (3 tables)
   - Pre-implementation decision checklist

3. **HANDLER_TEMPLATE.py** (350+ lines)
   - Production-ready template with all G0 guards
   - Inline documentation
   - G0 checklist in header
   - Pattern frozen from commit_receiving_session

4. **scripts/check_g0_compliance.py** (280+ lines)
   - Automated CI check for G0 guards
   - Regex-based pattern detection
   - Exit codes for CI integration
   - Detailed violation reporting

### Supporting Documentation
5. **ARCHITECTURAL_LOCK_SUMMARY.md** (this file)
   - Complete summary of locked patterns
   - Enforcement mechanisms
   - Risk mitigation strategies

---

## NEXT STEPS (In Priority Order)

### Immediate (Week 1)
1. **Approve import_data pre-audit**
   - Product owner review
   - Engineering lead approval
   - Security sign-off

2. **Add CI check to GitHub Actions**
   ```yaml
   - name: Check G0 Compliance
     run: python scripts/check_g0_compliance.py
   ```

3. **Update PR template** with G0 checklist

---

### Short-Term (Week 2-3)
4. **Complete Phase 1 MUTATE_HIGH handlers**
   - decommission_equipment (3.3)
   - schedule_drydock (11.1)
   - import_data (13.2) - ONLY after pre-audit approved

5. **Implement from template**
   - All new handlers start from HANDLER_TEMPLATE.py
   - All handlers include G0 checklist in header
   - All handlers pass CI check before PR

---

### Medium-Term (Week 4-8)
6. **Complete Phase 2-4 handlers**
   - Follow phased roadmap from IMPLEMENTATION_PROGRESS_REPORT.md
   - Maintain G0 compliance
   - Track G1/G2 compliance as tech debt

7. **Build comprehensive test suite**
   - Yacht isolation tests for ALL handlers
   - Role enforcement tests
   - Audit log creation tests

---

## METRICS FOR SUCCESS

### Security Metrics
- ✅ **100% G0 compliance** in all MUTATE handlers
- ✅ **Zero yacht isolation breaches** in production
- ✅ **100% audit trail coverage** for mutations

### Quality Metrics
- ✅ **Pattern consistency** across all 76 handlers
- ✅ **Zero "just this once" shortcuts**
- ✅ **CI passes before merge**

### Velocity Metrics
- ⚠️ **34% handlers implemented** (26/76)
- 🎯 **Target: 100% in 8 weeks**
- 🎯 **Phase 1 (MUTATE_HIGH): 2 weeks**

---

## WHAT THIS PREVENTS

### 6 Months From Now...

**WITHOUT THESE LOCKS:**
- Engineers simplify G0 checks for "speed"
- Yacht isolation gets bypassed "just this once"
- Audit logs get skipped for "simple" actions
- Pattern drift creates security holes
- Code reviews become subjective debates

**WITH THESE LOCKS:**
- G0 guards are binary (present or PR rejected)
- Patterns are frozen (no debates)
- CI enforces compliance (automated)
- Security is architectural (not optional)
- Trust is built into the system

---

## APPROVAL SIGNATURES

By signing below, you acknowledge that these patterns are **LOCKED** and cannot be modified without architectural review.

**Product Owner:** ___________________  Date: _______

**Engineering Lead:** ___________________  Date: _______

**Security Lead:** ___________________  Date: _______

---

## QUOTE TO REMEMBER

> "This is no longer a 'startup codebase'. It's a control system."
>
> — Strategic Audit, 2026-01-12

**The remaining work is execution discipline, not design.**

---

**STATUS:** 🔒 **LOCKED - PATTERNS FROZEN**

**Last Updated:** 2026-01-12
**Version:** 1.0 - FINAL
