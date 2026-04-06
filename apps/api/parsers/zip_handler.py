"""
ZIP Handler for the import pipeline.
Extracts ZIP archives and routes files to appropriate parsers.

File routing:
- .csv → csv_parser
- .xlsx → xlsx_parser
- .xls → xlsx_parser (parse_xls)
- .sql → sql_parser
- .pdf, .jpg, .png, .docx, etc. → document pipeline (stored, not parsed)
- Unknown → quarantined

Folder names in the ZIP are used as domain hints for documents.
"""

import os
import io
import zipfile
import logging
from pathlib import Path
from typing import Optional

from parsers.base_parser import ParseResult, FileWarning, DocumentInfo

logger = logging.getLogger("import.zip_handler")

# File extension routing
DATA_EXTENSIONS = {".csv", ".sql", ".xlsx", ".xls"}
DOCUMENT_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}

# Folder name → domain hint mapping
FOLDER_DOMAIN_HINTS = {
    "manual": "manuals",
    "manuals": "manuals",
    "handbook": "manuals",
    "certificate": "certificates",
    "certificates": "certificates",
    "cert": "certificates",
    "certs": "certificates",
    "photo": "photos",
    "photos": "photos",
    "image": "photos",
    "images": "photos",
    "drawing": "drawings",
    "drawings": "drawings",
    "schematic": "drawings",
    "schematics": "drawings",
    "report": "reports",
    "reports": "reports",
    "inspection": "reports",
    "equipment": "equipment",
    "workorder": "work_orders",
    "work_order": "work_orders",
    "work_orders": "work_orders",
    "fault": "faults",
    "faults": "faults",
    "defect": "faults",
    "defects": "faults",
    "spare": "parts",
    "spares": "parts",
    "part": "parts",
    "parts": "parts",
    "inventory": "parts",
}


def _infer_domain_from_path(filepath: str) -> Optional[str]:
    """Infer document domain from file path within the ZIP."""
    parts = Path(filepath).parts
    for part in parts:
        hint = FOLDER_DOMAIN_HINTS.get(part.lower())
        if hint:
            return hint
    # Check filename itself
    name_lower = Path(filepath).stem.lower()
    for keyword, domain in FOLDER_DOMAIN_HINTS.items():
        if keyword in name_lower:
            return domain
    return None


def extract_zip(raw_data: bytes, filename: str = "unknown.zip") -> dict:
    """
    Extract a ZIP archive and classify its contents.

    Returns:
        {
            "data_files": [(filename, extension, raw_bytes), ...],
            "documents": [DocumentInfo, ...],
            "unclassified": [DocumentInfo, ...],
            "warnings": [FileWarning, ...],
        }
    """
    warnings = []
    data_files = []
    documents = []
    unclassified = []

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_data), "r")
    except zipfile.BadZipFile:
        return {
            "data_files": [],
            "documents": [],
            "unclassified": [],
            "warnings": [FileWarning(field=None, message="Invalid ZIP file", severity="red")],
        }

    # Check for zip bomb (basic protection)
    total_size = sum(info.file_size for info in zf.infolist() if not info.is_dir())
    if total_size > 500 * 1024 * 1024:  # 500MB limit
        return {
            "data_files": [],
            "documents": [],
            "unclassified": [],
            "warnings": [FileWarning(
                field=None,
                message=f"ZIP contents too large ({total_size / 1024 / 1024:.0f}MB). Maximum 500MB.",
                severity="red",
            )],
        }

    for info in zf.infolist():
        # Skip directories and macOS resource forks
        if info.is_dir():
            continue
        if info.filename.startswith("__MACOSX/") or info.filename.startswith("._"):
            continue
        if info.filename.endswith(".DS_Store"):
            continue

        ext = os.path.splitext(info.filename)[1].lower()
        basename = os.path.basename(info.filename)

        try:
            file_data = zf.read(info.filename)
        except Exception as e:
            warnings.append(FileWarning(
                field=None,
                message=f"Cannot read {info.filename}: {e}",
                severity="amber",
            ))
            continue

        if ext in DATA_EXTENSIONS:
            data_files.append((basename, ext, file_data))

        elif ext in DOCUMENT_EXTENSIONS:
            domain = _infer_domain_from_path(info.filename)
            documents.append(DocumentInfo(
                filename=basename,
                size_bytes=len(file_data),
                content_type=DOCUMENT_EXTENSIONS[ext],
                domain_hint=domain,
                data=file_data,
            ))

        else:
            unclassified.append(DocumentInfo(
                filename=basename,
                size_bytes=len(file_data),
                content_type="application/octet-stream",
                domain_hint=None,
                data=file_data,
            ))

    zf.close()

    logger.info(
        f"Extracted {filename}: {len(data_files)} data files, "
        f"{len(documents)} documents, {len(unclassified)} unclassified"
    )

    return {
        "data_files": data_files,
        "documents": documents,
        "unclassified": unclassified,
        "warnings": warnings,
    }


def parse_zip(raw_data: bytes, filename: str = "unknown.zip", source: str = "generic") -> dict:
    """
    Extract and parse a ZIP archive.

    Returns:
        {
            "parse_results": [ParseResult, ...],  — one per data file
            "documents": [DocumentInfo, ...],
            "unclassified": [DocumentInfo, ...],
            "warnings": [FileWarning, ...],
        }
    """
    extraction = extract_zip(raw_data, filename)

    parse_results = []
    all_warnings = list(extraction["warnings"])

    for basename, ext, file_data in extraction["data_files"]:
        if ext == ".csv":
            from parsers.csv_parser import parse_csv
            result = parse_csv(file_data, basename)
            parse_results.append(result)

        elif ext == ".xlsx":
            from parsers.xlsx_parser import parse_xlsx
            result = parse_xlsx(file_data, basename)
            parse_results.append(result)

        elif ext == ".xls":
            from parsers.xlsx_parser import parse_xls
            result = parse_xls(file_data, basename)
            parse_results.append(result)

        elif ext == ".sql":
            from parsers.sql_parser import parse_sql
            results = parse_sql(file_data, basename)
            parse_results.extend(results)

    return {
        "parse_results": parse_results,
        "documents": extraction["documents"],
        "unclassified": extraction["unclassified"],
        "warnings": all_warnings,
    }
