from __future__ import annotations

"""
Document text extraction for enriching search_text.

PDF: extracts first N pages using pymupdf (fitz).
XLSX: extracts sheet names.
DOCX: extracts headings and first paragraphs.
TXT/CSV/MD: reads first N bytes directly.

All extraction is best-effort — failures return empty string.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger("extraction.extractor")

# Limits
MAX_EXTRACT_SIZE = 50 * 1024 * 1024  # 50 MB — skip extraction above this
MAX_PDF_PAGES = 5
MAX_TEXT_BYTES = 32 * 1024  # 32 KB for plain text files
MAX_OUTPUT_CHARS = 4000  # Truncate extracted text to this


def extract_text(file_path: str) -> str:
    """
    Extract searchable text from a file. Best-effort — returns empty string on failure.

    Supports:
        PDF: first 5 pages via pymupdf
        XLSX: sheet names
        DOCX: headings + first paragraphs
        TXT/CSV/MD/JSON/XML/HTML: first 32KB of raw text
    """
    try:
        size = os.path.getsize(file_path)
        if size > MAX_EXTRACT_SIZE:
            logger.debug("File too large for extraction (%d bytes): %s", size, file_path)
            return ""

        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return _extract_pdf(file_path)
        elif ext == ".xlsx":
            return _extract_xlsx(file_path)
        elif ext == ".docx":
            return _extract_docx(file_path)
        elif ext in (".txt", ".csv", ".md", ".json", ".xml", ".html", ".htm"):
            return _extract_plain_text(file_path)
        else:
            return ""

    except Exception as exc:
        logger.debug("Extraction failed for %s: %s", file_path, exc)
        return ""


def _extract_pdf(file_path: str) -> str:
    """Extract text from first N pages of a PDF using pymupdf."""
    try:
        import fitz  # pymupdf
    except ImportError:
        logger.debug("pymupdf not available, skipping PDF extraction")
        return ""

    try:
        doc = fitz.open(file_path)
        pages_to_read = min(len(doc), MAX_PDF_PAGES)
        text_parts = []

        for i in range(pages_to_read):
            page = doc[i]
            text = page.get_text("text")
            if text and text.strip():
                text_parts.append(text.strip())

        doc.close()

        if not text_parts:
            return ""

        combined = "\n\n".join(text_parts)
        return combined[:MAX_OUTPUT_CHARS]

    except Exception as exc:
        logger.debug("PDF extraction failed for %s: %s", file_path, exc)
        return ""


def _extract_xlsx(file_path: str) -> str:
    """Extract sheet names from an XLSX file (lightweight, no openpyxl dependency)."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(file_path, "r") as zf:
            # Try to read workbook.xml for sheet names
            try:
                with zf.open("xl/workbook.xml") as wb:
                    tree = ET.parse(wb)
                    root = tree.getroot()
                    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    sheets = root.findall(".//s:sheet", ns)
                    if sheets:
                        names = [s.get("name", "") for s in sheets if s.get("name")]
                        return "Sheets: " + ", ".join(names)
            except KeyError:
                pass

        return ""
    except Exception as exc:
        logger.debug("XLSX extraction failed for %s: %s", file_path, exc)
        return ""


def _extract_docx(file_path: str) -> str:
    """Extract headings and first paragraphs from a DOCX file."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(file_path, "r") as zf:
            try:
                with zf.open("word/document.xml") as doc:
                    tree = ET.parse(doc)
                    root = tree.getroot()
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

                    paragraphs = []
                    for p in root.findall(".//w:p", ns):
                        texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
                        if texts:
                            para = " ".join(texts).strip()
                            if para:
                                paragraphs.append(para)

                    if paragraphs:
                        # Take first 20 paragraphs
                        combined = "\n".join(paragraphs[:20])
                        return combined[:MAX_OUTPUT_CHARS]
            except KeyError:
                pass

        return ""
    except Exception as exc:
        logger.debug("DOCX extraction failed for %s: %s", file_path, exc)
        return ""


def _extract_plain_text(file_path: str) -> str:
    """Read first N bytes of a plain text file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(MAX_TEXT_BYTES)
        return text.strip()[:MAX_OUTPUT_CHARS] if text.strip() else ""
    except Exception as exc:
        logger.debug("Plain text extraction failed for %s: %s", file_path, exc)
        return ""
