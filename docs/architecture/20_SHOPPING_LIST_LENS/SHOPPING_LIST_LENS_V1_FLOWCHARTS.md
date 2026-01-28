# Shopping List Lens v1 - Visual Flowcharts

**Purpose**: Visual decision trees showing role-gated journeys, field requirements, and workflow paths.

---

## Table of Contents

1. [Master Journey Map](#1-master-journey-map)
2. [Create Shopping List Item Flow](#2-create-shopping-list-item-flow)
3. [Approve Shopping List Item Flow](#3-approve-shopping-list-item-flow)
4. [Reject Shopping List Item Flow](#4-reject-shopping-list-item-flow)
5. [Promote Candidate to Part Flow](#5-promote-candidate-to-part-flow)
6. [Role Permission Matrix](#6-role-permission-matrix)

---

## 1. Master Journey Map

**Entry Point**: User views shopping list with intent to take action

```mermaid
flowchart TD
    Start([User Views Shopping List]) --> AuthCheck{Authenticated?}

    AuthCheck -->|No| Error401[401 Unauthorized]
    AuthCheck -->|Yes| RoleCheck{User Role?}

    RoleCheck -->|crew<br/>deckhand<br/>steward| CrewActions{What needs<br/>to be done?}

    RoleCheck -->|engineer<br/>eto| EngineerActions{What needs<br/>to be done?}

    RoleCheck -->|chief_engineer<br/>chief_officer<br/>captain<br/>manager<br/>purser| HODActions{What needs<br/>to be done?}

    %% CREW Branch
    CrewActions -->|Request item| CreateFlow[Create Shopping<br/>List Item]
    CrewActions -->|View history| HistoryFlow[View Shopping List<br/>Item History]

    %% ENGINEER Branch - same as CREW + promote
    EngineerActions -->|Request item| CreateFlow
    EngineerActions -->|View history| HistoryFlow
    EngineerActions -->|Upgrade candidate<br/>to part| PromoteFlow[Promote Candidate<br/>to Part Catalog]

    %% HOD Branch - all actions
    HODActions -->|Request item| CreateFlow
    HODActions -->|View history| HistoryFlow
    HODActions -->|Approve item| ApproveFlow[Approve Shopping<br/>List Item]
    HODActions -->|Reject item| RejectFlow[Reject Shopping<br/>List Item]
    HODActions -->|Upgrade candidate| PromoteFlow

    %% Link to detailed flows
    CreateFlow -.->|See Flow 2| CreateDetail[Create Item Flow]
    ApproveFlow -.->|See Flow 3| ApproveDetail[Approve Flow]
    RejectFlow -.->|See Flow 4| RejectDetail[Reject Flow]
    PromoteFlow -.->|See Flow 5| PromoteDetail[Promote Flow]

    style Start fill:#e1f5ff
    style CrewActions fill:#ffebee
    style EngineerActions fill:#fff3e0
    style HODActions fill:#e8f5e9
    style CreateFlow fill:#bbdefb
    style ApproveFlow fill:#c5e1a5
    style RejectFlow fill:#ffccbc
    style PromoteFlow fill:#d1c4e9
```

---

## 2. Create Shopping List Item Flow

**Action**: `create_shopping_list_item` (MUTATE)
**Roles**: All authenticated users (crew, deckhand, steward, engineer, eto, chief_engineer, chief_officer, purser, captain, manager)

```mermaid
flowchart TD
    Start([Create Shopping List Item]) --> RoleCheck{Authenticated?}

    RoleCheck -->|No| Error401[401 Unauthorized]
    RoleCheck -->|Yes| YachtCheck{Has yacht_id<br/>in JWT claims?}

    YachtCheck -->|No| Error403[403 Forbidden<br/>Yacht ID required]
    YachtCheck -->|Yes| InputFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ item_name string 1-500 chars<br/>✓ quantity integer min:1 max:99999<br/>✓ source_type enum<br/>✓ is_candidate_part bool<br/>Optional:<br/>○ item_description string max:2000<br/>○ manufacturer string max:500<br/>○ model_number string max:500<br/>○ unit string max:50<br/>○ estimated_cost decimal<br/>○ urgency enum]

    InputFields --> NameValidate{item_name<br/>length<br/>1-500?}

    NameValidate -->|No| Error400A[400 Bad Request<br/>Invalid item name length]
    NameValidate -->|Yes| QtyValidate{quantity<br/>1-99999?}

    QtyValidate -->|No| Error400B[400 Bad Request<br/>Quantity out of range]
    QtyValidate -->|Yes| SourceValidate{source_type in:<br/>manual, wo,<br/>maint_plan,<br/>project?}

    SourceValidate -->|No| Error400C[400 Bad Request<br/>Invalid source_type]
    SourceValidate -->|Yes| UrgencyValidate{urgency<br/>valid enum<br/>if provided?}

    UrgencyValidate -->|No| Error400D[400 Bad Request<br/>Invalid urgency value]
    UrgencyValidate -->|Yes| CostValidate{estimated_cost<br/>non-negative<br/>if provided?}

    CostValidate -->|No| Error400E[400 Bad Request<br/>Negative cost not allowed]
    CostValidate -->|Yes| CreateRecord[INSERT INTO<br/>pms_shopping_list_items:<br/>- yacht_id from JWT<br/>- item_name, quantity, source_type<br/>- is_candidate_part<br/>- status = 'candidate' default<br/>- created_by = user_id<br/>- created_at = NOW]

    CreateRecord --> Success200[200 OK<br/>Return:<br/>- id UUID<br/>- item_name<br/>- quantity<br/>- status: candidate<br/>- source_type<br/>- is_candidate_part<br/>- created_at<br/>- created_by<br/>- all optional fields]

    Success200 --> End([Complete])

    style Start fill:#e1f5ff
    style Success200 fill:#c8e6c9
    style Error401 fill:#ffcdd2
    style Error403 fill:#ffcdd2
    style Error400A fill:#ffcdd2
    style Error400B fill:#ffcdd2
    style Error400C fill:#ffcdd2
    style Error400D fill:#ffcdd2
    style Error400E fill:#ffcdd2
    style NameValidate fill:#fff9c4
    style QtyValidate fill:#fff9c4
    style SourceValidate fill:#fff9c4
```

**4 Source Types**:
```
manual       → User manually entered item
wo           → Originated from work order
maint_plan   → Originated from maintenance plan
project      → Originated from project
```

**5 Urgency Levels** (optional):
```
routine → normal_priority → high_priority → urgent → critical
```

**Field Validation Summary**:
- **item_name**: 1-500 characters (required)
- **quantity**: 1-99999 (required)
- **source_type**: enum (required)
- **is_candidate_part**: boolean (required)
- **estimated_cost**: non-negative decimal (optional)
- **urgency**: enum (optional, default: routine)

---

## 3. Approve Shopping List Item Flow

**Action**: `approve_shopping_list_item` (MUTATE)
**Roles**: HOD only (chief_engineer, chief_officer, captain, manager, purser)

```mermaid
flowchart TD
    Start([Approve Shopping List Item]) --> RoleCheck{User is HOD?<br/>chief_engineer<br/>chief_officer<br/>captain<br/>manager<br/>purser}

    RoleCheck -->|No| Error403[403 Forbidden<br/>Only HoD can approve<br/>shopping list items]
    RoleCheck -->|Yes| YachtCheck{Item belongs<br/>to user's<br/>yacht?}

    YachtCheck -->|No| Error404[404 Not Found<br/>RLS blocks access<br/>or item doesn't exist]
    YachtCheck -->|Yes| InputFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ item_id UUID<br/>✓ quantity_approved integer<br/>Optional:<br/>○ notes string]

    InputFields --> ItemExists{Item exists?}

    ItemExists -->|No| Error404B[404 Not Found<br/>Item ID not found]
    ItemExists -->|Yes| StatusCheck{Item status<br/>= candidate?}

    StatusCheck -->|No rejected_at| Error400A[400 Bad Request<br/>Cannot approve rejected item]
    StatusCheck -->|No approved| Error400B[400 Bad Request<br/>Item already approved]
    StatusCheck -->|Yes candidate| QtyValidate{quantity_approved<br/>≥ 1 and ≤<br/>original qty?}

    QtyValidate -->|No| Error400C[400 Bad Request<br/>Invalid approved quantity]
    QtyValidate -->|Yes| UpdateRecord[UPDATE pms_shopping_list_items<br/>SET status = 'approved'<br/>SET quantity_approved = value<br/>SET approved_by = user_id<br/>SET approved_at = NOW<br/>SET notes = notes if provided<br/>SET updated_at = NOW]

    UpdateRecord --> HistoryRecord[Optional: INSERT INTO<br/>pms_shopping_list_item_state_history:<br/>- item_id<br/>- from_status: candidate<br/>- to_status: approved<br/>- changed_by: user_id<br/>- changed_at: NOW<br/>- notes]

    HistoryRecord --> Success200[200 OK<br/>Return:<br/>- id<br/>- status: approved<br/>- quantity_approved<br/>- approved_by<br/>- approved_at<br/>- notes<br/>- updated_at]

    Success200 --> End([Complete])

    style Start fill:#e1f5ff
    style Success200 fill:#c8e6c9
    style Error403 fill:#ffcdd2
    style Error404 fill:#ffcdd2
    style Error404B fill:#ffcdd2
    style Error400A fill:#ffcdd2
    style Error400B fill:#ffcdd2
    style Error400C fill:#ffcdd2
    style StatusCheck fill:#fff9c4
    style QtyValidate fill:#fff9c4
```

**State Transition**:
```
candidate → approved (terminal)
```

**HOD Roles** (is_hod() returns true):
- chief_engineer
- chief_officer
- captain
- manager
- purser

**Approval Business Rules**:
1. Only HOD can approve
2. Item must be in 'candidate' status
3. Cannot approve rejected items (rejected_at NOT NULL)
4. quantity_approved must be ≥ 1 and ≤ original quantity
5. Sets approved_at timestamp and approved_by user_id

---

## 4. Reject Shopping List Item Flow

**Action**: `reject_shopping_list_item` (MUTATE)
**Roles**: HOD only (chief_engineer, chief_officer, captain, manager, purser)

```mermaid
flowchart TD
    Start([Reject Shopping List Item]) --> RoleCheck{User is HOD?<br/>chief_engineer<br/>chief_officer<br/>captain<br/>manager<br/>purser}

    RoleCheck -->|No| Error403[403 Forbidden<br/>Only HoD can reject<br/>shopping list items]
    RoleCheck -->|Yes| YachtCheck{Item belongs<br/>to user's<br/>yacht?}

    YachtCheck -->|No| Error404[404 Not Found<br/>RLS blocks access<br/>or item doesn't exist]
    YachtCheck -->|Yes| InputFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ item_id UUID<br/>✓ rejection_reason string<br/>Optional:<br/>○ notes string]

    InputFields --> ItemExists{Item exists?}

    ItemExists -->|No| Error404B[404 Not Found<br/>Item ID not found]
    ItemExists -->|Yes| StatusCheck{Item status?}

    StatusCheck -->|rejected_at| Error400A[400 Bad Request<br/>Item already rejected]
    StatusCheck -->|approved| Error400B[400 Bad Request<br/>Cannot reject approved item]
    StatusCheck -->|candidate| ReasonCheck{rejection_reason<br/>provided and<br/>non-empty?}

    ReasonCheck -->|No| Error400C[400 Bad Request<br/>Rejection reason required]
    ReasonCheck -->|Yes| UpdateRecord[UPDATE pms_shopping_list_items<br/>SET rejected_at = NOW<br/>SET rejected_by = user_id<br/>SET rejection_reason = reason<br/>SET notes = notes if provided<br/>SET updated_at = NOW<br/>NOTE: status remains 'candidate']

    UpdateRecord --> HistoryRecord[Optional: INSERT INTO<br/>pms_shopping_list_item_state_history:<br/>- item_id<br/>- from_status: candidate<br/>- to_status: rejected<br/>- changed_by: user_id<br/>- changed_at: NOW<br/>- notes: rejection_reason]

    HistoryRecord --> Success200[200 OK<br/>Return:<br/>- id<br/>- status: candidate<br/>- rejected_at<br/>- rejected_by<br/>- rejection_reason<br/>- notes<br/>- updated_at]

    Success200 --> End([Complete])

    style Start fill:#e1f5ff
    style Success200 fill:#c8e6c9
    style Error403 fill:#ffcdd2
    style Error404 fill:#ffcdd2
    style Error404B fill:#ffcdd2
    style Error400A fill:#ffcdd2
    style Error400B fill:#ffcdd2
    style Error400C fill:#ffcdd2
    style StatusCheck fill:#fff9c4
    style ReasonCheck fill:#fff9c4
```

**State Transition**:
```
candidate → candidate (with rejected_at NOT NULL) - terminal
```

**Rejection Business Rules**:
1. Only HOD can reject
2. Item must be in 'candidate' status (rejected_at IS NULL)
3. Cannot reject already rejected items (rejected_at NOT NULL)
4. Cannot reject approved items (status='approved')
5. rejection_reason is required and cannot be empty
6. Sets rejected_at timestamp and rejected_by user_id
7. **Important**: status remains 'candidate', rejection marked by rejected_at field

**Material Drift Note**:
- Rejection does NOT change status field
- Rejected state indicated by rejected_at IS NOT NULL
- This allows queries like: `WHERE status='candidate' AND rejected_at IS NULL` for active candidates

---

## 5. Promote Candidate to Part Flow

**Action**: `promote_candidate_to_part` (MUTATE)
**Roles**: Engineers only (chief_engineer, engineer, manager)

```mermaid
flowchart TD
    Start([Promote Candidate to Part]) --> RoleCheck{User is<br/>engineer?<br/>chief_engineer<br/>engineer<br/>manager}

    RoleCheck -->|No| Error403[403 Forbidden<br/>Only engineers can promote<br/>candidates to parts catalog]
    RoleCheck -->|Yes| YachtCheck{Item belongs<br/>to user's<br/>yacht?}

    YachtCheck -->|No| Error404[404 Not Found<br/>RLS blocks access<br/>or item doesn't exist]
    YachtCheck -->|Yes| InputFields[Required Fields:<br/>✓ yacht_id UUID<br/>✓ item_id UUID<br/>✓ part_name string<br/>✓ part_number string<br/>Optional:<br/>○ manufacturer string<br/>○ model_number string<br/>○ description string<br/>○ category string]

    InputFields --> ItemExists{Item exists?}

    ItemExists -->|No| Error404B[404 Not Found<br/>Item ID not found]
    ItemExists -->|Yes| CandidateCheck{is_candidate_part<br/>= true?}

    CandidateCheck -->|No| Error400A[400 Bad Request<br/>Item not marked as<br/>candidate part]
    CandidateCheck -->|Yes| ApprovedCheck{Item status<br/>= approved?}

    ApprovedCheck -->|No rejected| Error400B[400 Bad Request<br/>Cannot promote rejected item]
    ApprovedCheck -->|No candidate| Error400C[400 Bad Request<br/>Item must be approved first]
    ApprovedCheck -->|Yes approved| PartNameCheck{part_name<br/>non-empty?}

    PartNameCheck -->|No| Error400D[400 Bad Request<br/>Part name required]
    PartNameCheck -->|Yes| PartNumberCheck{part_number<br/>non-empty?}

    PartNumberCheck -->|No| Error400E[400 Bad Request<br/>Part number required]
    PartNumberCheck -->|Yes| CreatePart[INSERT INTO<br/>pms_parts_catalog:<br/>- yacht_id<br/>- part_name<br/>- part_number<br/>- manufacturer<br/>- model_number<br/>- description<br/>- category<br/>- created_by = user_id<br/>- created_at = NOW]

    CreatePart --> PartCreated{Part creation<br/>successful?}

    PartCreated -->|No duplicate| Error409[409 Conflict<br/>Part number already exists]
    PartCreated -->|Yes| UpdateItem[UPDATE pms_shopping_list_items<br/>SET promoted_to_part_id = new_part.id<br/>SET promoted_by = user_id<br/>SET promoted_at = NOW<br/>SET updated_at = NOW]

    UpdateItem --> HistoryRecord[Optional: INSERT INTO<br/>pms_shopping_list_item_state_history:<br/>- item_id<br/>- from_status: approved<br/>- to_status: promoted<br/>- changed_by: user_id<br/>- changed_at: NOW<br/>- notes: part_id reference]

    HistoryRecord --> Success200[200 OK<br/>Return:<br/>- shopping_list_item_id<br/>- status: approved<br/>- promoted_to_part_id<br/>- promoted_by<br/>- promoted_at<br/>- new_part object:<br/>  - id<br/>  - part_name<br/>  - part_number<br/>  - created_at]

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
    style CandidateCheck fill:#fff9c4
    style ApprovedCheck fill:#fff9c4
    style PartNameCheck fill:#fff9c4
```

**State Transition**:
```
approved → approved (with promoted_to_part_id NOT NULL)
```

**Engineer Roles** (is_engineer() returns true):
- chief_engineer
- engineer
- manager

**Promotion Business Rules**:
1. Only engineers can promote
2. Item must have is_candidate_part = true
3. Item must be in 'approved' status
4. Cannot promote rejected items
5. Cannot promote non-approved items
6. part_name and part_number are required
7. Creates new record in pms_parts_catalog
8. Links shopping list item to new part via promoted_to_part_id
9. Sets promoted_at timestamp and promoted_by user_id
10. Part number must be unique within yacht

**Integration Note**:
- Promotes item from shopping list to permanent parts catalog
- Shopping list item retains its status='approved'
- Promotion marked by promoted_to_part_id field
- New part inherits manufacturer, model_number from shopping list item

---

## 6. Role Permission Matrix

```mermaid
flowchart LR
    subgraph Roles [User Roles]
        Crew[crew<br/>deckhand<br/>steward<br/>Basic Create]
        Eng[engineer<br/>eto<br/>Create + Promote]
        ChiefEng[chief_engineer<br/>Create + Approve<br/>+ Reject + Promote]
        HOD[chief_officer<br/>purser<br/>Create + Approve<br/>+ Reject]
        Senior[captain<br/>manager<br/>Full Access]
    end

    subgraph Actions [Shopping List Actions]
        Create[CREATE<br/>- create_shopping_list_item]

        View[VIEW<br/>- view_shopping_list_item_history]

        HODActions[HOD ACTIONS<br/>- approve_shopping_list_item<br/>- reject_shopping_list_item]

        EngActions[ENGINEER ACTIONS<br/>- promote_candidate_to_part]
    end

    Crew --> Create
    Crew --> View

    Eng --> Create
    Eng --> View
    Eng --> EngActions

    ChiefEng --> Create
    ChiefEng --> View
    ChiefEng --> HODActions
    ChiefEng --> EngActions

    HOD --> Create
    HOD --> View
    HOD --> HODActions

    Senior --> Create
    Senior --> View
    Senior --> HODActions
    Senior --> EngActions

    style Crew fill:#ffebee
    style Eng fill:#fff3e0
    style ChiefEng fill:#c8e6c9
    style HOD fill:#e8f5e9
    style Senior fill:#e3f2fd
    style Create fill:#bbdefb
    style View fill:#f5f5f5
    style HODActions fill:#ffccbc
    style EngActions fill:#d1c4e9
```

**Permission Hierarchy**:
```
crew/deckhand/steward (Create Only)
  ↓
engineer/eto (Create + Promote)
  ↓
chief_officer/purser (HOD: Create + Approve + Reject)
  ↓
chief_engineer (HOD + Engineer: All Actions)
  ↓
captain/manager (Full Access: All Actions)
```

**Role Permission Table**:

| Role | Create | Approve | Reject | Promote | View History |
|------|--------|---------|--------|---------|--------------|
| crew | ✅ | ❌ | ❌ | ❌ | ✅ |
| deckhand | ✅ | ❌ | ❌ | ❌ | ✅ |
| steward | ✅ | ❌ | ❌ | ❌ | ✅ |
| engineer | ✅ | ❌ | ❌ | ✅ | ✅ |
| eto | ✅ | ❌ | ❌ | ✅ | ✅ |
| chief_engineer | ✅ | ✅ | ✅ | ✅ | ✅ |
| chief_officer | ✅ | ✅ | ✅ | ❌ | ✅ |
| purser | ✅ | ✅ | ✅ | ❌ | ✅ |
| captain | ✅ | ✅ | ✅ | ✅ | ✅ |
| manager | ✅ | ✅ | ✅ | ✅ | ✅ |

**Special Note**:
- **chief_engineer** has BOTH HOD and engineer privileges (can approve AND promote)
- **manager** and **captain** have full access to all actions

---

## Complete User Journey Examples

### Journey 1: Simple Item Request (CREW → HOD)

```mermaid
flowchart LR
    A[CREW notices low<br/>cleaning supplies] --> B[create_shopping_list_item<br/>item: Deck cleaner<br/>qty: 10<br/>is_candidate: false]
    B --> C[Item created<br/>status: candidate]
    C --> D[HOD reviews request<br/>in shopping list]
    D --> E[approve_shopping_list_item<br/>quantity_approved: 10]
    E --> F[Item approved<br/>Ready for procurement]

    style A fill:#ffebee
    style B fill:#bbdefb
    style C fill:#fff9c4
    style D fill:#e1f5ff
    style E fill:#c5e1a5
    style F fill:#c8e6c9
```

### Journey 2: New Part Discovery (CREW → HOD → ENGINEER)

```mermaid
flowchart LR
    A[CREW identifies<br/>new filter type needed] --> B[create_shopping_list_item<br/>item: Fuel filter XYZ<br/>qty: 5<br/>is_candidate: true<br/>manufacturer: Racor]
    B --> C[Item created<br/>status: candidate<br/>is_candidate_part: true]
    C --> D[HOD reviews<br/>specifications]
    D --> E[approve_shopping_list_item<br/>quantity_approved: 5]
    E --> F[ENGINEER reviews<br/>for catalog addition]
    F --> G[promote_candidate_to_part<br/>part_name: Fuel Filter XYZ<br/>part_number: RAC-FLT-123]
    G --> H[New part in catalog<br/>Item promoted<br/>Ready for procurement]

    style A fill:#ffebee
    style B fill:#bbdefb
    style C fill:#fff9c4
    style D fill:#e1f5ff
    style E fill:#c5e1a5
    style F fill:#e1f5ff
    style G fill:#d1c4e9
    style H fill:#c8e6c9
```

### Journey 3: Item Rejection (CREW → HOD)

```mermaid
flowchart LR
    A[CREW requests<br/>expensive item] --> B[create_shopping_list_item<br/>item: Gold-plated wrench<br/>qty: 1<br/>estimated_cost: 5000]
    B --> C[Item created<br/>status: candidate]
    C --> D[HOD reviews cost<br/>and necessity]
    D --> E[reject_shopping_list_item<br/>reason: Over budget,<br/>standard tool sufficient]
    E --> F[Item rejected<br/>rejected_at set<br/>Procurement blocked]

    style A fill:#ffebee
    style B fill:#bbdefb
    style C fill:#fff9c4
    style D fill:#e1f5ff
    style E fill:#ffccbc
    style F fill:#ffcdd2
```

### Journey 4: Work Order Integration (ENGINEER → HOD)

```mermaid
flowchart LR
    A[Work order identifies<br/>part needed] --> B[create_shopping_list_item<br/>item: Hydraulic pump seal<br/>qty: 2<br/>source_type: wo<br/>urgency: urgent]
    B --> C[Item created<br/>status: candidate<br/>urgency: urgent]
    C --> D[HOD sees urgent flag<br/>prioritizes review]
    D --> E[approve_shopping_list_item<br/>quantity_approved: 2<br/>notes: Expedite shipping]
    E --> F[Item approved<br/>Urgent procurement<br/>WO can proceed]

    style A fill:#fff3e0
    style B fill:#bbdefb
    style C fill:#fff9c4
    style D fill:#e1f5ff
    style E fill:#c5e1a5
    style F fill:#c8e6c9
```

---

## Field Requirement Summary

### Required Fields by Action

| Action | Always Required | Optional |
|--------|----------------|----------|
| **create_shopping_list_item** | yacht_id, item_name (1-500 chars), quantity (1-99999), source_type (enum), is_candidate_part (bool) | item_description, manufacturer, model_number, unit, estimated_cost (≥0), urgency (enum), notes |
| **approve_shopping_list_item** | yacht_id, item_id, quantity_approved (≥1) | notes |
| **reject_shopping_list_item** | yacht_id, item_id, rejection_reason (non-empty) | notes |
| **promote_candidate_to_part** | yacht_id, item_id, part_name (non-empty), part_number (non-empty) | manufacturer, model_number, description, category |
| **view_shopping_list_item_history** | yacht_id, item_id | - |

### Enum Values

**source_type** (required on create):
```
- manual         # User-entered item
- wo             # From work order
- maint_plan     # From maintenance plan
- project        # From project
```

**urgency** (optional on create, default: routine):
```
- routine
- normal_priority
- high_priority
- urgent
- critical
```

### Status Field States

```
candidate    → Initial state (all new items)
approved     → HOD approved (terminal, can be promoted)
```

**Terminal State Indicators**:
- `rejected_at IS NOT NULL` → Rejected (terminal, status remains 'candidate')
- `status = 'approved'` → Approved (terminal, can be promoted)
- `promoted_to_part_id IS NOT NULL` → Promoted (status remains 'approved')

---

## State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> candidate: create_shopping_list_item<br/>(any authenticated user)

    candidate --> approved: approve_shopping_list_item<br/>(HOD only)

    candidate --> rejected: reject_shopping_list_item<br/>(HOD only)<br/>rejected_at set

    approved --> promoted: promote_candidate_to_part<br/>(engineer only)<br/>promoted_to_part_id set

    rejected --> [*]: Terminal State
    approved --> [*]: Terminal State
    promoted --> [*]: Terminal State

    note right of candidate
        Default status for all new items
        RLS: User can only update own items
        HOD can approve/reject
    end note

    note right of approved
        Terminal state
        quantity_approved set
        approved_by and approved_at recorded
        Can be promoted if is_candidate_part=true
    end note

    note right of rejected
        Pseudo-terminal state
        status='candidate' but rejected_at IS NOT NULL
        rejection_reason required
        Cannot be approved or promoted
    end note

    note right of promoted
        Extended terminal state
        status='approved' but promoted_to_part_id set
        New part created in catalog
        Shopping list item retained for audit
    end note
```

---

## Navigation Guide

**For Specific Scenarios**:
- Request supplies? → [Flow 2: Create Item](#2-create-shopping-list-item-flow)
- Approve request? → [Flow 3: Approve](#3-approve-shopping-list-item-flow) (HOD only)
- Reject request? → [Flow 4: Reject](#4-reject-shopping-list-item-flow) (HOD only)
- Add to catalog? → [Flow 5: Promote](#5-promote-candidate-to-part-flow) (Engineer only)

**For Role Questions**:
- What can I do? → [Flow 1: Master Journey](#1-master-journey-map) → Find your role
- Permission denied? → [Matrix 6: Roles](#6-role-permission-matrix) → Check access level

**For Field Questions**:
- What's required? → [Field Summary](#field-requirement-summary)
- Validation error? → Find action flow → Check validation nodes (yellow diamonds)

**For State Questions**:
- What states exist? → [State Machine](#state-machine-diagram)
- Can I do action X? → Check current state in state machine

---

## Security Notes

**Defense-in-Depth (3 Layers)**:

1. **Router Layer** (apps/api/main.py):
   - Action definitions enforce `allowed_roles`
   - First line of defense
   - Example: `"allowed_roles": ["chief_engineer", "chief_officer", "captain", "manager", "purser"]`

2. **Handler Layer** (apps/api/handlers/shopping_list_handlers.py):
   - Explicit role checks using `is_hod()` and `is_engineer()` RPCs
   - Blocks service key operations
   - Returns 403 with descriptive messages
   - Example: `if not is_hod_result.data: return 403`

3. **Database Layer** (RLS policies):
   - Blocks direct SQL access (PostgREST)
   - Role-specific UPDATE policies
   - Yacht isolation enforcement
   - Example: Policy `hod_approve_shopping_items` checks `is_hod(auth.uid(), get_user_yacht_id())`

**Result**: Users cannot bypass restrictions even with:
- Direct database access (blocked by RLS)
- Compromised UI (blocked by handler checks)
- Direct API calls (blocked by router + handlers)

---

**Document Version**: 2026-01-28
**Shopping List Lens v1**: Complete Visual Reference
