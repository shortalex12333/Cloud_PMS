"""
Document Indexing Workflow
Converted from n8n: Index_docs.json

Flow:
1. Receive document metadata from ingestion workflow
2. Call extraction service to get document text
3. Chunk text into segments (RecursiveCharacterTextSplitter)
4. Generate embeddings (OpenAI text-embedding-3-small)
5. Insert chunks + embeddings to search_document_chunks table
6. Respond with success status

Endpoint: POST /webhook/index-documents
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
import httpx
import openai

logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY", "")

# Chunking configuration (matching n8n Text Splitter)
CHUNK_SIZE = 1000  # Default RecursiveCharacterTextSplitter
CHUNK_OVERLAP = 200  # Matching n8n configuration


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Chunk text using recursive character splitting
    Mimics LangChain RecursiveCharacterTextSplitter behavior

    Args:
        text: Full document text
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or len(text) == 0:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        # Find the last newline or space before chunk_size to avoid breaking words
        if end < text_length:
            # Look for newline first
            last_newline = text.rfind("\n", start, end)
            if last_newline != -1 and last_newline > start:
                end = last_newline
            else:
                # Look for space
                last_space = text.rfind(" ", start, end)
                if last_space != -1 and last_space > start:
                    end = last_space

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward, accounting for overlap
        start = end - overlap if end < text_length else text_length

    return chunks


async def generate_embeddings(text_chunks: List[str]) -> List[List[float]]:
    """
    Generate embeddings using OpenAI text-embedding-3-small

    Args:
        text_chunks: List of text chunks

    Returns:
        List of embedding vectors
    """
    embeddings = []

    for chunk in text_chunks:
        response = await openai.Embedding.acreate(
            model="text-embedding-3-small",
            input=chunk
        )
        embedding = response['data'][0]['embedding']
        embeddings.append(embedding)

    return embeddings


async def handle_document_indexing(
    filename: str,
    content_type: str,
    storage_path: str,
    document_id: str,
    yacht_id: str,
    system_tag: str,
    doc_type: str
) -> Dict[str, Any]:
    """
    Handle document indexing - extract text, chunk, embed, and store

    Args:
        filename: Document filename
        content_type: MIME type
        storage_path: Path in Supabase Storage
        document_id: UUID from doc_metadata table
        yacht_id: Yacht UUID
        system_tag: System classification
        doc_type: Document type

    Returns:
        Dict with indexing status and metadata
    """

    try:
        # Step 1: Call extraction service
        extraction_url = os.getenv(
            "EXTRACTION_SERVICE_URL",
            "https://celeste-file-type.onrender.com/extract"
        )

        logger.info(f"Extracting text from {filename} via {extraction_url}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            extraction_payload = {
                "storage_path": storage_path,
                "content_type": content_type,
                "filename": filename,
                "yacht_id": yacht_id,
                "document_id": document_id,
                "doc_type": doc_type,
                "system_tag": system_tag
            }

            extraction_response = await client.post(
                extraction_url,
                json=extraction_payload
            )

            if extraction_response.status_code != 200:
                logger.error(f"Extraction failed: {extraction_response.status_code}")
                return {
                    "status": "error",
                    "message": f"Text extraction failed: {extraction_response.status_code}",
                    "document_id": document_id
                }

            extraction_data = extraction_response.json()
            extracted_text = extraction_data.get("text", "")

            if not extracted_text:
                logger.warning(f"No text extracted from {filename}")
                return {
                    "status": "error",
                    "message": "No text extracted from document",
                    "document_id": document_id
                }

        logger.info(f"Extracted {len(extracted_text)} characters from {filename}")

        # Step 2: Chunk text
        text_chunks = chunk_text(extracted_text)
        logger.info(f"Created {len(text_chunks)} chunks from {filename}")

        if len(text_chunks) == 0:
            return {
                "status": "error",
                "message": "No chunks created from document",
                "document_id": document_id
            }

        # Step 3: Generate embeddings
        logger.info(f"Generating embeddings for {len(text_chunks)} chunks")
        embeddings = await generate_embeddings(text_chunks)

        # Step 4: Insert chunks + embeddings to search_document_chunks
        chunk_records = []
        for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
            chunk_record = {
                "yacht_id": yacht_id,
                "document_id": document_id,
                "chunk_index": i,
                "content": chunk,
                "embedding": embedding,
                "metadata": {
                    "filename": filename,
                    "content_type": content_type,
                    "doc_type": doc_type,
                    "system_tag": system_tag,
                    "chunk_size": len(chunk)
                }
            }
            chunk_records.append(chunk_record)

        logger.info(f"Inserting {len(chunk_records)} chunks to search_document_chunks")

        insert_result = supabase.table("search_document_chunks").insert(chunk_records).execute()

        if not insert_result.data:
            logger.error("Failed to insert chunks")
            return {
                "status": "error",
                "message": "Failed to insert document chunks",
                "document_id": document_id
            }

        # Step 5: Update doc_metadata to mark as indexed
        update_result = supabase.table("doc_metadata").update({
            "indexed": True,
            "indexed_at": datetime.utcnow().isoformat()
        }).eq("id", document_id).execute()

        logger.info(f"Document {document_id} indexed successfully ({len(chunk_records)} chunks)")

        return {
            "status": "indexed",
            "document_id": document_id,
            "yacht_id": yacht_id,
            "filename": filename,
            "chunks_created": len(chunk_records),
            "characters_indexed": len(extracted_text)
        }

    except Exception as error:
        logger.error(f"Document indexing failed: {error}", exc_info=True)
        return {
            "status": "error",
            "message": str(error),
            "document_id": document_id
        }
