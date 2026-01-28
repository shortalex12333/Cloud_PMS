# Azure Email Integration Specification — Handover Export System

> **Document**: `IMPL_EMAIL_AZURE_INTEGRATION.md`
> **Created**: 2026-01-14
> **Purpose**: Complete specification for Microsoft Azure OAuth + Graph API integration for handover email extraction
> **Target Repo**: https://github.com/shortalex12333/handover_export
> **For**: Claude B implementation

---

## Context: Two Handover Sources

The `handover_export` system handles **TWO sources** of handover entries:

| Source | Priority | How It Works |
|--------|----------|--------------|
| **User-Created Entries** | PRIMARY | Users add notes to `handover_entries` table directly via UI → Filter by `user_id` → Generate draft → Sign → Export |
| **Email Extraction** | SECONDARY | Fetch from Outlook → AI classify → AI summarize → Create `handover_entries` → Same export flow |

**This document covers the EMAIL EXTRACTION source only.** For user-created entry export, see `10_supabase_schema.md` and `16_api_endpoints.md`.

---

## Executive Summary

This document specifies how to integrate Microsoft Outlook emails into the Celeste handover system using Azure AD OAuth2 and Microsoft Graph API. The system extracts, classifies, and summarises emails into handover-ready format that feeds into the same `handover_entries` table as user-created notes.

**Source Analysis:**
- `/Users/celeste7/Documents/MICROSOFT APP/` - Existing Azure app implementation
- `MVP_Email_Handover.json` - Working n8n workflow (to be converted to Python)

---

## Part 1: Azure AD App Registration

### Current Configuration

```yaml
Azure App Details:
  App Name: CelesteOS.Outlook
  App ID (Client ID): a744caeb-9896-4dbf-8b85-d5e07dba935c
  Tenant ID: d44c2402-b515-4d6d-a392-5cfc88ae53bb
  Publisher Domain: shortalexhotmailco.onmicrosoft.com
  Sign-in Audience: AzureADMyOrg (single tenant)
  Token Version: v2.0
```

### Redirect URIs

```yaml
Development:
  - http://localhost:8002 (public client)
  - http://localhost:8003/auth/callback (public client)

Production:
  - https://celeste7.ai/auth/microsoft/callback (web)
```

### Required Permissions (Microsoft Graph API)

| Permission | Type | ID | Purpose |
|------------|------|-----|---------|
| Mail.Read | Delegated | 810c84a8-4a9e-49e6-bf7d-12d183f40d01 | Read user mailbox |
| MailboxSettings.Read | Delegated | 7427e0e9-2fba-42fe-b0c0-848c9e6a8182 | Read mailbox folder structure |
| User.Read | Delegated | e1fe6dd8-ba31-4d61-89e7-88639da4683d | Read user profile |
| offline_access | Delegated | 37f7f235-527c-4136-accd-4a02d197296e | Maintain access (refresh tokens) |

### Security Configuration

```yaml
Public Client Flow: Enabled (allowPublicClient: true)
Implicit Grant: Disabled (no ID/Access token issuance)
OAuth2 Post Response: Disabled
PKCE: Required for public clients
```

---

## Part 2: Authentication Flow

### OAuth2 Authorization Code Flow with PKCE

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Browser  │     │  Celeste Backend │     │ Microsoft Azure │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                        │
         │ 1. Click "Connect Email"                       │
         │──────────────────────>│                        │
         │                       │                        │
         │                       │ 2. Generate PKCE       │
         │                       │    code_verifier +     │
         │                       │    code_challenge      │
         │                       │                        │
         │ 3. Redirect to Microsoft login                 │
         │<──────────────────────│                        │
         │                       │                        │
         │ 4. User authenticates │                        │
         │───────────────────────────────────────────────>│
         │                       │                        │
         │ 5. Redirect with auth code                     │
         │<───────────────────────────────────────────────│
         │                       │                        │
         │ 6. Forward auth code  │                        │
         │──────────────────────>│                        │
         │                       │                        │
         │                       │ 7. Exchange code for tokens
         │                       │─────────────────────────>
         │                       │                        │
         │                       │ 8. Receive tokens      │
         │                       │<─────────────────────────
         │                       │                        │
         │                       │ 9. Store tokens        │
         │                       │    (encrypted in DB)   │
         │                       │                        │
         │ 10. Show success      │                        │
         │<──────────────────────│                        │
         │                       │                        │
```

### Token Management

```python
# Token storage schema (from existing implementation)
CREATE TABLE user_tokens (
    user_id TEXT PRIMARY KEY,
    user_email TEXT,
    access_token TEXT,          # Encrypted at rest
    refresh_token TEXT,         # Encrypted at rest
    expires_at INTEGER,         # Unix timestamp
    created_at INTEGER,
    updated_at INTEGER
);
```

### Token Refresh Logic

```python
def get_valid_access_token(user_id: str) -> str:
    """Get valid access token, refreshing if needed"""
    token_info = get_user_token(user_id)

    if not token_info:
        raise AuthenticationRequired("User not authenticated")

    now = int(datetime.now().timestamp())

    # Token valid for at least 5 minutes
    if token_info['expires_at'] > now + 300:
        return token_info['access_token']

    # Refresh token
    if token_info['refresh_token']:
        new_tokens = refresh_access_token(token_info['refresh_token'])
        store_user_token(user_id, token_info['user_email'], new_tokens)
        return new_tokens['access_token']

    raise TokenExpired("Token expired and cannot be refreshed")
```

---

## Part 3: Microsoft Graph API Integration

### Core Endpoints

```yaml
Base URL: https://graph.microsoft.com/v1.0

Endpoints:
  User Profile: /me
  Messages: /me/messages
  Folders: /me/mailFolders
  Search: /me/messages?$search="{query}"
  Message Detail: /me/messages/{id}
```

### Email Search Query Parameters

```python
# Graph API query builder
def build_email_query(
    search_query: str = None,
    days_back: int = 90,
    max_results: int = 100,
    folder_id: str = None
) -> dict:
    """Build Microsoft Graph API query parameters"""

    params = {
        '$top': min(max_results, 999),
        '$select': 'id,subject,from,receivedDateTime,bodyPreview,body,isRead,hasAttachments,importance,conversationId',
        '$orderby': 'receivedDateTime desc'
    }

    filters = []

    if search_query:
        # Sanitize query for Graph search syntax
        sanitized = search_query.replace('"', '').strip()
        params['$search'] = f'"{sanitized}"'

    if days_back and days_back > 0:
        cutoff = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
        filters.append(f"receivedDateTime ge {cutoff}")

    if filters:
        params['$filter'] = ' and '.join(filters)

    return params
```

### Rate Limiting Handler

```python
def make_graph_request(method: str, url: str, max_retries: int = 3, **kwargs) -> dict:
    """Make Graph API request with rate limit handling"""

    for attempt in range(max_retries + 1):
        response = session.request(method, url, headers=get_headers(), **kwargs)

        if response.status_code == 429:
            # Respect Retry-After header
            retry_after = int(response.headers.get('Retry-After', 60))
            if attempt < max_retries:
                logger.warning(f"Rate limit hit, waiting {retry_after}s")
                time.sleep(retry_after)
                continue
            raise RateLimitExceeded()

        if response.status_code == 503:
            # Exponential backoff for service unavailable
            wait = min(2 ** attempt, 60)
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response.json()
```

---

## Part 4: Email Processing Pipeline

### Overview (from n8n workflow analysis)

The n8n workflow `MVP_Email_Handover.json` implements a multi-stage pipeline:

```
Webhook Trigger (POST /export-outlook)
    ↓
Extract Subject & Body
    ↓
Add Short ID + Deeplink
    ↓
┌─────────────────────────────────────┐
│ Parallel AI Classification          │
│   ├─ Subject → Category             │
│   └─ Body → Category + Summary      │
└─────────────────────────────────────┘
    ↓
Merge Results
    ↓
Group by Category
    ↓
Batch Summaries
    ↓
Group by Category + Subject
    ↓
AI Merge Summaries (GPT-4o-mini)
    ↓
Deduplicate Summaries & Actions
    ↓
Final Formatter (JSON structure)
    ↓
HTML Converter
    ↓
Prepare for Email
    ↓
Send via Microsoft Outlook
```

### Handover Categories (from n8n workflow)

```python
HANDOVER_CATEGORIES = [
    "Electrical",
    "Projects",
    "Financial",
    "Galley Laundry",
    "Risk",
    "Admin",
    "Fire Safety",
    "Tenders",
    "Logistics",
    "Deck",
    "General Outstanding"
]
```

### Domain Code Mapping

Map n8n categories to 18_handover_buckets domain codes:

| n8n Category | Domain Code | Presentation Bucket |
|--------------|-------------|---------------------|
| Electrical | ENG-03 | Engineering |
| Projects | ADM-04 | Admin_Compliance |
| Financial | ADM-03 | Admin_Compliance |
| Galley Laundry | INT-02, INT-03 | Interior |
| Risk | CMD-01 | Command |
| Admin | ADM-01, ADM-02 | Admin_Compliance |
| Fire Safety | ENG-08 | Engineering |
| Tenders | DECK-03 | Deck |
| Logistics | ADM-05 | Admin_Compliance |
| Deck | DECK-01 to DECK-06 | Deck |
| General Outstanding | Various | Per context |

---

## Part 5: Python Implementation Specification

### Directory Structure for handover_export Repo

```
handover_export/
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Environment configuration
│   ├── main.py                   # Entry point
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── azure_oauth.py        # OAuth2 + PKCE flow
│   │   ├── token_manager.py      # Token storage/refresh
│   │   └── middleware.py         # Auth middleware
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── client.py             # Microsoft Graph client
│   │   ├── email_fetcher.py      # Email retrieval
│   │   └── rate_limiter.py       # Rate limit handling
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── extractor.py          # Email content extraction
│   │   ├── classifier.py         # AI classification (category)
│   │   ├── summarizer.py         # AI summarization
│   │   ├── deduplicator.py       # Duplicate detection
│   │   ├── merger.py             # Summary merging
│   │   └── formatter.py          # Output formatting
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── openai_client.py      # OpenAI API wrapper
│   │   └── prompts.py            # Prompt templates
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   ├── html_generator.py     # HTML report generation
│   │   ├── pdf_generator.py      # PDF generation
│   │   └── email_sender.py       # Email dispatch
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── supabase_client.py    # Supabase integration
│   │   └── file_storage.py       # File storage handling
│   │
│   └── api/
│       ├── __init__.py
│       ├── routes.py             # FastAPI routes
│       └── schemas.py            # Pydantic models
│
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_graph.py
│   ├── test_pipeline.py
│   └── test_export.py
│
└── docs/
    ├── api.md
    ├── azure_setup.md
    └── deployment.md
```

### Core Classes

#### 1. Email Extractor

```python
# src/pipeline/extractor.py
from dataclasses import dataclass
from typing import List, Optional
import re

@dataclass
class ExtractedEmail:
    """Extracted email data structure"""
    short_id: str
    email_id: str
    conversation_id: str
    subject: str
    body: str
    body_preview: str
    sender: str
    received_at: str
    has_attachments: bool
    outlook_link: str

class EmailExtractor:
    """Extract and normalize email content"""

    def __init__(self):
        self.html_tag_pattern = re.compile(r'<[^>]+>')

    def extract(self, emails: List[dict], start_index: int = 1) -> List[ExtractedEmail]:
        """Extract structured data from raw Graph API emails"""
        extracted = []

        for idx, email in enumerate(emails, start=start_index):
            short_id = f"E{idx}"

            # Generate Outlook deeplink
            item_id = email.get('id', '')
            encoded_id = quote(item_id, safe='')
            outlook_link = f"https://outlook.office365.com/mail/deeplink/read/{encoded_id}?ItemID={encoded_id}&exvsurl=1"

            # Extract body content
            body_obj = email.get('body', {})
            body_content = body_obj.get('content', email.get('bodyPreview', ''))

            # Strip HTML if present
            if body_obj.get('contentType') == 'html':
                body_content = self._strip_html(body_content)

            extracted.append(ExtractedEmail(
                short_id=short_id,
                email_id=email.get('id', ''),
                conversation_id=email.get('conversationId', ''),
                subject=email.get('subject', '(no subject)'),
                body=body_content,
                body_preview=email.get('bodyPreview', ''),
                sender=self._extract_sender(email.get('from', {})),
                received_at=email.get('receivedDateTime', ''),
                has_attachments=email.get('hasAttachments', False),
                outlook_link=outlook_link
            ))

        return extracted

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        text = self.html_tag_pattern.sub('', html)
        return ' '.join(text.split()).strip()

    def _extract_sender(self, from_obj: dict) -> str:
        """Extract sender name/email from Graph API format"""
        email_addr = from_obj.get('emailAddress', {})
        name = email_addr.get('name', '')
        address = email_addr.get('address', '')
        return f"{name} <{address}>" if name else address
```

#### 2. AI Classifier

```python
# src/pipeline/classifier.py
from dataclasses import dataclass
from typing import Optional
from src.ai.openai_client import OpenAIClient

@dataclass
class ClassificationResult:
    """Classification result structure"""
    short_id: str
    category: str
    summary: str
    confidence: float

CLASSIFICATION_PROMPT = """
You are a maritime handover classification and summarisation assistant.

Your task:
1. Categorise the following EMAIL into ONE of the official handover categories.
2. Write a short professional summary (under 40 words) describing the main point or action.
3. Use 2nd person tone ("You need to...").
4. Output strict JSON only.

Choose only from this exact list of categories:
- Electrical
- Projects
- Financial
- Galley Laundry
- Risk
- Admin
- Fire Safety
- Tenders
- Logistics
- Deck
- General Outstanding

Rules:
- Choose exactly ONE category.
- Never invent or modify category names.
- Keep the summary factual and concise.
- Output must strictly follow the schema.

Schema:
{
  "shortId": "{short_id}",
  "category": "one of the categories above",
  "summary": "concise professional summary under 40 words"
}

Email subject: {subject}
Email body (first 100 words): {body}

Output (strict JSON only):
"""

class EmailClassifier:
    """Classify emails into handover categories using AI"""

    def __init__(self, openai_client: OpenAIClient):
        self.client = openai_client

    async def classify(self, email: ExtractedEmail) -> ClassificationResult:
        """Classify a single email"""

        # Trim body to 100 words
        body_words = email.body.split()[:100]
        trimmed_body = ' '.join(body_words)

        prompt = CLASSIFICATION_PROMPT.format(
            short_id=email.short_id,
            subject=email.subject,
            body=trimmed_body
        )

        response = await self.client.complete(
            prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"}
        )

        result = json.loads(response)

        return ClassificationResult(
            short_id=result.get('shortId', email.short_id),
            category=result.get('category', 'General Outstanding'),
            summary=result.get('summary', 'No summary generated.'),
            confidence=0.9  # TODO: Extract from model response
        )

    async def classify_batch(self, emails: List[ExtractedEmail]) -> List[ClassificationResult]:
        """Classify multiple emails concurrently"""
        tasks = [self.classify(email) for email in emails]
        return await asyncio.gather(*tasks)
```

#### 3. Summary Merger

```python
# src/pipeline/merger.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class MergedHandover:
    """Merged handover entry structure"""
    merge_key: str
    category: str
    subject_group: str
    subject: str
    summary: str
    actions: List[Dict]
    source_ids: List[Dict]

MERGE_PROMPT = """
You are a maritime engineering handover assistant.

Context:
You will receive multiple email summaries about the same subject group: "{subject_group}"
within the category "{category}". Your role is to produce a **concise, professional, and action-oriented handover entry**.

Instructions:
1. **Merge notes** that are clearly duplicates or reworded versions of the same point.
2. **Preserve distinctions** when they differ by sender, attachments, or time-specific details.
3. **Summarise precisely** — avoid vague or filler language.
4. **Use second person** ("You need to...").
5. **Actions:** Extract all required work as discrete items.
   - Each must have a clear *priority*: CRITICAL, HIGH, or NORMAL.
   - Each must contain one focused instruction.
6. **Keep subject and summary concise and professional**.
7. **Output strict JSON only**.

Schema:
{
  "handover": {
    "subject": "string (concise, cleaned-up title)",
    "summary": "string (2–3 sentences summarising the situation)",
    "actions": [
      { "priority": "CRITICAL" | "HIGH" | "NORMAL", "task": "string", "subTasks": [] }
    ],
    "params": []
  }
}

Input Notes:
{notes}

Output (strict JSON only):
"""

class SummaryMerger:
    """Merge multiple email summaries into handover entries"""

    def __init__(self, openai_client: OpenAIClient):
        self.client = openai_client

    def group_by_category_subject(
        self,
        classifications: List[ClassificationResult],
        emails: List[ExtractedEmail]
    ) -> Dict[str, List]:
        """Group classifications by category and normalized subject"""

        groups = {}
        email_map = {e.short_id: e for e in emails}

        for cls in classifications:
            email = email_map.get(cls.short_id)
            if not email:
                continue

            subject_group = self._normalize_subject(email.subject)
            key = f"{cls.category}::{subject_group}"

            if key not in groups:
                groups[key] = {
                    'category': cls.category,
                    'subject_group': subject_group,
                    'merge_key': self._build_merge_key(cls.category, subject_group),
                    'notes': [],
                    'source_ids': []
                }

            groups[key]['notes'].append({
                'subject': email.subject,
                'summary': cls.summary
            })
            groups[key]['source_ids'].append({
                'short_id': email.short_id,
                'summaryId': f"S{len(groups[key]['source_ids']) + 1}",
                'link': email.outlook_link
            })

        return groups

    async def merge_group(self, group: dict) -> MergedHandover:
        """Merge a group of summaries into a single handover"""

        notes_text = '\n\n'.join([
            f"({i+1}) Subject: {n['subject']}\nSummary: {n['summary']}"
            for i, n in enumerate(group['notes'])
        ])

        prompt = MERGE_PROMPT.format(
            subject_group=group['subject_group'],
            category=group['category'],
            notes=notes_text
        )

        response = await self.client.complete(
            prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        result = json.loads(response)
        handover = result.get('handover', {})

        return MergedHandover(
            merge_key=group['merge_key'],
            category=group['category'],
            subject_group=group['subject_group'],
            subject=handover.get('subject', group['subject_group']),
            summary=handover.get('summary', ''),
            actions=handover.get('actions', []),
            source_ids=group['source_ids']
        )

    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject for grouping"""
        normalized = subject.lower()
        normalized = re.sub(r'urgent[:\-]?\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
        return normalized.strip()

    def _build_merge_key(self, category: str, subject_group: str) -> str:
        """Build unique merge key"""
        return re.sub(r'[^a-z0-9]', '', f"{category}_{subject_group}".lower())
```

---

## Part 6: Supabase Integration

### Database Schema (handover_export specific)

```sql
-- ============================================================================
-- TABLE: email_extraction_jobs
-- Purpose: Track email extraction job runs
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id),

    -- Job configuration
    email_filter_query TEXT,
    days_back INTEGER DEFAULT 90,
    max_emails INTEGER DEFAULT 500,

    -- Job status
    status TEXT NOT NULL DEFAULT 'pending',
    -- Values: 'pending', 'fetching', 'processing', 'completed', 'failed'

    -- Results
    emails_fetched INTEGER DEFAULT 0,
    emails_classified INTEGER DEFAULT 0,
    handovers_generated INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error tracking
    error_message TEXT,
    error_stack TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN (
        'pending', 'fetching', 'processing', 'completed', 'failed'
    ))
);

-- ============================================================================
-- TABLE: email_classifications
-- Purpose: Store classified email summaries
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES email_extraction_jobs(id) ON DELETE CASCADE,
    vessel_id UUID NOT NULL,

    -- Email reference
    short_id TEXT NOT NULL,
    email_id TEXT NOT NULL,           -- Graph API message ID
    conversation_id TEXT,

    -- Email metadata
    subject TEXT NOT NULL,
    sender TEXT,
    received_at TIMESTAMPTZ,
    has_attachments BOOLEAN DEFAULT FALSE,
    outlook_link TEXT,

    -- Classification
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    confidence DECIMAL(3,2),

    -- Domain mapping
    domain_code TEXT,                 -- e.g., 'ENG-03'
    presentation_bucket TEXT,         -- e.g., 'Engineering'

    -- Timestamps
    classified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_category CHECK (category IN (
        'Electrical', 'Projects', 'Financial', 'Galley Laundry',
        'Risk', 'Admin', 'Fire Safety', 'Tenders', 'Logistics',
        'Deck', 'General Outstanding'
    ))
);

-- ============================================================================
-- TABLE: email_handover_drafts
-- Purpose: Generated handover entries from email extraction
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_handover_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES email_extraction_jobs(id) ON DELETE CASCADE,
    vessel_id UUID NOT NULL,

    -- Grouping
    merge_key TEXT NOT NULL,
    category TEXT NOT NULL,
    subject_group TEXT NOT NULL,

    -- Content
    handover_subject TEXT NOT NULL,
    handover_summary TEXT NOT NULL,
    handover_actions JSONB DEFAULT '[]',

    -- Source tracking
    source_email_ids TEXT[],          -- Array of short_ids
    source_links JSONB,               -- Array of {shortId, link}

    -- Domain mapping
    domain_code TEXT,
    presentation_bucket TEXT,
    risk_tags TEXT[],

    -- Integration status
    exported_to_handover BOOLEAN DEFAULT FALSE,
    handover_entry_id UUID,           -- Link to handover_entries if exported

    -- Timestamps
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(job_id, merge_key)
);

-- Indexes
CREATE INDEX idx_email_jobs_vessel ON email_extraction_jobs(vessel_id, created_at DESC);
CREATE INDEX idx_email_classifications_job ON email_classifications(job_id, category);
CREATE INDEX idx_email_drafts_job ON email_handover_drafts(job_id, category);
```

### RLS Policies

```sql
-- RLS for email_extraction_jobs
ALTER TABLE email_extraction_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "email_jobs_vessel_isolation" ON email_extraction_jobs
    FOR ALL USING (vessel_id IN (
        SELECT yacht_id FROM user_profiles WHERE id = auth.uid()
    ));

-- RLS for email_classifications
ALTER TABLE email_classifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "email_classifications_vessel_isolation" ON email_classifications
    FOR ALL USING (vessel_id IN (
        SELECT yacht_id FROM user_profiles WHERE id = auth.uid()
    ));

-- RLS for email_handover_drafts
ALTER TABLE email_handover_drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "email_drafts_vessel_isolation" ON email_handover_drafts
    FOR ALL USING (vessel_id IN (
        SELECT yacht_id FROM user_profiles WHERE id = auth.uid()
    ));
```

---

## Part 7: API Endpoints

### FastAPI Routes

```python
# src/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/email-handover", tags=["email-handover"])

# Request/Response Models
class ExtractionRequest(BaseModel):
    """Request to start email extraction"""
    email_filter_query: Optional[str] = None
    days_back: int = 90
    max_emails: int = 500

class ExtractionJobResponse(BaseModel):
    """Extraction job status"""
    job_id: str
    status: str
    emails_fetched: int
    emails_classified: int
    handovers_generated: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

class HandoverDraftResponse(BaseModel):
    """Generated handover draft"""
    id: str
    category: str
    subject: str
    summary: str
    actions: List[dict]
    source_emails: List[dict]
    domain_code: Optional[str]
    presentation_bucket: Optional[str]

# Endpoints

@router.post("/extract", response_model=ExtractionJobResponse)
async def start_extraction(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    vessel_id: str = Depends(get_vessel_context)
):
    """
    Start email extraction job

    Triggers background processing of user's emails:
    1. Fetch emails from Microsoft Graph
    2. Classify into categories
    3. Summarize and merge
    4. Generate handover drafts
    """
    # Create job record
    job = await create_extraction_job(
        user_id=user_id,
        vessel_id=vessel_id,
        config=request
    )

    # Start background processing
    background_tasks.add_task(
        run_extraction_pipeline,
        job_id=job.id,
        user_id=user_id
    )

    return ExtractionJobResponse(
        job_id=str(job.id),
        status=job.status,
        emails_fetched=0,
        emails_classified=0,
        handovers_generated=0,
        started_at=None,
        completed_at=None,
        error_message=None
    )

@router.get("/jobs/{job_id}", response_model=ExtractionJobResponse)
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get extraction job status"""
    job = await get_extraction_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ExtractionJobResponse(
        job_id=str(job.id),
        status=job.status,
        emails_fetched=job.emails_fetched,
        emails_classified=job.emails_classified,
        handovers_generated=job.handovers_generated,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )

@router.get("/jobs/{job_id}/drafts", response_model=List[HandoverDraftResponse])
async def get_job_drafts(
    job_id: str,
    category: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get generated handover drafts for a job"""
    drafts = await get_handover_drafts(job_id, category=category)

    return [
        HandoverDraftResponse(
            id=str(d.id),
            category=d.category,
            subject=d.handover_subject,
            summary=d.handover_summary,
            actions=d.handover_actions,
            source_emails=d.source_links,
            domain_code=d.domain_code,
            presentation_bucket=d.presentation_bucket
        )
        for d in drafts
    ]

@router.post("/jobs/{job_id}/export-to-handover")
async def export_to_handover(
    job_id: str,
    draft_ids: List[str],
    user_id: str = Depends(get_current_user),
    vessel_id: str = Depends(get_vessel_context)
):
    """
    Export selected drafts to handover_entries

    Creates handover_entries records from email extraction drafts.
    These will appear in the next handover draft generation.
    """
    exported = []

    for draft_id in draft_ids:
        entry_id = await export_draft_to_handover(
            draft_id=draft_id,
            user_id=user_id,
            vessel_id=vessel_id
        )
        exported.append({
            'draft_id': draft_id,
            'handover_entry_id': str(entry_id)
        })

    return {
        'success': True,
        'exported': exported,
        'count': len(exported)
    }

@router.post("/generate-report")
async def generate_report(
    job_id: str,
    format: str = "html",  # html, pdf
    user_id: str = Depends(get_current_user)
):
    """
    Generate handover report from extraction job

    Returns HTML or PDF document ready for export/email.
    """
    if format not in ['html', 'pdf']:
        raise HTTPException(status_code=400, detail="Invalid format")

    drafts = await get_handover_drafts(job_id)

    if format == 'html':
        html = await generate_html_report(drafts)
        return {'format': 'html', 'content': html}
    else:
        pdf_url = await generate_pdf_report(drafts)
        return {'format': 'pdf', 'url': pdf_url}
```

---

## Part 8: Environment Configuration

### Environment Variables

```bash
# .env.example

# Azure AD Configuration
AZURE_TENANT_ID=d44c2402-b515-4d6d-a392-5cfc88ae53bb
AZURE_CLIENT_ID=a744caeb-9896-4dbf-8b85-d5e07dba935c
AZURE_REDIRECT_URI=http://localhost:8003/auth/callback

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...

# Token Encryption
EMAIL_TOKEN_ENCRYPTION_KEY=your-32-byte-encryption-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Logging
LOG_LEVEL=INFO
```

### Requirements

```txt
# requirements.txt

# Web Framework
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0

# Microsoft Graph / Azure
msal>=1.26.0
requests>=2.31.0

# Database
supabase>=2.3.0
asyncpg>=0.29.0

# AI
openai>=1.10.0
tiktoken>=0.5.0

# PDF Generation
weasyprint>=60.0
jinja2>=3.1.0

# Utilities
python-dotenv>=1.0.0
python-dateutil>=2.8.0
httpx>=0.26.0

# Security
cryptography>=41.0.0
python-jose>=3.3.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```

---

## Part 9: Deployment Configuration

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  handover-export:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - EMAIL_TOKEN_ENCRYPTION_KEY=${EMAIL_TOKEN_ENCRYPTION_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Redis for job queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Part 10: Non-Negotiables

From both the Azure integration and 18_handover_buckets specifications:

1. **No silent email access** - User must explicitly authenticate
2. **No storage of plain text tokens** - Encrypt at rest
3. **No bypassing rate limits** - Respect Graph API Retry-After
4. **No auto-creation of handover entries** - User must confirm/export
5. **No classification modification** - AI classifies, user accepts or rejects
6. **No email content stored permanently** - Only summaries and references
7. **Invalid state returns appropriate HTTP status** (401, 403, 429, 409)
8. **All extraction jobs are auditable** - Full job history maintained
9. **Source email links preserved** - Always link back to Outlook
10. **Domain code mapping required** - Every classification maps to 18_handover_buckets taxonomy

---

## Related Documents

- `ANALYSIS_feasibility.md` - Gap analysis for handover system
- `10_supabase_schema.md` - Core handover schema
- `15_python_job_spec.md` - Python job specifications
- `16_api_endpoints.md` - Handover API endpoints
- `/Users/celeste7/Documents/MICROSOFT APP/yacht-email-reader/ENGINEER_HANDOFF.md` - Azure integration source
