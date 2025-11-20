"""
Embedding generation utilities
"""
import httpx
from config import settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


async def get_embedding(text: str) -> list[float]:
    """
    Generate embedding for text using OpenAI API

    Args:
        text: Text to embed

    Returns:
        Embedding vector as list of floats
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text,
                    "model": settings.embedding_model
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]

            # Validate dimensions
            if len(embedding) != settings.embedding_dimensions:
                logger.warning(
                    f"Embedding dimension mismatch: got {len(embedding)}, "
                    f"expected {settings.embedding_dimensions}"
                )

            return embedding

    except httpx.HTTPError as e:
        logger.error(f"HTTP error generating embedding: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in batch

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": texts,
                    "model": settings.embedding_model
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings

    except httpx.HTTPError as e:
        logger.error(f"HTTP error generating batch embeddings: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise
