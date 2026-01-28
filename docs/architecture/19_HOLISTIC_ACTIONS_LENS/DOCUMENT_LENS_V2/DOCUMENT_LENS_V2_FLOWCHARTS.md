# Document Lens v2 - Flowcharts

## Overview

Visual decision flows for Document Lens v2 actions.

---

## 1. Upload Document Flow

```mermaid
flowchart TD
    A[User: Upload Document] --> B{Role Check}
    B -->|crew/deckhand/etc| C[403 Forbidden]
    B -->|HOD role| D{Validate Payload}
    D -->|Missing file_name| E[400 Bad Request]
    D -->|Missing mime_type| E
    D -->|Valid| F[Sanitize Filename]
    F --> G[Generate Document ID]
    G --> H[Build Storage Path]
    H --> I[Create doc_metadata Row]
    I --> J[Generate Signed Upload URL]
    J --> K[Write Audit Log]
    K --> L[Return: document_id, upload_url]

    style C fill:#f66
    style E fill:#f66
    style L fill:#6f6
```

---

## 2. Update Document Flow

```mermaid
flowchart TD
    A[User: Update Document] --> B{Role Check}
    B -->|crew/deckhand/etc| C[403 Forbidden]
    B -->|HOD role| D{Document Exists?}
    D -->|No| E[404 Not Found]
    D -->|Yes| F{Document Deleted?}
    F -->|Yes| G[400 Cannot Update Deleted]
    F -->|No| H[Extract Update Fields]
    H --> I[Log to Audit]
    I --> J[Return: success, updated_fields]

    style C fill:#f66
    style E fill:#f66
    style G fill:#f66
    style J fill:#6f6
```

---

## 3. Delete Document Flow (SIGNED)

```mermaid
flowchart TD
    A[User: Delete Document] --> B{Role Check}
    B -->|Not captain/manager| C[403 Forbidden]
    B -->|captain/manager| D{Signature Provided?}
    D -->|No| E[400 Signature Required]
    D -->|Yes| F{Reason Provided?}
    F -->|No| G[400 Reason Required]
    F -->|Yes| H{Document Exists?}
    H -->|No| I[404 Not Found]
    H -->|Yes| J{Already Deleted?}
    J -->|Yes| K[400 Already Deleted]
    J -->|No| L[Log SIGNED Audit Entry]
    L --> M[Return: success, is_signed=true]

    style C fill:#f66
    style E fill:#f66
    style G fill:#f66
    style I fill:#f66
    style K fill:#f66
    style M fill:#6f6
```

---

## 4. Get Document URL Flow

```mermaid
flowchart TD
    A[User: Get Document URL] --> B{Authenticated?}
    B -->|No| C[401 Unauthorized]
    B -->|Yes| D{Document Exists?}
    D -->|No| E[404 Not Found]
    D -->|Yes| F[Get Storage Path]
    F --> G{File in Storage?}
    G -->|No| H[500 Storage Error]
    G -->|Yes| I[Generate Signed URL]
    I --> J[Return: signed_url, expires_in]

    style C fill:#f66
    style E fill:#f66
    style H fill:#f66
    style J fill:#6f6
```

---

## 5. Action List Role Gating

```mermaid
flowchart TD
    A[GET /v1/actions/list?domain=documents] --> B{Extract User Role}
    B --> C{Is HOD Role?}
    C -->|Yes| D[Return: upload, update, tags, delete*, get_url, list]
    C -->|No| E{Is Captain/Manager?}
    E -->|Yes| D
    E -->|No| F[Return: get_url, list only]

    D --> G[Filter by Variant]
    G --> H[MUTATE actions visible to HOD]
    G --> I[SIGNED actions visible to captain/manager]
    G --> J[READ actions visible to all]

    style D fill:#6f6
    style F fill:#ff6
```

---

## 6. Complete User Journey: Upload and Share

```mermaid
sequenceDiagram
    participant HOD as Chief Engineer
    participant API as Actions API
    participant DB as doc_metadata
    participant Storage as Supabase Storage
    participant Crew as Crew Member

    HOD->>API: upload_document (file_name, mime_type)
    API->>API: Validate role (HOD OK)
    API->>DB: INSERT doc_metadata
    API->>Storage: Create signed upload URL
    API-->>HOD: {document_id, upload_url}

    HOD->>Storage: PUT file to upload_url
    Storage-->>HOD: 200 OK

    HOD->>API: add_document_tags (document_id, tags)
    API->>DB: UPDATE tags
    API-->>HOD: {success}

    Note over HOD,Crew: Later, crew needs the document

    Crew->>API: get_document_url (document_id)
    API->>API: Validate role (crew OK for READ)
    API->>Storage: Create signed download URL
    API-->>Crew: {signed_url}

    Crew->>Storage: GET signed_url
    Storage-->>Crew: Document file
```

---

## 7. Complete User Journey: Delete with Signature

```mermaid
sequenceDiagram
    participant Captain
    participant API as Actions API
    participant DB as doc_metadata
    participant Audit as pms_audit_log

    Captain->>API: delete_document (document_id, reason, signature)
    API->>API: Validate role (captain OK)
    API->>API: Validate signature (non-empty JSON)
    API->>API: Validate reason (required)
    API->>DB: SELECT document
    DB-->>API: Document found

    API->>Audit: INSERT signed audit entry
    Note over API,Audit: signature = {signature_type, role_at_signing, signed_at, hash}

    API-->>Captain: {success, is_signed: true}
```

---

## 8. Error Decision Tree

```mermaid
flowchart TD
    A[Action Request] --> B{401?}
    B -->|Missing/invalid JWT| C[401 Unauthorized]
    B -->|Valid JWT| D{403?}
    D -->|Role not in allowed_roles| E[403 Forbidden]
    D -->|Role OK| F{400?}
    F -->|Missing required field| G[400 Bad Request]
    F -->|Invalid format| G
    F -->|Signature required but empty| G
    F -->|Valid payload| H{404?}
    H -->|Document not found| I[404 Not Found]
    H -->|Document exists| J{500?}
    J -->|Storage error| K[500 Internal Error]
    J -->|Success| L[200 OK]

    style C fill:#f66
    style E fill:#f66
    style G fill:#f66
    style I fill:#f66
    style K fill:#f66
    style L fill:#6f6
```

---

## Role Hierarchy Visualization

```mermaid
graph TD
    subgraph "SIGNED Actions"
        A[captain]
        B[manager]
    end

    subgraph "MUTATE Actions"
        C[chief_engineer]
        D[chief_officer]
        E[chief_steward]
        F[purser]
        A
        B
    end

    subgraph "READ Actions"
        G[crew]
        H[deckhand]
        I[steward]
        J[chef]
        K[bosun]
        L[engineer]
        M[eto]
        C
        D
        E
        F
        A
        B
    end
```

---

## Audit Log Signature Patterns

```mermaid
flowchart LR
    subgraph "Non-Signed Actions"
        A[upload_document] --> B["signature: {}"]
        C[update_document] --> B
        D[add_document_tags] --> B
    end

    subgraph "Signed Actions"
        E[delete_document] --> F["signature: {<br>signature_type,<br>role_at_signing,<br>signed_at,<br>signature_hash<br>}"]
    end

    style B fill:#ff6
    style F fill:#6f6
```
