"""
Email Watcher - Token Extractor

Extracts structured tokens from email metadata:
- Work Order IDs (WO-####)
- Purchase Order IDs (PO-####)
- Equipment IDs (EQ-####)
- Part numbers
- Serial numbers
- Attachment signals (quote, invoice, etc.)
- Vendor domain/email hashes
"""

import re
import hashlib
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TokenExtractor:
    """
    Extract structured tokens from email metadata.

    Phase 7a-d: ID Patterns, Part Numbers, Attachments, Vendor Domains
    """

    # ==========================================================================
    # Phase 7a: ID Patterns
    # ==========================================================================

    ID_PATTERNS = {
        'wo_id': re.compile(r'\b(?:WO[-#]?|Work\s*Order[-#:\s]*)(\d{1,6})\b', re.IGNORECASE),
        'po_id': re.compile(r'\b(?:PO[-#]?|Purchase\s*Order[-#:\s]*)(\d{1,6})\b', re.IGNORECASE),
        'eq_id': re.compile(r'\b(?:EQ[-#]?)(\d{1,6})\b', re.IGNORECASE),
        'fault_id': re.compile(r'\b(?:FAULT[-#]?|Fault[-#:\s]*)(\d{1,6})\b', re.IGNORECASE),
        'invoice_id': re.compile(r'\b(?:INV[-#]?|Invoice[-#:\s]*)(\d{1,10})\b', re.IGNORECASE),
        'quote_id': re.compile(r'\b(?:QU?[-#]?|Quote[-#:\s]*)(\d{1,10})\b', re.IGNORECASE),
    }

    # ==========================================================================
    # Phase 7b: Part/Serial Number Patterns
    # ==========================================================================

    PART_PATTERNS = {
        # Part numbers: 2-4 letters, optional dash, 3-8 digits, optional suffix
        'part_number': re.compile(r'\b([A-Z]{2,4}[-]?\d{3,8}[-]?[A-Z0-9]{0,4})\b'),
        # Serial numbers: S/N or Serial followed by alphanumeric
        'serial_number': re.compile(r'\b(?:S/?N|Serial)[-:\s]*([A-Z0-9]{6,20})\b', re.IGNORECASE),
        # OEM numbers
        'oem_number': re.compile(r'\b(?:OEM|Original)[-:\s]*([A-Z0-9-]{5,20})\b', re.IGNORECASE),
    }

    # ==========================================================================
    # Phase 7c: Attachment Filename Patterns
    # ==========================================================================

    PROCUREMENT_PATTERNS = {
        'quote': re.compile(r'quote|quotation|proforma|estimate', re.IGNORECASE),
        'invoice': re.compile(r'invoice|inv[-_]|billing', re.IGNORECASE),
        'receipt': re.compile(r'receipt|payment|confirmation', re.IGNORECASE),
        'po': re.compile(r'purchase[-_]?order|po[-_]', re.IGNORECASE),
        'pricing': re.compile(r'pricing|price[-_]?list|catalog', re.IGNORECASE),
    }

    SERVICE_PATTERNS = {
        'service_report': re.compile(r'service[-_]?report|job[-_]?sheet|work[-_]?report', re.IGNORECASE),
        'completion': re.compile(r'completion|sign[-_]?off|handover', re.IGNORECASE),
        'certificate': re.compile(r'certificate|cert[-_]|certification', re.IGNORECASE),
        'inspection': re.compile(r'inspection|survey|audit', re.IGNORECASE),
    }

    TECHNICAL_PATTERNS = {
        'manual': re.compile(r'manual|handbook|guide', re.IGNORECASE),
        'datasheet': re.compile(r'datasheet|data[-_]?sheet|spec', re.IGNORECASE),
        'drawing': re.compile(r'drawing|diagram|schematic', re.IGNORECASE),
    }

    def __init__(self):
        """Initialize the token extractor."""
        pass

    def extract_all(
        self,
        subject: str,
        from_address: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        participant_hashes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract all tokens from email metadata.

        Args:
            subject: Email subject line
            from_address: Sender email address
            attachments: List of attachment metadata (name, size, etc.)
            participant_hashes: List of participant email hashes

        Returns:
            Dictionary of extracted tokens
        """
        tokens = {}

        # Extract ID patterns from subject
        id_tokens = self.extract_ids(subject)
        if id_tokens:
            tokens['ids'] = id_tokens

        # Extract part/serial numbers from subject
        part_tokens = self.extract_part_numbers(subject)
        if part_tokens:
            tokens['parts'] = part_tokens

        # Extract from attachments
        if attachments:
            # Part numbers in attachment filenames
            for att in attachments:
                filename = att.get('name', '')
                att_parts = self.extract_part_numbers(filename)
                if att_parts:
                    for key, values in att_parts.items():
                        tokens.setdefault('parts', {}).setdefault(key, []).extend(values)

            # Classify attachments
            att_signals = self.classify_attachments(attachments)
            if att_signals['procurement'] or att_signals['service'] or att_signals['technical']:
                tokens['attachment_signals'] = att_signals

        # Extract vendor signals
        vendor_signals = self.extract_vendor_signals(from_address, participant_hashes)
        if vendor_signals:
            tokens['vendor'] = vendor_signals

        return tokens

    def extract_ids(self, text: str) -> Dict[str, List[str]]:
        """
        Extract ID patterns from text (Phase 7a).

        Args:
            text: Text to search (subject line, etc.)

        Returns:
            Dictionary mapping ID type to list of matched values
        """
        tokens = {}

        for name, pattern in self.ID_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                # Deduplicate while preserving order
                unique = list(dict.fromkeys(matches))
                tokens[name] = unique

        return tokens

    def extract_part_numbers(self, text: str) -> Dict[str, List[str]]:
        """
        Extract part/serial numbers from text (Phase 7b).

        Args:
            text: Text to search

        Returns:
            Dictionary mapping part type to list of matched values
        """
        tokens = {}

        for name, pattern in self.PART_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                # Filter out common false positives
                filtered = [m for m in matches if not self._is_false_positive(m, name)]
                if filtered:
                    tokens[name] = list(dict.fromkeys(filtered))

        return tokens

    def _is_false_positive(self, match: str, match_type: str) -> bool:
        """Check if a match is likely a false positive."""
        # Common false positives for part numbers
        false_positives = {
            'RE', 'FW', 'FWD', 'PDF', 'DOC', 'DOCX', 'XLS', 'XLSX',
            'PNG', 'JPG', 'JPEG', 'GIF', 'ZIP', 'RAR',
        }

        upper = match.upper()

        # Check if it's a file extension or common prefix
        if upper in false_positives:
            return True

        # Serial numbers should have both letters and numbers
        if match_type == 'serial_number':
            has_letter = any(c.isalpha() for c in match)
            has_digit = any(c.isdigit() for c in match)
            if not (has_letter and has_digit):
                return True

        return False

    def classify_attachments(
        self,
        attachments: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Classify attachments by type signals (Phase 7c).

        Args:
            attachments: List of attachment metadata

        Returns:
            Dictionary with procurement, service, technical, and other lists
        """
        signals = {
            'procurement': [],
            'service': [],
            'technical': [],
            'other': []
        }

        for att in attachments:
            filename = att.get('name', '')
            if not filename:
                continue

            classified = False

            # Check procurement patterns
            for pattern in self.PROCUREMENT_PATTERNS.values():
                if pattern.search(filename):
                    signals['procurement'].append(filename)
                    classified = True
                    break

            # Check service patterns
            if not classified:
                for pattern in self.SERVICE_PATTERNS.values():
                    if pattern.search(filename):
                        signals['service'].append(filename)
                        classified = True
                        break

            # Check technical patterns
            if not classified:
                for pattern in self.TECHNICAL_PATTERNS.values():
                    if pattern.search(filename):
                        signals['technical'].append(filename)
                        classified = True
                        break

            # Unclassified
            if not classified:
                signals['other'].append(filename)

        return signals

    def extract_vendor_signals(
        self,
        from_address: str,
        participant_hashes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract vendor-related signals (Phase 7d).

        Args:
            from_address: Sender email address
            participant_hashes: List of participant email hashes

        Returns:
            Dictionary with vendor signals
        """
        signals = {}

        if from_address and '@' in from_address:
            # Extract domain
            domain = from_address.split('@')[1].lower()
            signals['sender_domain'] = domain

            # Hash the email address
            email_lower = from_address.lower().strip()
            signals['sender_hash'] = hashlib.sha256(email_lower.encode()).hexdigest()

            # Check if it's a common personal email domain
            personal_domains = {
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'icloud.com', 'aol.com', 'mail.com', 'protonmail.com'
            }
            signals['is_personal_domain'] = domain in personal_domains

        # Include participant hashes for multi-party matching
        if participant_hashes:
            signals['participant_hashes'] = participant_hashes

        return signals

    def get_primary_id(self, tokens: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Get the primary ID from extracted tokens (highest priority match).

        Priority order: WO > PO > Fault > Equipment > Quote > Invoice

        Args:
            tokens: Extracted tokens dictionary

        Returns:
            Dictionary with 'type' and 'value' or None
        """
        ids = tokens.get('ids', {})

        # Priority order
        priority = ['wo_id', 'po_id', 'fault_id', 'eq_id', 'quote_id', 'invoice_id']

        for id_type in priority:
            if id_type in ids and ids[id_type]:
                return {
                    'type': id_type,
                    'value': ids[id_type][0]  # Take first match
                }

        return None

    def has_procurement_signal(self, tokens: Dict[str, Any]) -> bool:
        """
        Check if tokens indicate procurement activity.

        Args:
            tokens: Extracted tokens dictionary

        Returns:
            True if procurement signals present
        """
        # Check for PO/Quote/Invoice IDs
        ids = tokens.get('ids', {})
        if any(k in ids for k in ['po_id', 'quote_id', 'invoice_id']):
            return True

        # Check attachment signals
        att_signals = tokens.get('attachment_signals', {})
        if att_signals.get('procurement'):
            return True

        return False

    def has_service_signal(self, tokens: Dict[str, Any]) -> bool:
        """
        Check if tokens indicate service activity.

        Args:
            tokens: Extracted tokens dictionary

        Returns:
            True if service signals present
        """
        # Check for WO/Fault IDs
        ids = tokens.get('ids', {})
        if any(k in ids for k in ['wo_id', 'fault_id']):
            return True

        # Check attachment signals
        att_signals = tokens.get('attachment_signals', {})
        if att_signals.get('service'):
            return True

        return False


# Export
__all__ = ['TokenExtractor']
