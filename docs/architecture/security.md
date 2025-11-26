
# 🛡️ **security.md — CelesteOS Security Architecture**

**Version:** 1.0
**Owner:** Engineering
**Status:** Draft (Approved for MVP)

---

# # 🔒 **Overview**

CelesteOS stores and processes engineering documentation, fault history, and maintenance intelligence for superyachts.
Because the platform interacts with sensitive operational data, our security model is built around:

* **Cloud-first isolation**
* **Strong encryption**
* **Per-yacht boundaries**
* **Ephemeral, signed access**
* **Read-only ingestion from vessel NAS**
* **Zero PII storage**
* **Tamper-proof integrity checks**

The goal is simple:

> **Guarantee that no yacht’s data can ever be accessed, inferred, leaked, or modified by another party — including other yachts using CelesteOS.**

---

# # 🟦 **1. Data Isolation Model**

CelesteOS uses a **True Isolation Architecture** where each yacht’s data exists in its own logical and physical boundary.

### **1.1 Isolation Layers**

Each yacht receives:

* Its own **object storage bucket** (or bucket prefix)
* Its own **database schema**
  or
  Its own **database instance** (for ultra-sensitive clients)
* Its own **API namespace**
* Its own **yacht_signature** (cryptographic identity)
* Its own **encryption keys**
* Its own **worker queue**

No cross-tenant access.
No shared tables.
No shared object directories.

### **1.2 Blast Radius**

If a yacht environment fails, the impact is LIMITED to that vessel alone.

### **1.3 No PII**

CelesteOS never stores:

* passports
* DOB
* salary
* owner identities
* guest information

User accounts contain:

* name
* email
* role

---

# # 🔐 **2. Encryption Standards**

### **2.1 Data in Transit**

All traffic is encrypted using **TLS 1.3** with strict policies:

* HSTS
* No TLS fallback
* No insecure ciphers
* Certificate pinning recommended for mobile apps

### **2.2 Data at Rest**

All stored data uses **AES-256 encryption** via:

* Encrypted block volumes
* Encrypted object storage
* Encrypted DB rows (sensitive fields)
* Encrypted tokens

### **2.3 Client-Side Integrity**

Documents are hashed using **SHA256** before upload.

This ensures:

* no tampering
* no corruption
* no duplicate uploads
* no collisions in embeddings

CelesteOS independently re-hashes files in the cloud to confirm integrity.

---

# # 🧩 **3. Authentication & Access Control**

### **3.1 Yacht Signature (Identity of Vessel)**

Each vessel gets a **unique cryptographic signature** created during onboarding.

Used to:

* validate that upload requests come from that yacht
* link all documents to the correct isolation bucket
* restrict local agent traffic
* authenticate mobile uploads
* prevent cross-vessel leakage

It acts as the **root identity** for the entire yacht’s environment.

### **3.2 User Authentication**

Users authenticate through:

* password
* OAuth provider (Microsoft/Google)
* device token (mobile app)

### **3.3 Token Types**

* **API tokens** (hashed, non-reversible)
* **Refresh tokens**
* **Device tokens** (mobile upload)
* **Yacht installation tokens**

Tokens are NEVER stored in plaintext.

### **3.4 Role-Based Access Control**

Roles determine:

* who can create work orders
* who can add to handover
* who can export reports
* who can manage equipment
* who can manage users
* who can modify predictive features

Roles:

* Captain
* Chief Engineer
* ETO
* Deck/Interior
* Management
* Vendor

---

# # 🟧 **4. Upload Security (NAS → Cloud)**

### **4.1 NAS Read-Only Principle**

Local agent connects to NAS with **read-only credentials**.

Agent cannot:

* delete files
* overwrite files
* rename files
* modify metadata

### **4.2 SHA256 Integrity**

Every file is:

* hashed locally
* hashed in the cloud
* compared
* deduplicated

Ensures no corruption, tampering, or inconsistency.

### **4.3 Chunked, Resumable Uploads**

Large files uploaded in:

* 8–32 MB encrypted chunks
* resumable streams
* retry-safe transactions

If connection drops, upload continues without corruption.

### **4.4 Yacht Signature Binding**

Every upload includes:

* yacht_signature
* timestamp
* HMAC authentication

This ensures the cloud knows EXACTLY which yacht is the source.

### **4.5 Zero Trust Agent**

The agent does not trust the cloud.
The cloud does not trust the agent.

All communication MUST be:

* signed
* timestamped
* validated

---

# # 🟥 **5. API Security**

### **5.1 Strict Authentication**

ALL endpoints require:

* yacht_signature
* user_token
* time-limited signed URLs for file upload/download

### **5.2 Request Validation**

Cloud checks:

* file size
* SHA256 hash
* chunk order
* content type
* yacht assignment
* duplicate prevention

### **5.3 Rate Limiting & Throttling**

* Prevents brute force
* Prevents misconfigured agents from flooding the cloud
* Ensures fair system load distribution

---

# # 🟩 **6. Object Storage Security**

### **6.1 Encrypted Buckets**

Each yacht has:

* isolated bucket
* private only
* not public
* no listing permissions

### **6.2 Access Via Presigned URLs**

When user wants to open a manual:

* backend generates a one-time URL
* expires within minutes
* can only access that single file

Presigned URLs require:

* yacht_signature
* user authentication
* request validation

### **6.3 No Direct Public Access**

Documents are NEVER:

* public
* cached on CDN
* returned directly from storage

---

# # 🟨 **7. Database Security**

### **7.1 Isolation Per Yacht**

Options:

* schema per yacht
* or table-level RBAC + yacht_id row-level policy

### **7.2 Row-Level Security (RLS)**

Even inside shared tables (if used), RLS ensures:

> “A query returns only rows matching the user’s yacht_id.”

### **7.3 Audit Logging**

Track:

* logins
* file uploads
* deletions
* work order modifications
* handover exports
* failed authentication

---

# # 🔍 **8. Compliance & Legal**

Even though CelesteOS does NOT store PII, we align with:

### **8.1 GDPR / UK Data Protection**

* Right to access
* Right to erase
* Data minimisation
* Purpose limitation

### **8.2 IMO cyber requirements (MSC-FAL.1/Circ.3)**

* network segmentation
* least privilege
* logging and monitoring

### **8.3 MLC / ISM Impacts**

Only applies to:

* hours of rest
* safety documents
* maintenance logs

CelesteOS stores these in a compliant manner.

### **8.4 Owner & Management NDA Enforcement**

Data isolation prevents cross-yacht leaks, even within a fleet.

---

# # 🟥 **9. Threat Model**

### **Threat: Unauthorised access to another yacht’s data**

Mitigation:

* per-yacht buckets
* per-yacht DB schema
* yacht signature required
* RLS
* no cross-account tokens

---

### **Threat: Compromised device on the yacht**

Mitigation:

* user-level permissions
* revoke tokens instantly
* no local caches beyond last few searches
* no admin access from agent

---

### **Threat: Intercepted NAS → cloud upload**

Mitigation:

* TLS 1.3
* SHA256 verification
* chunk-level signing
* HMAC-bound yacht_signature

---

### **Threat: Cloud breach**

Mitigation:

* encrypted buckets
* no PII
* zero public endpoints
* DB encryption
* audit logs
* blast radius limited per yacht

---

### **Threat: Rogue crew member**

Mitigation:

* role-based permissions
* action logging
* token revocation
* limited export ability

---

# # 🏁 **10. Summary**

CelesteOS implements:

* **Cloud-first strong encryption**
* **Per-yacht isolation**
* **Secure NAS ingestion**
* **Cryptographic yacht identities**
* **Strong user auth**
* **Strict API validation**
* **No PII**
* **Threat model coverage**

This creates a system owners can trust with the vessel’s **engineering memory**, without exposing any sensitive operational or personal data.

---
