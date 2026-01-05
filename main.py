"""
CelesteOS Document Extraction Service
Dedicated microservice for extracting text from documents (PDF, DOCX, etc.)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber
import httpx
import io
import os

app = FastAPI(
    title="CelesteOS Extraction Service",
    description="Document text extraction microservice",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class URLRequest(BaseModel):
    storage_url: str
    service_key: str = None

class ExtractionResponse(BaseModel):
    text: str
    pages: int = 0
    chars: int = 0
    status: str = "success"

# --- Health Check ---

@app.get("/")
def health():
    return {"status": "ok", "service": "extraction"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# --- PDF Extraction ---

@app.post("/extract/pdf", response_model=ExtractionResponse)
async def extract_pdf(file: UploadFile = File(...)):
    """Extract text from uploaded PDF file."""
    try:
        contents = await file.read()
        text, pages = _parse_pdf(contents)
        return ExtractionResponse(text=text, pages=pages, chars=len(text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

@app.post("/extract/pdf-from-url", response_model=ExtractionResponse)
async def extract_pdf_from_url(request: URLRequest):
    """Fetch PDF from URL and extract text."""
    try:
        headers = {}
        if request.service_key:
            headers = {
                "apikey": request.service_key,
                "Authorization": f"Bearer {request.service_key}"
            }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(request.storage_url, headers=headers)
            resp.raise_for_status()
            pdf_bytes = resp.content
        
        text, pages = _parse_pdf(pdf_bytes)
        return ExtractionResponse(text=text, pages=pages, chars=len(text))
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch PDF: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

def _parse_pdf(pdf_bytes: bytes) -> tuple[str, int]:
    """Parse PDF bytes and return (text, page_count)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        
        full_text = "\n\n".join(pages_text)
        return full_text, len(pdf.pages)

# --- Generic Text Extraction (for non-PDF) ---

@app.post("/extract/text", response_model=ExtractionResponse)
async def extract_text(file: UploadFile = File(...)):
    """Extract text from text-based files (txt, csv, json, xml, etc.)."""
    try:
        contents = await file.read()
        text = contents.decode('utf-8', errors='ignore')
        return ExtractionResponse(text=text, chars=len(text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

@app.post("/extract/text-from-url", response_model=ExtractionResponse)
async def extract_text_from_url(request: URLRequest):
    """Fetch text file from URL and return contents."""
    try:
        headers = {}
        if request.service_key:
            headers = {
                "apikey": request.service_key,
                "Authorization": f"Bearer {request.service_key}"
            }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(request.storage_url, headers=headers)
            resp.raise_for_status()
            text = resp.text
        
        return ExtractionResponse(text=text, chars=len(text))
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

# --- Auto-detect and Extract ---

class AutoExtractRequest(BaseModel):
    storage_url: str
    content_type: str
    service_key: str = None

@app.post("/extract/auto", response_model=ExtractionResponse)
async def extract_auto(request: AutoExtractRequest):
    """Auto-detect file type and extract text accordingly."""
    try:
        headers = {}
        if request.service_key:
            headers = {
                "apikey": request.service_key,
                "Authorization": f"Bearer {request.service_key}"
            }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(request.storage_url, headers=headers)
            resp.raise_for_status()
            file_bytes = resp.content
        
        # Route by content type
        if request.content_type == "application/pdf":
            text, pages = _parse_pdf(file_bytes)
            return ExtractionResponse(text=text, pages=pages, chars=len(text))
        else:
            # Treat as text
            text = file_bytes.decode('utf-8', errors='ignore')
            return ExtractionResponse(text=text, chars=len(text))
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
