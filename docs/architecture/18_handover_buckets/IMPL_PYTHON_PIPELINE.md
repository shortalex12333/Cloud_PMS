# Python Pipeline Specification — Email-to-Handover Workflow

> **Document**: `IMPL_PYTHON_PIPELINE.md`
> **Created**: 2026-01-14
> **Purpose**: Complete Python implementation spec converted from n8n MVP_Email_Handover.json
> **Target Repo**: https://github.com/shortalex12333/handover_export
> **For**: Claude B implementation

---

## Executive Summary

This document provides the complete Python implementation specification for the email-to-handover pipeline, converted from the working n8n workflow `MVP_Email_Handover.json`.

The pipeline transforms raw emails from Microsoft Graph API into structured handover entries suitable for crew shift changes.

---

## Part 1: Pipeline Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EMAIL-TO-HANDOVER PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   STAGE 1   │    │   STAGE 2   │    │   STAGE 3   │    │   STAGE 4   │       │
│  │   FETCH     │───>│   EXTRACT   │───>│  CLASSIFY   │───>│   GROUP     │       │
│  │   EMAILS    │    │   CONTENT   │    │   (AI)      │    │   BY TOPIC  │       │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   STAGE 5   │    │   STAGE 6   │    │   STAGE 7   │    │   STAGE 8   │       │
│  │   MERGE     │───>│  DEDUPE     │───>│   FORMAT    │───>│   EXPORT    │       │
│  │   (AI)      │    │             │    │   OUTPUT    │    │   (HTML/PDF)│       │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Stage Responsibilities

| Stage | Name | Input | Output | AI Used |
|-------|------|-------|--------|---------|
| 1 | Fetch Emails | Graph API query | Raw email list | No |
| 2 | Extract Content | Raw emails | ExtractedEmail[] | No |
| 3 | Classify | ExtractedEmail[] | ClassificationResult[] | GPT-4o-mini |
| 4 | Group by Topic | ClassificationResult[] | TopicGroups{} | No |
| 5 | Merge Summaries | TopicGroups{} | MergedHandover[] | GPT-4o-mini |
| 6 | Deduplicate | MergedHandover[] | DeduplicatedHandover[] | No |
| 7 | Format Output | DeduplicatedHandover[] | FormattedReport | No |
| 8 | Export | FormattedReport | HTML/PDF/Email | No |

---

## Part 2: Data Structures

### Core Types

```python
# src/pipeline/types.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"

class HandoverCategory(str, Enum):
    ELECTRICAL = "Electrical"
    PROJECTS = "Projects"
    FINANCIAL = "Financial"
    GALLEY_LAUNDRY = "Galley Laundry"
    RISK = "Risk"
    ADMIN = "Admin"
    FIRE_SAFETY = "Fire Safety"
    TENDERS = "Tenders"
    LOGISTICS = "Logistics"
    DECK = "Deck"
    GENERAL = "General Outstanding"

@dataclass
class RawEmail:
    """Raw email from Microsoft Graph API"""
    id: str
    subject: str
    body: Dict[str, Any]  # {content, contentType}
    body_preview: str
    from_address: Dict[str, Any]  # {emailAddress: {name, address}}
    received_datetime: str
    conversation_id: str
    has_attachments: bool
    importance: str

@dataclass
class ExtractedEmail:
    """Extracted and normalized email"""
    short_id: str              # E1, E2, etc.
    email_id: str
    conversation_id: str
    subject: str
    body_text: str             # HTML stripped
    body_preview: str
    sender_name: str
    sender_email: str
    received_at: datetime
    has_attachments: bool
    outlook_link: str

@dataclass
class ClassificationResult:
    """AI classification result"""
    short_id: str
    category: HandoverCategory
    summary: str
    confidence: float = 0.9

@dataclass
class TopicGroup:
    """Group of emails on the same topic"""
    merge_key: str
    category: HandoverCategory
    subject_group: str         # Normalized subject
    notes: List[Dict[str, str]]  # [{subject, summary}]
    source_ids: List[Dict[str, str]]  # [{shortId, summaryId, link}]

@dataclass
class HandoverAction:
    """Action item from handover"""
    priority: Priority
    task: str
    sub_tasks: List[str] = field(default_factory=list)

@dataclass
class MergedHandover:
    """Merged handover entry"""
    merge_key: str
    category: HandoverCategory
    subject_group: str
    subject: str
    summary: str
    actions: List[HandoverAction]
    source_ids: List[Dict[str, str]]
    domain_code: Optional[str] = None
    presentation_bucket: Optional[str] = None

@dataclass
class FormattedReport:
    """Final formatted report"""
    meta: Dict[str, Any]
    sections: Dict[str, List[MergedHandover]]
    html: str
    generated_at: datetime
```

---

## Part 3: Stage Implementations

### Stage 1: Fetch Emails

```python
# src/pipeline/stages/fetch_emails.py
from typing import List
from datetime import datetime, timedelta
from src.graph.client import GraphClient
from src.pipeline.types import RawEmail

class FetchEmailsStage:
    """
    Stage 1: Fetch emails from Microsoft Graph API

    n8n equivalent: Webhook trigger + Graph API call
    """

    def __init__(self, graph_client: GraphClient):
        self.graph = graph_client

    async def execute(
        self,
        query: str = None,
        days_back: int = 90,
        max_emails: int = 500,
        folder_id: str = None
    ) -> List[RawEmail]:
        """Fetch emails matching criteria"""

        # Build query parameters
        params = {
            '$top': min(max_emails, 999),
            '$select': ','.join([
                'id', 'subject', 'from', 'receivedDateTime',
                'bodyPreview', 'body', 'isRead', 'hasAttachments',
                'importance', 'conversationId'
            ]),
            '$orderby': 'receivedDateTime desc'
        }

        # Date filter
        if days_back > 0:
            cutoff = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
            params['$filter'] = f"receivedDateTime ge {cutoff}"

        # Search query
        if query:
            sanitized = query.replace('"', '').strip()
            params['$search'] = f'"{sanitized}"'

        # Fetch from Graph API
        endpoint = f"/me/mailFolders/{folder_id}/messages" if folder_id else "/me/messages"
        response = await self.graph.get(endpoint, params=params)

        # Convert to RawEmail objects
        return [
            RawEmail(
                id=msg['id'],
                subject=msg.get('subject', '(no subject)'),
                body=msg.get('body', {}),
                body_preview=msg.get('bodyPreview', ''),
                from_address=msg.get('from', {}),
                received_datetime=msg.get('receivedDateTime', ''),
                conversation_id=msg.get('conversationId', ''),
                has_attachments=msg.get('hasAttachments', False),
                importance=msg.get('importance', 'normal')
            )
            for msg in response.get('value', [])
        ]
```

### Stage 2: Extract Content

```python
# src/pipeline/stages/extract_content.py
import re
from typing import List
from urllib.parse import quote
from datetime import datetime
from dateutil import parser
from src.pipeline.types import RawEmail, ExtractedEmail

class ExtractContentStage:
    """
    Stage 2: Extract and normalize email content

    n8n equivalent: "Extract Subject & Body" + "Add Short Id"
    """

    def __init__(self):
        self.html_pattern = re.compile(r'<[^>]+>')
        self.whitespace_pattern = re.compile(r'\s+')

    def execute(self, emails: List[RawEmail], start_index: int = 1) -> List[ExtractedEmail]:
        """Extract structured data from raw emails"""

        extracted = []

        for idx, email in enumerate(emails, start=start_index):
            short_id = f"E{idx}"

            # Generate Outlook deeplink
            encoded_id = quote(email.id, safe='')
            outlook_link = (
                f"https://outlook.office365.com/mail/deeplink/read/{encoded_id}"
                f"?ItemID={encoded_id}&exvsurl=1"
            )

            # Extract body text
            body_content = email.body.get('content', email.body_preview)
            if email.body.get('contentType') == 'html':
                body_content = self._strip_html(body_content)

            # Parse sender
            from_addr = email.from_address.get('emailAddress', {})
            sender_name = from_addr.get('name', '')
            sender_email = from_addr.get('address', '')

            # Parse datetime
            try:
                received_at = parser.parse(email.received_datetime)
            except:
                received_at = datetime.now()

            extracted.append(ExtractedEmail(
                short_id=short_id,
                email_id=email.id,
                conversation_id=email.conversation_id,
                subject=email.subject,
                body_text=body_content,
                body_preview=email.body_preview,
                sender_name=sender_name,
                sender_email=sender_email,
                received_at=received_at,
                has_attachments=email.has_attachments,
                outlook_link=outlook_link
            ))

        return extracted

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        text = self.html_pattern.sub('', html)
        text = self.whitespace_pattern.sub(' ', text)
        return text.strip()
```

### Stage 3: Classify (AI)

```python
# src/pipeline/stages/classify.py
import asyncio
import json
from typing import List
from src.ai.openai_client import OpenAIClient
from src.pipeline.types import ExtractedEmail, ClassificationResult, HandoverCategory

CLASSIFY_SYSTEM_PROMPT = """You are a precise maritime email subject classifier."""

CLASSIFY_USER_PROMPT = """
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

class ClassifyStage:
    """
    Stage 3: Classify emails using AI

    n8n equivalent: "Prompt Email Extraction" + "DS Blog" + "AI Process Response1"
    """

    def __init__(self, openai_client: OpenAIClient):
        self.ai = openai_client
        self.max_concurrent = 10  # Rate limit protection

    async def execute(self, emails: List[ExtractedEmail]) -> List[ClassificationResult]:
        """Classify all emails with concurrency control"""

        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [self._classify_with_semaphore(email, semaphore) for email in emails]
        return await asyncio.gather(*tasks)

    async def _classify_with_semaphore(
        self,
        email: ExtractedEmail,
        semaphore: asyncio.Semaphore
    ) -> ClassificationResult:
        """Classify single email with semaphore"""
        async with semaphore:
            return await self._classify_single(email)

    async def _classify_single(self, email: ExtractedEmail) -> ClassificationResult:
        """Classify a single email"""

        # Trim body to 100 words
        body_words = email.body_text.split()[:100]
        trimmed_body = ' '.join(body_words)

        prompt = CLASSIFY_USER_PROMPT.format(
            short_id=email.short_id,
            subject=email.subject,
            body=trimmed_body
        )

        try:
            response = await self.ai.complete(
                system_prompt=CLASSIFY_SYSTEM_PROMPT,
                user_prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            result = json.loads(response)

            # Validate and map category
            category_str = result.get('category', 'General Outstanding')
            try:
                category = HandoverCategory(category_str)
            except ValueError:
                category = HandoverCategory.GENERAL

            return ClassificationResult(
                short_id=result.get('shortId', email.short_id),
                category=category,
                summary=result.get('summary', 'No summary generated.'),
                confidence=0.9
            )

        except Exception as e:
            # Fallback on error
            return ClassificationResult(
                short_id=email.short_id,
                category=HandoverCategory.GENERAL,
                summary=f"Classification error: {str(e)}",
                confidence=0.0
            )
```

### Stage 4: Group by Topic

```python
# src/pipeline/stages/group_topics.py
import re
from typing import List, Dict
from src.pipeline.types import (
    ExtractedEmail, ClassificationResult, TopicGroup, HandoverCategory
)

class GroupTopicsStage:
    """
    Stage 4: Group classified emails by category and subject

    n8n equivalent: "Group Emails by Equipment" + "Batch Summaries" + "Group summaries by category + subject"
    """

    def execute(
        self,
        classifications: List[ClassificationResult],
        emails: List[ExtractedEmail]
    ) -> Dict[str, TopicGroup]:
        """Group classifications by category and normalized subject"""

        email_map = {e.short_id: e for e in emails}
        groups: Dict[str, TopicGroup] = {}

        for cls in classifications:
            email = email_map.get(cls.short_id)
            if not email:
                continue

            subject_group = self._normalize_subject(email.subject)
            key = f"{cls.category.value}::{subject_group}"
            merge_key = self._build_merge_key(cls.category.value, subject_group)

            if key not in groups:
                groups[key] = TopicGroup(
                    merge_key=merge_key,
                    category=cls.category,
                    subject_group=subject_group,
                    notes=[],
                    source_ids=[]
                )

            # Add note
            groups[key].notes.append({
                'subject': email.subject,
                'summary': cls.summary
            })

            # Add source reference
            summary_id = f"S{len(groups[key].source_ids) + 1}"
            groups[key].source_ids.append({
                'shortId': email.short_id,
                'summaryId': summary_id,
                'link': email.outlook_link
            })

        return groups

    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject for grouping"""
        normalized = subject.lower()
        # Remove common prefixes
        normalized = re.sub(r'^(re:|fw:|fwd:)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'urgent[:\-]?\s*', '', normalized, flags=re.IGNORECASE)
        # Remove non-alphanumeric
        normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
        return normalized.strip()

    def _build_merge_key(self, category: str, subject_group: str) -> str:
        """Build unique merge key"""
        combined = f"{category}_{subject_group}"
        return re.sub(r'[^a-z0-9]', '', combined.lower())
```

### Stage 5: Merge Summaries (AI)

```python
# src/pipeline/stages/merge_summaries.py
import asyncio
import json
from typing import List, Dict
from src.ai.openai_client import OpenAIClient
from src.pipeline.types import (
    TopicGroup, MergedHandover, HandoverAction, Priority, HandoverCategory
)

MERGE_SYSTEM_PROMPT = """You are a precise maritime handover summarisation assistant that merges multiple notes into clear, structured JSON output."""

MERGE_USER_PROMPT = """
You are a maritime engineering handover assistant.

Context:
You will receive multiple email summaries about the same subject group: "{subject_group}"
within the category "{category}". Your role is to produce a **concise, professional, and action-oriented handover entry**.

Instructions:
1. **Merge notes** that are clearly duplicates or reworded versions of the same point.
2. **Preserve distinctions** when they differ by:
   - Sender or source (implying separate actions or updates)
   - Attachments or linked references
   - Time-specific details
3. **Summarise precisely** — avoid vague or filler language like "ensure communication is maintained".
4. **Use second person** ("You need to...").
5. **Actions:** Extract all required work as discrete items.
   - Each must have a clear *priority*: CRITICAL, HIGH, or NORMAL.
   - Each must contain one focused instruction.
   - If an email references a file, document, or attachment, represent it as a **subTask**, not a separate note.
6. **Keep subject and summary concise and professional** (plain English, no jargon or redundant phrases).
7. **Output strict JSON only** following this schema — do not include commentary.

Schema:
{{
  "handover": {{
    "subject": "string (concise, cleaned-up title)",
    "summary": "string (2–3 sentences summarising the situation)",
    "actions": [
      {{ "priority": "CRITICAL" | "HIGH" | "NORMAL", "task": "string", "subTasks": [] }}
    ],
    "params": []
  }}
}}

Input Notes:
{notes}

Output (strict JSON only):
"""

# Domain code mapping
CATEGORY_TO_DOMAIN = {
    HandoverCategory.ELECTRICAL: ('ENG-03', 'Engineering'),
    HandoverCategory.PROJECTS: ('ADM-04', 'Admin_Compliance'),
    HandoverCategory.FINANCIAL: ('ADM-03', 'Admin_Compliance'),
    HandoverCategory.GALLEY_LAUNDRY: ('INT-02', 'Interior'),
    HandoverCategory.RISK: ('CMD-01', 'Command'),
    HandoverCategory.ADMIN: ('ADM-01', 'Admin_Compliance'),
    HandoverCategory.FIRE_SAFETY: ('ENG-08', 'Engineering'),
    HandoverCategory.TENDERS: ('DECK-03', 'Deck'),
    HandoverCategory.LOGISTICS: ('ADM-05', 'Admin_Compliance'),
    HandoverCategory.DECK: ('DECK-01', 'Deck'),
    HandoverCategory.GENERAL: (None, None),
}

class MergeSummariesStage:
    """
    Stage 5: Merge grouped summaries into handover entries using AI

    n8n equivalent: "Prompt Builder2" + "DS Blog2" + "AI Response Processor2"
    """

    def __init__(self, openai_client: OpenAIClient):
        self.ai = openai_client
        self.max_concurrent = 5  # Lower limit for longer operations

    async def execute(self, groups: Dict[str, TopicGroup]) -> List[MergedHandover]:
        """Merge all groups with concurrency control"""

        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [
            self._merge_with_semaphore(group, semaphore)
            for group in groups.values()
        ]
        return await asyncio.gather(*tasks)

    async def _merge_with_semaphore(
        self,
        group: TopicGroup,
        semaphore: asyncio.Semaphore
    ) -> MergedHandover:
        """Merge single group with semaphore"""
        async with semaphore:
            return await self._merge_single(group)

    async def _merge_single(self, group: TopicGroup) -> MergedHandover:
        """Merge a single topic group"""

        # Format notes for prompt
        notes_text = '\n\n'.join([
            f"({i+1}) Subject: {n['subject']}\nSummary: {n['summary']}"
            for i, n in enumerate(group.notes)
        ])

        prompt = MERGE_USER_PROMPT.format(
            subject_group=group.subject_group,
            category=group.category.value,
            notes=notes_text
        )

        try:
            response = await self.ai.complete(
                system_prompt=MERGE_SYSTEM_PROMPT,
                user_prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response)
            handover = result.get('handover', {})

            # Parse actions
            actions = [
                HandoverAction(
                    priority=Priority(a.get('priority', 'NORMAL')),
                    task=a.get('task', ''),
                    sub_tasks=a.get('subTasks', [])
                )
                for a in handover.get('actions', [])
            ]

            # Get domain mapping
            domain_code, bucket = CATEGORY_TO_DOMAIN.get(
                group.category,
                (None, None)
            )

            return MergedHandover(
                merge_key=group.merge_key,
                category=group.category,
                subject_group=group.subject_group,
                subject=handover.get('subject', group.subject_group),
                summary=handover.get('summary', ''),
                actions=actions,
                source_ids=group.source_ids,
                domain_code=domain_code,
                presentation_bucket=bucket
            )

        except Exception as e:
            # Fallback on error
            return MergedHandover(
                merge_key=group.merge_key,
                category=group.category,
                subject_group=group.subject_group,
                subject=group.subject_group,
                summary=f"Merge error: {str(e)}",
                actions=[],
                source_ids=group.source_ids,
                domain_code=None,
                presentation_bucket=None
            )
```

### Stage 6: Deduplicate

```python
# src/pipeline/stages/deduplicate.py
from typing import List
from src.pipeline.types import MergedHandover, HandoverAction

class DeduplicateStage:
    """
    Stage 6: Deduplicate summaries and actions

    n8n equivalent: "Deduplicate Summaries & Actions"
    """

    def __init__(self, similarity_threshold: float = 0.9):
        self.threshold = similarity_threshold

    def execute(self, handovers: List[MergedHandover]) -> List[MergedHandover]:
        """Deduplicate handovers and their actions"""

        deduplicated = []

        for handover in handovers:
            # Deduplicate actions within handover
            unique_actions = self._dedupe_actions(handover.actions)

            deduplicated.append(MergedHandover(
                merge_key=handover.merge_key,
                category=handover.category,
                subject_group=handover.subject_group,
                subject=handover.subject,
                summary=handover.summary,
                actions=unique_actions,
                source_ids=handover.source_ids,
                domain_code=handover.domain_code,
                presentation_bucket=handover.presentation_bucket
            ))

        return deduplicated

    def _dedupe_actions(self, actions: List[HandoverAction]) -> List[HandoverAction]:
        """Remove duplicate actions"""
        unique = []
        seen_tasks = set()

        for action in actions:
            normalized = self._normalize(action.task)
            if normalized not in seen_tasks:
                seen_tasks.add(normalized)
                unique.append(action)

        return unique

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison"""
        return ''.join(c.lower() for c in text if c.isalnum())

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) == 0:
            return len(s2)
        if len(s2) == 0:
            return len(s1)

        matrix = [[0] * (len(s2) + 1) for _ in range(len(s1) + 1)]

        for i in range(len(s1) + 1):
            matrix[i][0] = i
        for j in range(len(s2) + 1):
            matrix[0][j] = j

        for i in range(1, len(s1) + 1):
            for j in range(1, len(s2) + 1):
                if s1[i-1] == s2[j-1]:
                    matrix[i][j] = matrix[i-1][j-1]
                else:
                    matrix[i][j] = min(
                        matrix[i-1][j-1] + 1,
                        matrix[i][j-1] + 1,
                        matrix[i-1][j] + 1
                    )

        return matrix[len(s1)][len(s2)]

    def _is_near_duplicate(self, text1: str, text2: str) -> bool:
        """Check if two strings are near-duplicates"""
        norm1 = self._normalize(text1)
        norm2 = self._normalize(text2)

        max_len = max(len(norm1), len(norm2))
        if max_len == 0:
            return True

        distance = self._levenshtein_distance(norm1, norm2)
        similarity = 1 - (distance / max_len)

        return similarity >= self.threshold
```

### Stage 7: Format Output

```python
# src/pipeline/stages/format_output.py
from typing import List, Dict
from datetime import datetime
from src.pipeline.types import MergedHandover, FormattedReport, Priority

class FormatOutputStage:
    """
    Stage 7: Format handovers into final report structure

    n8n equivalent: "Final Formatter"
    """

    def execute(self, handovers: List[MergedHandover]) -> FormattedReport:
        """Format handovers into structured report"""

        # Group by category
        sections: Dict[str, List[MergedHandover]] = {}
        for h in handovers:
            cat = h.category.value
            if cat not in sections:
                sections[cat] = []
            sections[cat].append(h)

        # Calculate statistics
        total_emails = sum(len(h.source_ids) for h in handovers)
        critical_count = sum(
            1 for h in handovers
            for a in h.actions if a.priority == Priority.CRITICAL
        )
        high_count = sum(
            1 for h in handovers
            for a in h.actions if a.priority == Priority.HIGH
        )

        meta = {
            'generatedAt': datetime.now().isoformat(),
            'totalSections': len(sections),
            'totalEmails': total_emails,
            'sectionsProcessed': len([s for s in sections.values() if s]),
            'criticalCount': critical_count,
            'highCount': high_count
        }

        # Generate HTML
        html = self._generate_html(sections, meta)

        return FormattedReport(
            meta=meta,
            sections=sections,
            html=html,
            generated_at=datetime.now()
        )

    def _generate_html(self, sections: Dict, meta: Dict) -> str:
        """Generate HTML report"""

        # Section order
        section_order = [
            'Electrical', 'Projects', 'Admin', 'Galley Laundry',
            'Risk', 'Fire Safety', 'Tenders', 'Logistics',
            'Deck', 'Financial', 'General Outstanding'
        ]

        sections_html = ''
        for section_name in section_order:
            if section_name not in sections:
                continue

            handovers = sections[section_name]
            items_html = ''

            for h in handovers:
                actions_html = ''
                for a in h.actions:
                    priority_class = a.priority.value.lower()
                    sub_tasks = ''.join(f'<li>{st}</li>' for st in a.sub_tasks)
                    sub_tasks_html = f'<ul>{sub_tasks}</ul>' if sub_tasks else ''

                    actions_html += f'''
                        <div class="action-item">
                            <span class="priority {priority_class}">[{a.priority.value}]</span>
                            {a.task}
                            {sub_tasks_html}
                        </div>
                    '''

                sources_html = ''.join(
                    f'<a href="{s["link"]}" target="_blank">{s["shortId"]}</a> '
                    for s in h.source_ids
                )

                items_html += f'''
                    <div class="handover-item">
                        <h3>{h.subject}</h3>
                        <div class="summary">{h.summary}</div>
                        <div class="actions">{actions_html}</div>
                        <div class="sources">Source Emails: {sources_html}</div>
                    </div>
                '''

            sections_html += f'''
                <div class="section">
                    <div class="section-header">{section_name.upper()}</div>
                    {items_html}
                </div>
            '''

        return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Yacht Handover Report - {meta['generatedAt'][:10]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; }}
        h1 {{ text-align: center; color: #003366; }}
        .meta {{ text-align: center; margin-bottom: 30px; color: #666; }}
        .section {{ margin-bottom: 40px; border-top: 3px solid #003366; padding-top: 20px; }}
        .section-header {{ font-size: 16px; font-weight: bold; margin-bottom: 15px; }}
        .handover-item {{ margin-bottom: 25px; padding: 15px; border: 1px solid #ccc; border-radius: 6px; }}
        .handover-item h3 {{ margin-top: 0; color: #003366; }}
        .summary {{ font-style: italic; margin: 10px 0; }}
        .actions {{ margin: 15px 0; }}
        .action-item {{ margin: 8px 0; }}
        .priority {{ font-weight: bold; padding: 2px 6px; margin-right: 8px; }}
        .critical {{ color: #d32f2f; }}
        .high {{ color: #f57c00; }}
        .normal {{ color: #1976d2; }}
        .sources {{ font-size: 12px; color: #666; margin-top: 10px; }}
        .sources a {{ margin-right: 10px; }}
    </style>
</head>
<body>
    <h1>YACHT HANDOVER REPORT</h1>
    <div class="meta">
        Generated: {meta['generatedAt']}<br>
        Sections: {meta['totalSections']} | Emails Processed: {meta['totalEmails']}
    </div>
    {sections_html}
</body>
</html>
        '''
```

### Stage 8: Export

```python
# src/pipeline/stages/export.py
from typing import Optional
from src.pipeline.types import FormattedReport
from src.export.pdf_generator import PDFGenerator
from src.export.email_sender import EmailSender

class ExportStage:
    """
    Stage 8: Export report to various formats

    n8n equivalent: "HTML Converter" + "Prepare for Email" + "Convert to Attachment" + "Send a message"
    """

    def __init__(
        self,
        pdf_generator: Optional[PDFGenerator] = None,
        email_sender: Optional[EmailSender] = None
    ):
        self.pdf = pdf_generator
        self.email = email_sender

    async def export_html(self, report: FormattedReport) -> str:
        """Export as HTML string"""
        return report.html

    async def export_pdf(self, report: FormattedReport, output_path: str) -> str:
        """Export as PDF file"""
        if not self.pdf:
            raise ValueError("PDF generator not configured")

        return await self.pdf.generate(report.html, output_path)

    async def send_email(
        self,
        report: FormattedReport,
        recipients: List[str],
        subject: Optional[str] = None
    ) -> dict:
        """Send report via email"""
        if not self.email:
            raise ValueError("Email sender not configured")

        # Generate subject if not provided
        if not subject:
            date_str = report.generated_at.strftime('%Y-%m-%d')
            sections = report.meta.get('sectionsProcessed', 0)
            emails = report.meta.get('totalEmails', 0)
            subject = f"Yacht Handover Report - {date_str} | {sections} Active Sections | {emails} Emails"

        # Prepare email body
        email_body = f"""
Please find attached the Yacht Handover Report for {date_str}.

This report contains:
- Technical summaries
- Key action items
- Direct email links
- Vendor details and deadlines

Sections with updates: {', '.join(report.sections.keys())}
"""

        return await self.email.send(
            recipients=recipients,
            subject=subject,
            body=email_body,
            html_attachment=report.html,
            attachment_name=f"Yacht_Handover_Report_{date_str}.html"
        )
```

---

## Part 4: Pipeline Orchestrator

```python
# src/pipeline/orchestrator.py
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Callable
from src.pipeline.types import FormattedReport
from src.pipeline.stages.fetch_emails import FetchEmailsStage
from src.pipeline.stages.extract_content import ExtractContentStage
from src.pipeline.stages.classify import ClassifyStage
from src.pipeline.stages.group_topics import GroupTopicsStage
from src.pipeline.stages.merge_summaries import MergeSummariesStage
from src.pipeline.stages.deduplicate import DeduplicateStage
from src.pipeline.stages.format_output import FormatOutputStage
from src.pipeline.stages.export import ExportStage

@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    query: Optional[str] = None
    days_back: int = 90
    max_emails: int = 500
    folder_id: Optional[str] = None

@dataclass
class PipelineProgress:
    """Pipeline progress tracking"""
    stage: str
    stage_number: int
    total_stages: int
    items_processed: int
    items_total: int
    started_at: datetime
    message: str

class EmailHandoverPipeline:
    """
    Main pipeline orchestrator

    Coordinates all stages of the email-to-handover pipeline.
    """

    def __init__(
        self,
        fetch_stage: FetchEmailsStage,
        extract_stage: ExtractContentStage,
        classify_stage: ClassifyStage,
        group_stage: GroupTopicsStage,
        merge_stage: MergeSummariesStage,
        dedupe_stage: DeduplicateStage,
        format_stage: FormatOutputStage,
        export_stage: ExportStage
    ):
        self.fetch = fetch_stage
        self.extract = extract_stage
        self.classify = classify_stage
        self.group = group_stage
        self.merge = merge_stage
        self.dedupe = dedupe_stage
        self.format = format_stage
        self.export = export_stage

        self._progress_callback: Optional[Callable[[PipelineProgress], None]] = None

    def on_progress(self, callback: Callable[[PipelineProgress], None]):
        """Register progress callback"""
        self._progress_callback = callback

    async def run(self, config: PipelineConfig) -> FormattedReport:
        """Run full pipeline"""

        started_at = datetime.now()

        # Stage 1: Fetch Emails
        self._report_progress(
            stage="fetch", stage_number=1, total=8,
            items=0, items_total=0,
            message="Fetching emails from Outlook...",
            started_at=started_at
        )
        raw_emails = await self.fetch.execute(
            query=config.query,
            days_back=config.days_back,
            max_emails=config.max_emails,
            folder_id=config.folder_id
        )

        # Stage 2: Extract Content
        self._report_progress(
            stage="extract", stage_number=2, total=8,
            items=0, items_total=len(raw_emails),
            message=f"Extracting content from {len(raw_emails)} emails...",
            started_at=started_at
        )
        extracted = self.extract.execute(raw_emails)

        # Stage 3: Classify
        self._report_progress(
            stage="classify", stage_number=3, total=8,
            items=0, items_total=len(extracted),
            message=f"Classifying {len(extracted)} emails with AI...",
            started_at=started_at
        )
        classifications = await self.classify.execute(extracted)

        # Stage 4: Group by Topic
        self._report_progress(
            stage="group", stage_number=4, total=8,
            items=len(classifications), items_total=len(classifications),
            message="Grouping emails by topic...",
            started_at=started_at
        )
        groups = self.group.execute(classifications, extracted)

        # Stage 5: Merge Summaries
        self._report_progress(
            stage="merge", stage_number=5, total=8,
            items=0, items_total=len(groups),
            message=f"Merging {len(groups)} topic groups with AI...",
            started_at=started_at
        )
        merged = await self.merge.execute(groups)

        # Stage 6: Deduplicate
        self._report_progress(
            stage="dedupe", stage_number=6, total=8,
            items=len(merged), items_total=len(merged),
            message="Removing duplicates...",
            started_at=started_at
        )
        deduplicated = self.dedupe.execute(merged)

        # Stage 7: Format Output
        self._report_progress(
            stage="format", stage_number=7, total=8,
            items=len(deduplicated), items_total=len(deduplicated),
            message="Formatting final report...",
            started_at=started_at
        )
        report = self.format.execute(deduplicated)

        # Stage 8: Complete
        self._report_progress(
            stage="complete", stage_number=8, total=8,
            items=len(deduplicated), items_total=len(deduplicated),
            message="Pipeline complete!",
            started_at=started_at
        )

        return report

    def _report_progress(
        self,
        stage: str,
        stage_number: int,
        total: int,
        items: int,
        items_total: int,
        message: str,
        started_at: datetime
    ):
        """Report progress to callback"""
        if self._progress_callback:
            self._progress_callback(PipelineProgress(
                stage=stage,
                stage_number=stage_number,
                total_stages=total,
                items_processed=items,
                items_total=items_total,
                started_at=started_at,
                message=message
            ))
```

---

## Part 5: Performance Targets

From `15_python_job_spec.md`:

| Metric | Target | Notes |
|--------|--------|-------|
| Fetch 500 emails | < 10 seconds | Graph API rate limited |
| Classify 500 emails | < 20 seconds | 10 concurrent AI calls |
| Merge 100 groups | < 15 seconds | 5 concurrent AI calls |
| Total pipeline | < 30 seconds | For 500 emails |
| Export rendering | < 10 seconds | HTML generation |

### Optimization Strategies

1. **Concurrent AI calls**: Use asyncio.Semaphore to control concurrency
2. **Batch Graph API calls**: Use `$top` parameter efficiently
3. **Cache classifications**: Store results in database for re-runs
4. **Streaming progress**: Report progress for long-running operations

---

## Part 6: Error Handling

```python
# src/pipeline/errors.py

class PipelineError(Exception):
    """Base pipeline error"""
    def __init__(self, stage: str, message: str, details: dict = None):
        self.stage = stage
        self.message = message
        self.details = details or {}
        super().__init__(f"[{stage}] {message}")

class FetchError(PipelineError):
    """Error fetching emails"""
    def __init__(self, message: str, details: dict = None):
        super().__init__("fetch", message, details)

class ClassificationError(PipelineError):
    """Error classifying emails"""
    def __init__(self, message: str, details: dict = None):
        super().__init__("classify", message, details)

class MergeError(PipelineError):
    """Error merging summaries"""
    def __init__(self, message: str, details: dict = None):
        super().__init__("merge", message, details)

class ExportError(PipelineError):
    """Error exporting report"""
    def __init__(self, message: str, details: dict = None):
        super().__init__("export", message, details)
```

---

## Part 7: Testing Strategy

```python
# tests/test_pipeline.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.orchestrator import EmailHandoverPipeline, PipelineConfig

@pytest.fixture
def mock_stages():
    """Create mock pipeline stages"""
    return {
        'fetch': MagicMock(),
        'extract': MagicMock(),
        'classify': AsyncMock(),
        'group': MagicMock(),
        'merge': AsyncMock(),
        'dedupe': MagicMock(),
        'format': MagicMock(),
        'export': MagicMock()
    }

@pytest.mark.asyncio
async def test_pipeline_runs_all_stages(mock_stages):
    """Test that pipeline executes all stages in order"""
    # Setup mocks
    mock_stages['fetch'].execute = AsyncMock(return_value=[])
    mock_stages['extract'].execute.return_value = []
    mock_stages['classify'].execute.return_value = []
    mock_stages['group'].execute.return_value = {}
    mock_stages['merge'].execute.return_value = []
    mock_stages['dedupe'].execute.return_value = []
    mock_stages['format'].execute.return_value = MagicMock(
        html='<html></html>',
        meta={},
        sections={}
    )

    # Create pipeline
    pipeline = EmailHandoverPipeline(**mock_stages)

    # Run pipeline
    config = PipelineConfig(days_back=7, max_emails=10)
    result = await pipeline.run(config)

    # Verify all stages called
    mock_stages['fetch'].execute.assert_called_once()
    mock_stages['extract'].execute.assert_called_once()
    mock_stages['classify'].execute.assert_called_once()
    mock_stages['group'].execute.assert_called_once()
    mock_stages['merge'].execute.assert_called_once()
    mock_stages['dedupe'].execute.assert_called_once()
    mock_stages['format'].execute.assert_called_once()

@pytest.mark.asyncio
async def test_classification_handles_errors():
    """Test that classification gracefully handles AI errors"""
    # Test implementation
    pass

@pytest.mark.asyncio
async def test_merge_groups_correctly():
    """Test that merge stage groups by category and subject"""
    # Test implementation
    pass
```

---

## Related Documents

- `IMPL_EMAIL_AZURE_INTEGRATION.md` - Azure OAuth configuration
- `15_python_job_spec.md` - Job specifications
- `MVP_Email_Handover.json` - Original n8n workflow
- `ANALYSIS_feasibility.md` - Gap analysis
