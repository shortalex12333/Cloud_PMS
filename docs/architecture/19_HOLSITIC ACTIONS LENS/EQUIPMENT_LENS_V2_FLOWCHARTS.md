# Equipment Lens v2 - Visual Flowcharts

**Purpose**: Visual decision trees showing role-gated journeys, field requirements, and workflow paths.

---

## Table of Contents

1. [Master Journey Map](#1-master-journey-map)
2. [Set Equipment Status Flow](#2-set-equipment-status-flow)
3. [Decommission & Replace Flow](#3-decommission--replace-flow)
4. [Attach Image with Comment Flow](#4-attach-image-with-comment-flow)
5. [Archive/Restore Flow](#5-archiverestore-flow)
6. [Role Permission Matrix](#6-role-permission-matrix)

---

## 1. Master Journey Map

**Entry Point**: User views equipment with intent to take action

```mermaid
flowchart TD
    Start([User Views Equipment]) --> AuthCheck{Authenticated?}

    AuthCheck -->|No| Error401[401 Unauthorized]
    AuthCheck -->|Yes| RoleCheck{User Role?}

    RoleCheck -->|crew| ReadOnly[Read-Only Actions<br/>- View details<br/>- View documents<br/>- View history]

    RoleCheck -->|engineer<br/>eto| EngineerActions{What needs<br/>to be done?}

    RoleCheck -->|chief_engineer<br/>chief_officer<br/>purser<br/>HOD roles| HODActions{What needs<br/>to be done?}

    RoleCheck -->|captain<br/>manager| CaptainActions{What needs<br/>to be done?}

    %% Engineer Branch
    EngineerActions -->|Document issue| DocFlow[Attach Image<br/>with Comment]
    EngineerActions -->|Log hours| HoursFlow[Record Equipment<br/>Hours]
    EngineerActions -->|Update status| StatusFlow[Set Equipment<br/>Status]

    %% HOD Branch
    HODActions -->|Create repair| WOFlow[Create Work Order<br/>for Equipment]
    HODActions -->|Update status| StatusFlow
    HODActions -->|Add note| NoteFlow[Add Equipment<br/>Note]
    HODActions -->|Archive| ArchiveFlow[Archive Equipment<br/>MUTATE]

    %% Captain Branch
    CaptainActions -->|Permanent removal| DecomFlow[Decommission &<br/>Replace SIGNED]
    CaptainActions -->|Restore archived| RestoreFlow[Restore Archived<br/>Equipment SIGNED]
    CaptainActions -->|Any HOD action| HODActions

    %% Link to detailed flows
    StatusFlow -.->|See Flow 2| StatusDetail[Set Status Flow]
    DecomFlow -.->|See Flow 3| DecomDetail[Decommission Flow]
    DocFlow -.->|See Flow 4| DocDetail[Attach Image Flow]
    ArchiveFlow -.->|See Flow 5| ArchiveDetail[Archive Flow]
    RestoreFlow -.->|See Flow 5| RestoreDetail[Restore Flow]

    style Start fill:#e1f5ff
    style ReadOnly fill:#ffebee
    style EngineerActions fill:#fff3e0
    style HODActions fill:#f3e5f5
    style CaptainActions fill:#e8f5e9
    style StatusFlow fill:#bbdefb
    style DecomFlow fill:#ffccbc
    style DocFlow fill:#c5e1a5
    style ArchiveFlow fill:#d1c4e9
```

---

## 2. Set Equipment Status Flow

**Action**: `set_equipment_status` (MUTATE)
**Roles**: engineer, eto, chief_engineer, chief_officer, purser, captain, manager

```mermaid
flowchart TD
    Start([Set Equipment Status]) --> RoleCheck{Has HOD+<br/>permission?}

    RoleCheck -->|No crew| Error403[403 Forbidden<br/>Crew cannot write]
    RoleCheck -->|Yes| YachtCheck{Equipment<br/>belongs to<br/>user's yacht?}

    YachtCheck -->|No| Error404[404 Not Found<br/>RLS blocks access]
    YachtCheck -->|Yes| InputFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ equipment_id UUID<br/>✓ to_status enum]

    InputFields --> StatusValidate{Valid status<br/>value?}

    StatusValidate -->|No| Error400A[400 Bad Request<br/>Invalid status enum]
    StatusValidate -->|Yes| StatusCheck{to_status =<br/>'out_of_service'?}

    StatusCheck -->|No| SimpleUpdate[Update equipment.status<br/>Update equipment.updated_at<br/>Update equipment.updated_by]

    StatusCheck -->|Yes OOS| WORequired{work_order_id<br/>provided?}

    WORequired -->|No| Error400B[400 Bad Request<br/>OOS requires work_order_id]
    WORequired -->|Yes| WOValidate[Validate Work Order:<br/>1. WO exists<br/>2. WO.equipment_id matches<br/>3. WO.status in OPEN/IN_PROGRESS<br/>4. WO.yacht_id matches]

    WOValidate --> WOCheck{WO valid?}
    WOCheck -->|No| Error400C[400 Bad Request<br/>Invalid work order]
    WOCheck -->|Yes| OOSUpdate[Update equipment.status = OOS<br/>Link to work_order_id<br/>Update timestamps]

    SimpleUpdate --> AuditLog[Optional: Create audit log entry]
    OOSUpdate --> AuditLog

    AuditLog --> Success200[200 OK<br/>Return:<br/>- equipment_id<br/>- new_status<br/>- updated_at]

    Success200 --> End([Complete])

    style Start fill:#e1f5ff
    style Success200 fill:#c8e6c9
    style Error403 fill:#ffcdd2
    style Error404 fill:#ffcdd2
    style Error400A fill:#ffcdd2
    style Error400B fill:#ffcdd2
    style Error400C fill:#ffcdd2
    style StatusCheck fill:#fff9c4
    style WORequired fill:#fff9c4
```

**8 Status Values**:
```
operational → degraded → failed → maintenance
                ↓
        out_of_service (requires WO)
                ↓
           in_service
                ↓
            archived
                ↓
        decommissioned
```

**Field Requirements**:
- **Required Always**: yacht_id, equipment_id, to_status
- **Conditional Required**: work_order_id (if to_status='out_of_service')
- **Optional**: reason (string)

---

## 3. Decommission & Replace Flow

**Action**: `decommission_and_replace_equipment` (SIGNED)
**Roles**: captain, manager only

```mermaid
flowchart TD
    Start([Decommission & Replace]) --> RoleCheck{User is<br/>captain or<br/>manager?}

    RoleCheck -->|No| Error403[403 Forbidden<br/>SIGNED action requires<br/>signature authority]
    RoleCheck -->|Yes| YachtCheck{Equipment<br/>belongs to<br/>user's yacht?}

    YachtCheck -->|No| Error404[404 Not Found<br/>RLS blocks access]
    YachtCheck -->|Yes| StatusCheck{Equipment<br/>already<br/>decommissioned?}

    StatusCheck -->|Yes| Error409[409 Conflict<br/>Already decommissioned]
    StatusCheck -->|No| PrepareInput[PREPARE Phase<br/>Required Fields:<br/>✓ yacht_id UUID<br/>✓ equipment_id UUID<br/>✓ reason string<br/>✓ replacement_name string<br/>✓ mode = prepare<br/>Optional:<br/>○ replacement_manufacturer<br/>○ replacement_model_number]

    PrepareInput --> GenerateToken[Generate confirmation_token<br/>Expires in 5 minutes<br/>Store in temp cache:<br/>- equipment_id<br/>- reason<br/>- replacement details]

    GenerateToken --> PrepareResponse[200 OK Prepare Response:<br/>- status: pending_signature<br/>- confirmation_token<br/>- action_summary<br/>- expires_at]

    PrepareResponse --> UserReview{Captain reviews<br/>and confirms?}

    UserReview -->|Cancel| Cancelled([Action Cancelled])
    UserReview -->|Confirm| ExecuteInput[EXECUTE Phase<br/>Required Fields:<br/>✓ mode = execute<br/>✓ confirmation_token<br/>✓ signature object:<br/>  ✓ pin string<br/>  ✓ totp string<br/>  ✓ reason string]

    ExecuteInput --> TokenValidate{Token valid<br/>and not<br/>expired?}

    TokenValidate -->|No| Error400A[400 Bad Request<br/>Invalid/expired token]
    TokenValidate -->|Yes| PINValidate[Validate PIN:<br/>bcrypt compare<br/>user.pin_hash]

    PINValidate --> PINCheck{PIN correct?}
    PINCheck -->|No| Error422A[422 Unprocessable<br/>Invalid PIN]
    PINCheck -->|Yes| TOTPValidate[Validate TOTP:<br/>Check current 30s window<br/>user.totp_secret]

    TOTPValidate --> TOTPCheck{TOTP valid?}
    TOTPCheck -->|No| Error422B[422 Unprocessable<br/>Invalid TOTP]
    TOTPCheck -->|Yes| AtomicTransaction[BEGIN TRANSACTION<br/>1. Create replacement equipment<br/>2. Set original status = decommissioned<br/>3. Create audit log with signature<br/>4. Invalidate confirmation_token<br/>COMMIT]

    AtomicTransaction --> TransactionCheck{Transaction<br/>success?}
    TransactionCheck -->|No| Error500[500 Internal Error<br/>Rollback transaction]
    TransactionCheck -->|Yes| ExecuteResponse[200 OK Execute Response:<br/>- status: success<br/>- decommissioned_equipment_id<br/>- replacement_equipment_id<br/>- audit_log_id<br/>- signature_verified: true<br/>- completed_at]

    ExecuteResponse --> End([Complete])

    style Start fill:#e1f5ff
    style PrepareResponse fill:#fff9c4
    style ExecuteResponse fill:#c8e6c9
    style UserReview fill:#fff9c4
    style Error403 fill:#ffcdd2
    style Error404 fill:#ffcdd2
    style Error409 fill:#ffcdd2
    style Error400A fill:#ffcdd2
    style Error422A fill:#ffcdd2
    style Error422B fill:#ffcdd2
    style Error500 fill:#ffcdd2
    style AtomicTransaction fill:#bbdefb
```

**Two-Phase Pattern**:
1. **PREPARE**: Generate token, show preview
2. **EXECUTE**: Validate signature, commit changes

**Signature Requirements**:
- **PIN**: 4-6 digit code (bcrypt hashed)
- **TOTP**: Time-based OTP (30-second window)
- **Reason**: Textual justification for audit trail

**Audit Log Invariant**:
- `pms_audit_log.signature` column **NEVER NULL** for SIGNED actions
- Stores: `{pin_valid: true, totp_valid: true, timestamp: "..."}`

---

## 4. Attach Image with Comment Flow

**Action**: `attach_image_with_comment` (MUTATE)
**Roles**: engineer, eto, chief_engineer, chief_officer, chief_steward, purser, captain, manager

```mermaid
flowchart TD
    Start([Attach Image with Comment]) --> RoleCheck{Has write<br/>permission?}

    RoleCheck -->|No crew| Error403[403 Forbidden<br/>Write requires HOD+]
    RoleCheck -->|Yes| YachtCheck{Equipment<br/>belongs to<br/>user's yacht?}

    YachtCheck -->|No| Error404[404 Not Found<br/>RLS blocks access]
    YachtCheck -->|Yes| InputFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ equipment_id UUID<br/>✓ file string storage path<br/>✓ comment string non-empty<br/>Optional:<br/>○ document_type string]

    InputFields --> CommentCheck{Comment<br/>provided and<br/>non-empty?}

    CommentCheck -->|No| Error400A[400 Bad Request<br/>Comment required]
    CommentCheck -->|Yes| PathCheck{Storage path<br/>starts with<br/>documents/?}

    PathCheck -->|Yes| Error400B[400 Bad Request<br/>Remove documents/ prefix]
    PathCheck -->|No| PathPattern[Validate Pattern:<br/>yacht_id/equipment/equipment_id/filename<br/>Example:<br/>85fe1119.../equipment/abc123/manual.pdf]

    PathPattern --> YachtIDMatch{Path yacht_id<br/>matches<br/>user's yacht?}

    YachtIDMatch -->|No| Error400C[400 Bad Request<br/>Wrong yacht_id in path]
    YachtIDMatch -->|Yes| EquipIDMatch{Path equipment_id<br/>matches<br/>parameter?}

    EquipIDMatch -->|No| Error400D[400 Bad Request<br/>Path equipment_id mismatch]
    EquipIDMatch -->|Yes| NestedCheck{Path contains<br/>nested dirs?}

    NestedCheck -->|Yes| Error400E[400 Bad Request<br/>No nested paths allowed]
    NestedCheck -->|No| StorageCheck[Optional: Verify file<br/>exists in storage bucket]

    StorageCheck --> StorageExists{File exists?}
    StorageExists -->|No| Error404B[404 Not Found<br/>File not in storage]
    StorageExists -->|Yes| CreateDoc[INSERT INTO<br/>pms_equipment_documents:<br/>- equipment_id<br/>- storage_path<br/>- comment NEW v2<br/>- created_by<br/>- created_at]

    CreateDoc --> DuplicateCheck{Unique<br/>storage_path?}
    DuplicateCheck -->|No| Error409[409 Conflict<br/>Document already linked]
    DuplicateCheck -->|Yes| Success200[200 OK<br/>Return:<br/>- document_id<br/>- storage_path<br/>- comment<br/>- created_at]

    Success200 --> End([Complete])

    style Start fill:#e1f5ff
    style Success200 fill:#c8e6c9
    style Error403 fill:#ffcdd2
    style Error404 fill:#ffcdd2
    style Error404B fill:#ffcdd2
    style Error400A fill:#ffcdd2
    style Error400B fill:#ffcdd2
    style Error400C fill:#ffcdd2
    style Error400D fill:#ffcdd2
    style Error400E fill:#ffcdd2
    style Error409 fill:#ffcdd2
    style PathCheck fill:#fff9c4
    style YachtIDMatch fill:#fff9c4
    style NestedCheck fill:#fff9c4
```

**Storage Path Validation Rules**:

```
✓ VALID:
  {yacht_id}/equipment/{equipment_id}/filename.ext
  85fe1119-b04c-41ac-80f1-829d23322598/equipment/abc-123/oil_leak.jpg

✗ INVALID:
  documents/85fe1119.../equipment/abc-123/file.pdf    # No documents/ prefix
  other-yacht-id/equipment/abc-123/file.pdf            # Wrong yacht_id
  85fe1119.../equipment/xyz-999/file.pdf               # Wrong equipment_id
  85fe1119.../equipment/abc-123/nested/dir/file.pdf   # No nesting allowed
```

**Material Drift Fix (v2)**:
- **v1**: Used `description` field (wrong)
- **v2**: Uses `comment` field (correct per spec)
- Migration 018 added `pms_equipment_documents.comment` column

---

## 5. Archive/Restore Flow

**Action**: `archive_equipment` (MUTATE) + `restore_archived_equipment` (SIGNED)

```mermaid
flowchart TD
    Start([Archive or Restore?]) --> Choice{User Intent?}

    Choice -->|Archive| ArchiveStart[Archive Equipment<br/>MUTATE Action]
    Choice -->|Restore| RestoreStart[Restore Archived<br/>SIGNED Action]

    %% Archive Branch
    ArchiveStart --> ArchiveRole{User has<br/>HOD+ role?}
    ArchiveRole -->|No| Error403A[403 Forbidden]
    ArchiveRole -->|Yes| ArchiveYacht{Equipment<br/>belongs to<br/>user's yacht?}

    ArchiveYacht -->|No| Error404A[404 Not Found]
    ArchiveYacht -->|Yes| ArchiveStatus{Current status<br/>= decommissioned?}

    ArchiveStatus -->|Yes| Error409A[409 Conflict<br/>Cannot archive<br/>decommissioned equipment]
    ArchiveStatus -->|No| ArchiveFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ equipment_id UUID<br/>Optional:<br/>○ reason string]

    ArchiveFields --> ArchiveUpdate[UPDATE pms_equipment<br/>SET status = 'archived'<br/>SET updated_at = NOW<br/>SET updated_by = user_id]

    ArchiveUpdate --> ArchiveSuccess[200 OK Archive<br/>Return:<br/>- equipment_id<br/>- new_status: archived<br/>- updated_at]

    ArchiveSuccess --> ArchiveEnd([Archived])

    %% Restore Branch
    RestoreStart --> RestoreRole{User is<br/>captain or<br/>manager?}

    RestoreRole -->|No| Error403B[403 Forbidden<br/>SIGNED action requires<br/>signature authority]
    RestoreRole -->|Yes| RestoreYacht{Equipment<br/>belongs to<br/>user's yacht?}

    RestoreYacht -->|No| Error404B[404 Not Found]
    RestoreYacht -->|Yes| RestoreStatus{Current status<br/>= archived?}

    RestoreStatus -->|No| Error400B[400 Bad Request<br/>Only archived equipment<br/>can be restored]
    RestoreStatus -->|Yes| RestorePrepare[PREPARE Phase<br/>Required:<br/>✓ yacht_id<br/>✓ equipment_id<br/>✓ mode = prepare]

    RestorePrepare --> RestoreToken[Generate confirmation_token<br/>Expires in 5 minutes]

    RestoreToken --> RestorePrepareResp[200 OK Prepare<br/>- confirmation_token<br/>- expires_at]

    RestorePrepareResp --> RestoreReview{Captain<br/>confirms<br/>restore?}

    RestoreReview -->|Cancel| RestoreCancelled([Cancelled])
    RestoreReview -->|Confirm| RestoreExecute[EXECUTE Phase<br/>Required:<br/>✓ mode = execute<br/>✓ confirmation_token<br/>✓ signature pin, totp, reason]

    RestoreExecute --> RestoreSigValidate[Validate Signature:<br/>1. Check PIN bcrypt<br/>2. Check TOTP window<br/>3. Verify token not expired]

    RestoreSigValidate --> RestoreSigCheck{Signature<br/>valid?}

    RestoreSigCheck -->|No| Error422B[422 Unprocessable<br/>Invalid signature]
    RestoreSigCheck -->|Yes| RestoreUpdate[UPDATE pms_equipment<br/>SET status = 'in_service'<br/>SET updated_at = NOW<br/>CREATE audit_log with signature]

    RestoreUpdate --> RestoreSuccess[200 OK Execute<br/>Return:<br/>- equipment_id<br/>- new_status: in_service<br/>- signature_verified: true<br/>- audit_log_id<br/>- restored_at]

    RestoreSuccess --> RestoreEnd([Restored])

    style Start fill:#e1f5ff
    style ArchiveSuccess fill:#c8e6c9
    style RestoreSuccess fill:#c8e6c9
    style Choice fill:#fff9c4
    style Error403A fill:#ffcdd2
    style Error403B fill:#ffcdd2
    style Error404A fill:#ffcdd2
    style Error404B fill:#ffcdd2
    style Error409A fill:#ffcdd2
    style Error400B fill:#ffcdd2
    style Error422B fill:#ffcdd2
    style RestoreReview fill:#fff9c4
```

**Status Transitions**:
```
Archive (MUTATE):
  operational/degraded/failed → archived

Restore (SIGNED):
  archived → in_service
```

**Material Drift Fix (v2)**:
- **v1**: Used `deleted_at` soft delete (wrong)
- **v2**: Uses `status='archived'` (correct per spec)
- Migration 019 added status constraint with 8 values

---

## 6. Role Permission Matrix

```mermaid
flowchart LR
    subgraph Roles [User Roles]
        Crew[crew<br/>Read Only]
        Deck[deckhand<br/>Read Only]
        Stew[steward<br/>Read Only]
        Eng[engineer<br/>Basic Write]
        ETO[eto<br/>Basic Write]
        ChiefEng[chief_engineer<br/>HOD Write]
        ChiefOff[chief_officer<br/>HOD Write]
        ChiefStew[chief_steward<br/>HOD Write]
        Purser[purser<br/>HOD Write NEW v2]
        Capt[captain<br/>Sign Authority]
        Mgr[manager<br/>Sign Authority]
    end

    subgraph Actions [Equipment Actions]
        Read[READ Actions<br/>- get_open_faults<br/>- get_related_entities]

        Mutate[MUTATE Actions<br/>- create_equipment<br/>- set_equipment_status<br/>- attach_image_with_comment<br/>- record_equipment_hours<br/>- add_equipment_note<br/>- archive_equipment]

        Signed[SIGNED Actions<br/>- decommission_and_replace<br/>- restore_archived<br/>- decommission_equipment]
    end

    Crew --> Read
    Deck --> Read
    Stew --> Read

    Eng --> Read
    Eng --> Mutate
    ETO --> Read
    ETO --> Mutate

    ChiefEng --> Read
    ChiefEng --> Mutate
    ChiefOff --> Read
    ChiefOff --> Mutate
    ChiefStew --> Read
    ChiefStew --> Mutate
    Purser --> Read
    Purser --> Mutate

    Capt --> Read
    Capt --> Mutate
    Capt --> Signed
    Mgr --> Read
    Mgr --> Mutate
    Mgr --> Signed

    style Crew fill:#ffebee
    style Deck fill:#ffebee
    style Stew fill:#ffebee
    style Eng fill:#fff3e0
    style ETO fill:#fff3e0
    style ChiefEng fill:#e8f5e9
    style ChiefOff fill:#e8f5e9
    style ChiefStew fill:#e8f5e9
    style Purser fill:#e8f5e9
    style Capt fill:#e3f2fd
    style Mgr fill:#e3f2fd
    style Read fill:#f5f5f5
    style Mutate fill:#bbdefb
    style Signed fill:#ffccbc
```

**Permission Hierarchy**:
```
crew/deckhand/steward (Read Only)
  ↓
engineer/eto (Basic Write)
  ↓
chief_engineer/chief_officer/chief_steward/purser (HOD Write)
  ↓
captain/manager (Sign Authority)
```

**Key Additions in Equipment Lens v2**:
- ✅ **purser** added to HOD roles (Migration 017)
- ✅ **set_equipment_status** replaces update_equipment_status (OOS validation)
- ✅ **attach_image_with_comment** adds comment field (Migration 018)
- ✅ **8-value status enum** (Migration 019)

---

## Complete User Journey Examples

### Journey 1: Equipment Breaks Down

```mermaid
flowchart LR
    A[Engineer notices<br/>oil leak] --> B[attach_image_with_comment<br/>Photo + description]
    B --> C[create_work_order_for_equipment<br/>Create repair WO]
    C --> D[set_equipment_status<br/>to_status=out_of_service<br/>work_order_id=WO123]
    D --> E[Engineer repairs<br/>following WO]
    E --> F[close_work_order<br/>Mark WO complete]
    F --> G[set_equipment_status<br/>to_status=operational]

    style A fill:#ffebee
    style B fill:#fff9c4
    style C fill:#fff9c4
    style D fill:#fff9c4
    style E fill:#e1f5ff
    style F fill:#fff9c4
    style G fill:#c8e6c9
```

### Journey 2: Equipment End of Life

```mermaid
flowchart LR
    A[Captain reviews<br/>aging equipment] --> B[add_equipment_note<br/>Document failure history]
    B --> C[decommission_and_replace<br/>PREPARE phase]
    C --> D[Captain enters<br/>PIN + TOTP]
    D --> E[decommission_and_replace<br/>EXECUTE phase]
    E --> F[Original: status=decommissioned<br/>New: status=operational]
    F --> G[link_document_to_equipment<br/>Transfer manuals to new]

    style A fill:#ffebee
    style B fill:#fff9c4
    style C fill:#fff9c4
    style D fill:#e1f5ff
    style E fill:#ffccbc
    style F fill:#c8e6c9
    style G fill:#fff9c4
```

### Journey 3: Seasonal Equipment Archive

```mermaid
flowchart LR
    A[End of season<br/>jet skis stored] --> B[archive_equipment<br/>MUTATE by HOD]
    B --> C[status=archived<br/>Equipment in storage]
    C --> D[Start of season<br/>6 months later]
    D --> E[restore_archived_equipment<br/>PREPARE by Captain]
    E --> F[Captain enters<br/>PIN + TOTP]
    F --> G[restore_archived_equipment<br/>EXECUTE SIGNED]
    G --> H[status=in_service<br/>Ready for use]

    style A fill:#ffebee
    style B fill:#fff9c4
    style C fill:#e1f5ff
    style D fill:#ffebee
    style E fill:#fff9c4
    style F fill:#e1f5ff
    style G fill:#ffccbc
    style H fill:#c8e6c9
```

---

## Field Requirement Summary

### Required Fields by Action

| Action | Always Required | Conditionally Required | Optional |
|--------|----------------|----------------------|----------|
| **set_equipment_status** | yacht_id, equipment_id, to_status | work_order_id (if OOS) | reason |
| **attach_image_with_comment** | yacht_id, equipment_id, file, comment | - | document_type |
| **decommission_and_replace** (PREPARE) | yacht_id, equipment_id, reason, replacement_name, mode=prepare | - | replacement_manufacturer, replacement_model_number |
| **decommission_and_replace** (EXECUTE) | mode=execute, confirmation_token, signature{pin, totp, reason} | - | - |
| **archive_equipment** | yacht_id, equipment_id | - | reason |
| **restore_archived_equipment** (PREPARE) | yacht_id, equipment_id, mode=prepare | - | - |
| **restore_archived_equipment** (EXECUTE) | mode=execute, confirmation_token, signature{pin, totp, reason} | - | - |

### Signature Object Structure

For all SIGNED actions (EXECUTE phase):
```json
{
  "signature": {
    "pin": "1234",              // Required: 4-6 digit PIN
    "totp": "567890",           // Required: 6-digit TOTP
    "reason": "Justification"   // Required: Audit trail text
  }
}
```

---

## Navigation Guide

**For Specific Scenarios**:
- Equipment broken? → [Flow 2: Set Status](#2-set-equipment-status-flow) → OOS branch
- Document issue? → [Flow 4: Attach Image](#4-attach-image-with-comment-flow)
- End of life? → [Flow 3: Decommission](#3-decommission--replace-flow)
- Temporary storage? → [Flow 5: Archive](#5-archiverestore-flow) → Archive branch
- Bring back equipment? → [Flow 5: Restore](#5-archiverestore-flow) → Restore branch

**For Role Questions**:
- What can I do? → [Flow 1: Master Journey](#1-master-journey-map) → Find your role
- Permission denied? → [Matrix 6: Roles](#6-role-permission-matrix) → Check access level

**For Field Questions**:
- What's required? → [Field Summary](#field-requirement-summary)
- Validation error? → Find action flow → Check validation nodes (yellow diamonds)

---

**Document Version**: 2026-01-27
**Equipment Lens v2**: Complete Visual Reference
