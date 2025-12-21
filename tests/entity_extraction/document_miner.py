"""
Document Term Mining Pipeline
=============================

Reverse-engineers entity patterns from actual yacht documents.
This solves the chicken-and-egg problem by:
1. Extracting ALL terms from documents first
2. Grouping by document category/type
3. Building frequency analysis
4. Identifying domain-specific vocabulary
5. Creating candidate entity lists for validation

NO AUTOMATION of entity creation - humans validate all candidates.
"""

import os
import re
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime

# PDF extraction
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PyMuPDF not installed. Run: pip install pymupdf")


@dataclass
class DocumentTerms:
    """Terms extracted from a single document."""
    file_path: str
    category: str  # 01_BRIDGE, 02_ENGINEERING, etc.
    subcategory: str  # radar, engines, etc.
    doc_type: str  # manuals, parts, maintenance, schematics
    brand: Optional[str]

    # Extracted terms
    all_terms: List[str]
    noun_phrases: List[str]
    measurements: List[str]
    model_numbers: List[str]
    part_numbers: List[str]

    # Metadata
    word_count: int
    extraction_date: str


class DocumentMiner:
    """
    Mines terms from yacht documents for entity pattern discovery.

    This is the REVERSE ENGINEERING step - we look at what's actually
    in the documents to inform what entities we should extract.
    """

    # Patterns for extracting specific term types
    MEASUREMENT_PATTERNS = [
        r'\d+(?:\.\d+)?\s*(?:V|volts?|VAC|VDC)',
        r'\d+(?:\.\d+)?\s*(?:A|amps?|mA)',
        r'\d+(?:\.\d+)?\s*(?:W|watts?|kW|MW)',
        r'\d+(?:\.\d+)?\s*(?:Hz|kHz|MHz)',
        r'\d+(?:\.\d+)?\s*(?:bar|psi|kPa|MPa)',
        r'\d+(?:\.\d+)?\s*(?:°C|°F|celsius|fahrenheit)',
        r'\d+(?:\.\d+)?\s*(?:rpm|RPM)',
        r'\d+(?:\.\d+)?\s*(?:l/min|gpm|m³/h)',
        r'\d+(?:\.\d+)?\s*(?:mm|cm|m|in|ft)',
        r'\d+(?:\.\d+)?\s*(?:kg|g|lb|lbs)',
        r'\d+(?:\.\d+)?\s*(?:L|liters?|gallons?)',
    ]

    MODEL_NUMBER_PATTERNS = [
        r'[A-Z]{2,5}[-\s]?\d{3,6}[A-Z]?',  # MTU-4000, CAT3512
        r'[A-Z]+\d+[A-Z]+\d*',  # VHF210, GPS19x
        r'\d{4,6}[-\s]?[A-Z]{1,3}',  # 1234-AB
    ]

    PART_NUMBER_PATTERNS = [
        r'P/?N[:\s]*[A-Z0-9\-]+',  # P/N: 12345-ABC
        r'Part\s*(?:No\.?|Number)[:\s]*[A-Z0-9\-]+',
        r'[A-Z]{2,3}\d{5,8}',  # AB12345678
    ]

    # Known brands to look for
    KNOWN_BRANDS = {
        'mtu', 'caterpillar', 'cat', 'cummins', 'volvo', 'volvo penta',
        'yanmar', 'john deere', 'man', 'perkins', 'detroit diesel',
        'furuno', 'raymarine', 'garmin', 'simrad', 'navico', 'b&g',
        'victron', 'mastervolt', 'fischer panda', 'northern lights',
        'onan', 'kohler', 'westerbeke', 'whisperpower',
        'spectra', 'sea recovery', 'village marine', 'katadyn',
        'dometic', 'marine air', 'cruisair', 'webasto',
        'lewmar', 'maxwell', 'muir', 'lofrans', 'quick',
        'jabsco', 'johnson pump', 'rule', 'whale', 'shurflo',
        'groco', 'racor', 'parker', 'vetus', 'aqualarm',
    }

    def __init__(self, root_dir: str, db_path: Optional[str] = None):
        self.root_dir = Path(root_dir)
        self.db_path = db_path or str(Path(__file__).parent / "mined_terms.db")
        self._init_db()

        # Compile patterns
        self.measurement_re = [re.compile(p, re.IGNORECASE) for p in self.MEASUREMENT_PATTERNS]
        self.model_re = [re.compile(p) for p in self.MODEL_NUMBER_PATTERNS]
        self.part_re = [re.compile(p, re.IGNORECASE) for p in self.PART_NUMBER_PATTERNS]

    def _init_db(self):
        """Initialize SQLite database for storing mined terms."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                file_path TEXT UNIQUE,
                category TEXT,
                subcategory TEXT,
                doc_type TEXT,
                brand TEXT,
                word_count INTEGER,
                extraction_date TEXT
            )
        ''')

        # Terms table (frequency across documents)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS terms (
                id INTEGER PRIMARY KEY,
                term TEXT,
                term_type TEXT,
                frequency INTEGER DEFAULT 1,
                doc_count INTEGER DEFAULT 1,
                categories TEXT,
                first_seen TEXT,
                UNIQUE(term, term_type)
            )
        ''')

        # Document-Term mapping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doc_terms (
                doc_id INTEGER,
                term_id INTEGER,
                count INTEGER DEFAULT 1,
                FOREIGN KEY(doc_id) REFERENCES documents(id),
                FOREIGN KEY(term_id) REFERENCES terms(id),
                UNIQUE(doc_id, term_id)
            )
        ''')

        # Ground truth annotations (human validated)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ground_truth (
                id INTEGER PRIMARY KEY,
                term TEXT,
                entity_type TEXT,
                canonical TEXT,
                confidence REAL,
                validated_by TEXT,
                validation_date TEXT,
                notes TEXT,
                UNIQUE(term, entity_type)
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_terms_type ON terms(term_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_terms_freq ON terms(frequency DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gt_type ON ground_truth(entity_type)')

        conn.commit()
        conn.close()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        if not PDF_AVAILABLE:
            return ""

        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"Error extracting {pdf_path}: {e}")
            return ""

    def parse_file_path(self, file_path: str) -> Tuple[str, str, str, Optional[str]]:
        """
        Parse file path to extract category, subcategory, doc_type, brand.

        Example: ROOT/02_ENGINEERING/engines/mtu/manuals/MTU_4000_Manual.pdf
        Returns: ('02_ENGINEERING', 'engines', 'manuals', 'mtu')
        """
        parts = Path(file_path).parts
        root_idx = -1
        for i, p in enumerate(parts):
            if p == 'ROOT':
                root_idx = i
                break

        if root_idx == -1:
            return ('unknown', 'unknown', 'unknown', None)

        relative_parts = parts[root_idx + 1:]

        category = relative_parts[0] if len(relative_parts) > 0 else 'unknown'
        subcategory = relative_parts[1] if len(relative_parts) > 1 else 'unknown'

        # Look for doc_type and brand
        doc_type = 'unknown'
        brand = None

        for p in relative_parts[2:]:
            p_lower = p.lower()
            if p_lower in ['manuals', 'parts', 'maintenance', 'schematics', 'specs', 'installation']:
                doc_type = p_lower
            elif p_lower in self.KNOWN_BRANDS or any(b in p_lower for b in self.KNOWN_BRANDS):
                brand = p_lower

        return (category, subcategory, doc_type, brand)

    def extract_terms(self, text: str) -> DocumentTerms:
        """Extract various term types from document text."""
        if not text:
            return None

        # Normalize text
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text)

        # Extract measurements
        measurements = []
        for pattern in self.measurement_re:
            measurements.extend(pattern.findall(text))

        # Extract model numbers
        model_numbers = []
        for pattern in self.model_re:
            model_numbers.extend(pattern.findall(text))

        # Extract part numbers
        part_numbers = []
        for pattern in self.part_re:
            part_numbers.extend(pattern.findall(text))

        # Extract all words (for frequency analysis)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Extract noun phrases (2-3 word combinations that appear together)
        # Simple heuristic: adjacent capitalized words
        noun_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b', text)

        return {
            'all_terms': words,
            'noun_phrases': noun_phrases,
            'measurements': list(set(measurements)),
            'model_numbers': list(set(model_numbers)),
            'part_numbers': list(set(part_numbers)),
            'word_count': len(words)
        }

    def mine_document(self, file_path: str) -> Optional[DocumentTerms]:
        """Mine terms from a single document."""
        category, subcategory, doc_type, brand = self.parse_file_path(file_path)

        # Extract text
        if file_path.lower().endswith('.pdf'):
            text = self.extract_text_from_pdf(file_path)
        else:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except:
                return None

        if not text:
            return None

        terms = self.extract_terms(text)
        if not terms:
            return None

        return DocumentTerms(
            file_path=file_path,
            category=category,
            subcategory=subcategory,
            doc_type=doc_type,
            brand=brand,
            all_terms=terms['all_terms'],
            noun_phrases=terms['noun_phrases'],
            measurements=terms['measurements'],
            model_numbers=terms['model_numbers'],
            part_numbers=terms['part_numbers'],
            word_count=terms['word_count'],
            extraction_date=datetime.now().isoformat()
        )

    def mine_all_documents(self, limit: Optional[int] = None) -> Dict:
        """
        Mine all documents in ROOT directory.

        Returns summary statistics.
        """
        pdf_files = list(self.root_dir.rglob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]

        stats = {
            'total_files': len(pdf_files),
            'processed': 0,
            'failed': 0,
            'total_words': 0,
            'unique_terms': set(),
            'categories': Counter(),
            'brands': Counter(),
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for i, pdf_path in enumerate(pdf_files):
            if i % 50 == 0:
                print(f"Processing {i}/{len(pdf_files)}...")

            doc_terms = self.mine_document(str(pdf_path))
            if not doc_terms:
                stats['failed'] += 1
                continue

            stats['processed'] += 1
            stats['total_words'] += doc_terms.word_count
            stats['unique_terms'].update(doc_terms.all_terms)
            stats['categories'][doc_terms.category] += 1
            if doc_terms.brand:
                stats['brands'][doc_terms.brand] += 1

            # Store in database
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO documents
                    (file_path, category, subcategory, doc_type, brand, word_count, extraction_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    doc_terms.file_path, doc_terms.category, doc_terms.subcategory,
                    doc_terms.doc_type, doc_terms.brand, doc_terms.word_count,
                    doc_terms.extraction_date
                ))
                doc_id = cursor.lastrowid

                # Store term frequencies
                term_counts = Counter(doc_terms.all_terms)
                for term, count in term_counts.most_common(100):  # Top 100 terms per doc
                    cursor.execute('''
                        INSERT INTO terms (term, term_type, frequency, categories, first_seen)
                        VALUES (?, 'word', 1, ?, ?)
                        ON CONFLICT(term, term_type) DO UPDATE SET
                            frequency = frequency + 1,
                            doc_count = doc_count + 1
                    ''', (term, doc_terms.category, doc_terms.extraction_date))

                # Store measurements
                for m in doc_terms.measurements:
                    cursor.execute('''
                        INSERT INTO terms (term, term_type, frequency, categories, first_seen)
                        VALUES (?, 'measurement', 1, ?, ?)
                        ON CONFLICT(term, term_type) DO UPDATE SET
                            frequency = frequency + 1,
                            doc_count = doc_count + 1
                    ''', (m, doc_terms.category, doc_terms.extraction_date))

                # Store model numbers
                for m in doc_terms.model_numbers:
                    cursor.execute('''
                        INSERT INTO terms (term, term_type, frequency, categories, first_seen)
                        VALUES (?, 'model_number', 1, ?, ?)
                        ON CONFLICT(term, term_type) DO UPDATE SET
                            frequency = frequency + 1,
                            doc_count = doc_count + 1
                    ''', (m, doc_terms.category, doc_terms.extraction_date))

                conn.commit()
            except Exception as e:
                print(f"DB error for {pdf_path}: {e}")

        conn.close()

        stats['unique_terms'] = len(stats['unique_terms'])
        return stats

    def get_top_terms(self, term_type: str = 'word', limit: int = 100) -> List[Tuple[str, int]]:
        """Get top terms by frequency."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT term, frequency FROM terms
            WHERE term_type = ?
            ORDER BY frequency DESC
            LIMIT ?
        ''', (term_type, limit))

        results = cursor.fetchall()
        conn.close()
        return results

    def get_candidate_entities(self, min_frequency: int = 5) -> Dict[str, List]:
        """
        Get candidate entities that appear frequently across documents.

        These are CANDIDATES for human review, not automatically added patterns.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        candidates = {
            'equipment': [],
            'measurements': [],
            'model_numbers': [],
            'potential_symptoms': [],
            'potential_actions': [],
        }

        # High-frequency technical terms (potential equipment)
        cursor.execute('''
            SELECT term, frequency, doc_count FROM terms
            WHERE term_type = 'word'
            AND frequency >= ?
            AND length(term) >= 4
            ORDER BY frequency DESC
        ''', (min_frequency,))

        for term, freq, doc_count in cursor.fetchall():
            # Filter common English words
            if term not in COMMON_WORDS:
                candidates['equipment'].append({
                    'term': term,
                    'frequency': freq,
                    'doc_count': doc_count,
                    'needs_review': True
                })

        # Measurements
        cursor.execute('''
            SELECT term, frequency FROM terms
            WHERE term_type = 'measurement'
            ORDER BY frequency DESC
            LIMIT 200
        ''')
        candidates['measurements'] = [{'term': t, 'frequency': f} for t, f in cursor.fetchall()]

        # Model numbers
        cursor.execute('''
            SELECT term, frequency FROM terms
            WHERE term_type = 'model_number'
            ORDER BY frequency DESC
            LIMIT 200
        ''')
        candidates['model_numbers'] = [{'term': t, 'frequency': f} for t, f in cursor.fetchall()]

        conn.close()
        return candidates

    def export_for_review(self, output_path: str):
        """Export candidate entities to JSON for human review."""
        candidates = self.get_candidate_entities()

        review_data = {
            'generated_at': datetime.now().isoformat(),
            'instructions': '''
HUMAN REVIEW REQUIRED
=====================
These are candidate entities mined from actual yacht documents.
For each candidate, you must:
1. Decide if it's a valid entity (yes/no)
2. Assign an entity type (equipment, symptom, action, etc.)
3. Provide the canonical form
4. Assign a confidence weight (0.0-1.0)

DO NOT automatically add these to patterns.
Each must be manually validated.
            ''',
            'candidates': candidates
        }

        with open(output_path, 'w') as f:
            json.dump(review_data, f, indent=2)

        print(f"Exported {sum(len(v) for v in candidates.values())} candidates to {output_path}")


# Common English words to filter out
COMMON_WORDS = {
    'the', 'and', 'for', 'that', 'with', 'are', 'from', 'this', 'have',
    'not', 'but', 'can', 'all', 'when', 'there', 'will', 'been', 'more',
    'some', 'would', 'make', 'like', 'into', 'time', 'has', 'look', 'two',
    'way', 'could', 'people', 'than', 'first', 'water', 'been', 'call',
    'who', 'oil', 'its', 'now', 'find', 'long', 'down', 'day', 'did', 'get',
    'come', 'made', 'may', 'part', 'over', 'such', 'new', 'just', 'only',
    'see', 'other', 'were', 'which', 'then', 'them', 'these', 'she', 'many',
    'well', 'about', 'after', 'should', 'also', 'must', 'any', 'before',
    'most', 'through', 'where', 'being', 'system', 'use', 'used', 'using',
    'check', 'figure', 'section', 'page', 'note', 'warning', 'caution',
    'refer', 'manual', 'install', 'installation', 'operation', 'maintenance',
}


if __name__ == "__main__":
    # Example usage
    ROOT_DIR = "/Users/celeste7/Documents/yacht-nas/ROOT"

    miner = DocumentMiner(ROOT_DIR)

    print("Mining documents (first 50 for testing)...")
    stats = miner.mine_all_documents(limit=50)

    print(f"\nMining Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Processed: {stats['processed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Total words: {stats['total_words']}")
    print(f"  Unique terms: {stats['unique_terms']}")

    print(f"\nCategories: {dict(stats['categories'])}")
    print(f"Brands: {dict(stats['brands'])}")

    print("\nTop 20 terms:")
    for term, freq in miner.get_top_terms(limit=20):
        print(f"  {term}: {freq}")

    # Export for review
    miner.export_for_review("/tmp/entity_candidates.json")
