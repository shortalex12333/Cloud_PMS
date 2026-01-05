"""
CelesteOS Document Extraction Service v3.0
Universal text extraction with OCR fallback for scanned PDFs.

Extraction Lanes:
- LANE 1: PyMuPDF text extraction (fast, native text)
- LANE 2: Tesseract OCR fallback (scanned/image PDFs)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fitz  # PyMuPDF
import httpx
import io
import os
import csv
import json
from PIL import Image
import pytesseract

app = FastAPI(
    title="CelesteOS Extraction Service",
    description="Universal document text extraction with OCR",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class ExtractRequest(BaseModel):
    storage_path: str
    content_type: str
    filename: str
    yacht_id: str
    document_id: str
    service_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
    doc_type: str = None
    system_tag: str = None

class ExtractionResponse(BaseModel):
    text: str
    pages: int = 0
    chars: int = 0
    status: str = "success"
    extraction_method: str = "unknown"
    filename: str = ""
    content_type: str = ""
    yacht_id: str = ""
    document_id: str = ""
    doc_type: str = None
    system_tag: str = None

# --- Health ---

@app.get("/")
def health():
    return {"status": "ok", "service": "extraction", "version": "3.0.0"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "extraction_methods": ["pymupdf", "tesseract_ocr", "docx", "xlsx", "csv", "json", "text"],
        "supported_types": [
            "application/pdf",
            "text/plain", "text/csv", "text/html", "text/xml",
            "application/json", "application/xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
    }

# --- Main Extraction Endpoint ---

SUPABASE_STORAGE_BASE = "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object"
MIN_TEXT_THRESHOLD = 50  # Minimum chars before triggering OCR fallback

@app.post("/extract", response_model=ExtractionResponse)
async def extract(request: ExtractRequest):
    """
    Main extraction endpoint with intelligent routing.
    """
    try:
        # Build storage URL
        storage_url = f"{SUPABASE_STORAGE_BASE}/{request.storage_path}"

        # Fetch file from Supabase
        headers = {
            "apikey": request.service_key,
            "Authorization": f"Bearer {request.service_key}"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(storage_url, headers=headers)
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"File not found: {request.storage_path}")
            resp.raise_for_status()
            file_bytes = resp.content

        # Extract based on content type
        text, pages, method = await _extract_by_type(file_bytes, request.content_type, request.filename)

        return ExtractionResponse(
            text=text,
            pages=pages,
            chars=len(text),
            status="success",
            extraction_method=method,
            filename=request.filename,
            content_type=request.content_type,
            yacht_id=request.yacht_id,
            document_id=request.document_id,
            doc_type=request.doc_type,
            system_tag=request.system_tag
        )

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


async def _extract_by_type(file_bytes: bytes, content_type: str, filename: str) -> tuple[str, int, str]:
    """Route extraction based on content type. Returns (text, pages, method)."""

    # PDF - with OCR fallback
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        return _extract_pdf_with_ocr_fallback(file_bytes)

    # Excel XLSX
    if content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or filename.lower().endswith(".xlsx"):
        text, pages = _extract_xlsx(file_bytes)
        return text, pages, "openpyxl"

    # Word DOCX
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.lower().endswith(".docx"):
        text, pages = _extract_docx(file_bytes)
        return text, pages, "python-docx"

    # CSV
    if content_type == "text/csv" or filename.lower().endswith(".csv"):
        text, pages = _extract_csv(file_bytes)
        return text, pages, "csv"

    # JSON
    if content_type == "application/json" or filename.lower().endswith(".json"):
        text, pages = _extract_json(file_bytes)
        return text, pages, "json"

    # XML
    if content_type in ["application/xml", "text/xml"] or filename.lower().endswith(".xml"):
        text, pages = _extract_text(file_bytes)
        return text, pages, "text"

    # HTML
    if content_type == "text/html" or filename.lower().endswith(".html"):
        text, pages = _extract_html(file_bytes)
        return text, pages, "html"

    # Default: plain text
    text, pages = _extract_text(file_bytes)
    return text, pages, "text"


def _extract_pdf_with_ocr_fallback(file_bytes: bytes) -> tuple[str, int, str]:
    """
    Extract PDF with intelligent fallback:
    LANE 1: PyMuPDF native text extraction
    LANE 2: Tesseract OCR if text is minimal/empty
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    num_pages = len(doc)

    # LANE 1: Try PyMuPDF text extraction
    all_text = []
    for page in doc:
        text = page.get_text()
        if text:
            all_text.append(text.strip())

    combined_text = "\n\n".join(all_text)

    # Check if we got meaningful text
    if len(combined_text) >= MIN_TEXT_THRESHOLD:
        doc.close()
        return combined_text, num_pages, "pymupdf"

    # LANE 2: OCR fallback for scanned PDFs
    ocr_text = []
    for page_num in range(num_pages):
        page = doc[page_num]
        # Render page to image at 200 DPI
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Run Tesseract OCR
        try:
            text = pytesseract.image_to_string(img)
            if text:
                ocr_text.append(text.strip())
        except Exception as e:
            # If OCR fails, continue with next page
            ocr_text.append(f"[OCR failed on page {page_num + 1}: {str(e)}]")

    doc.close()

    ocr_combined = "\n\n".join(ocr_text)

    # Return whichever has more content
    if len(ocr_combined) > len(combined_text):
        return ocr_combined, num_pages, "tesseract_ocr"
    else:
        return combined_text if combined_text else ocr_combined, num_pages, "pymupdf"


def _extract_xlsx(file_bytes: bytes) -> tuple[str, int]:
    """Extract text from Excel XLSX."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        all_text = []
        for sheet in wb.worksheets:
            rows = []
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(str(cell) if cell is not None else "" for cell in row)
                if row_text.strip():
                    rows.append(row_text)
            if rows:
                all_text.append(f"=== {sheet.title} ===\n" + "\n".join(rows))
        return "\n\n".join(all_text), len(wb.worksheets)
    except ImportError:
        return "[XLSX extraction requires openpyxl]", 0


def _extract_docx(file_bytes: bytes) -> tuple[str, int]:
    """Extract text from Word DOCX."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs), len(paragraphs)
    except ImportError:
        return "[DOCX extraction requires python-docx]", 0


def _extract_csv(file_bytes: bytes) -> tuple[str, int]:
    """Extract text from CSV."""
    text = file_bytes.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(text))
    rows = [" | ".join(row) for row in reader]
    return "\n".join(rows), len(rows)


def _extract_json(file_bytes: bytes) -> tuple[str, int]:
    """Extract text from JSON - pretty print it."""
    text = file_bytes.decode('utf-8', errors='ignore')
    try:
        data = json.loads(text)
        return json.dumps(data, indent=2), 1
    except:
        return text, 1


def _extract_html(file_bytes: bytes) -> tuple[str, int]:
    """Extract text from HTML - strip tags."""
    import re
    text = file_bytes.decode('utf-8', errors='ignore')
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean, 1


def _extract_text(file_bytes: bytes) -> tuple[str, int]:
    """Extract plain text."""
    return file_bytes.decode('utf-8', errors='ignore'), 1


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
