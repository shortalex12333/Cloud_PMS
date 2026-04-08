"""
Base parser types for the import pipeline.
All parsers return ParseResult instances.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# Regex to detect file references in column values
_FILE_REF_PATTERN = re.compile(
    r'(?:'
    r'[A-Za-z]:\\[^\s,;]+\.\w{2,4}'           # Windows path: C:\PMS\doc.pdf
    r'|/[^\s,;]+\.\w{2,4}'                     # Unix path: /PMS/docs/report.pdf
    r'|[^\s,;/\\]+\.(?:pdf|jpg|jpeg|png|doc|docx|xls|xlsx|tif|tiff|bmp|gif|txt|rtf|msg|eml)'
    r')',
    re.IGNORECASE,
)


def looks_like_file_ref(sample_values: list[str]) -> float:
    """
    Return 0.0-1.0 confidence that sample values contain file references.
    Checks for Windows/Unix paths and common document file extensions.
    """
    non_empty = [v for v in sample_values if v and str(v).strip()]
    if not non_empty:
        return 0.0
    hits = sum(1 for v in non_empty if _FILE_REF_PATTERN.search(str(v)))
    return hits / len(non_empty)


@dataclass
class ColumnInfo:
    """Detected column from a source file."""
    source_name: str
    sample_values: list[str] = field(default_factory=list)
    inferred_type: str = "text"  # text, integer, float, date, boolean


@dataclass
class FileWarning:
    """Warning generated during parsing."""
    field: Optional[str]
    message: str
    severity: str = "info"  # info, amber, red
    row: Optional[int] = None


@dataclass
class ParseResult:
    """Result of parsing a single file."""
    filename: str
    encoding_detected: str
    delimiter_detected: Optional[str]  # None for XLSX/SQL
    header_row: int  # 0-indexed row where headers were found
    row_count: int  # data rows (excluding header and metadata)
    columns: list[ColumnInfo] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)  # list of {column_name: value}
    date_format_detected: Optional[str] = None  # ISO, DD/MM/YYYY, MM/DD/YYYY, DD-MMM-YYYY, excel_serial, ambiguous
    warnings: list[FileWarning] = field(default_factory=list)
    domain_hint: Optional[str] = None  # equipment, work_orders, faults, parts, certificates, crew


@dataclass
class DocumentInfo:
    """A non-data file found in a ZIP (PDF, image, etc.)."""
    filename: str
    size_bytes: int
    content_type: str
    domain_hint: Optional[str] = None  # manuals, photos, certificates — inferred from folder
    data: Optional[bytes] = None
