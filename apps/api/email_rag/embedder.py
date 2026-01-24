#!/usr/bin/env python3
"""
Email Embedding Generation Module

Generates vector embeddings for email content using OpenAI's text-embedding-3-small model.
Uses OpenAI SDK v1.x syntax.
"""

import os
from typing import Optional, List
from datetime import datetime
from openai import OpenAI


def get_openai_client() -> OpenAI:
    """Get configured OpenAI client."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


async def generate_email_embedding(
    message_id: str,
    preview_text: str,
    yacht_id: str,
    supabase
) -> Optional[List[float]]:
    """
    Generate vector embedding for email preview text and store in database.

    Args:
        message_id: UUID of email_messages record
        preview_text: Email preview text (first 200 chars)
        yacht_id: UUID of yacht (for RLS)
        supabase: Supabase client

    Returns:
        List of 1536 floats (embedding vector) or None on error

    Cost: ~$0.000002 per email (0.0002 cents)
    """
    try:
        client = get_openai_client()

        # Truncate to 8000 chars max (safe limit for embeddings)
        text_to_embed = preview_text[:8000]

        # Generate embedding
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_to_embed
        )

        embedding = response.data[0].embedding
        tokens_used = response.usage.total_tokens
        cost = (tokens_used / 1_000_000) * 0.02

        # Store in database
        supabase.table('email_messages').update({
            'embedding': embedding,
            'extraction_status': 'completed',
            'indexed_at': datetime.utcnow().isoformat()
        }).eq('id', message_id).eq('yacht_id', yacht_id).execute()

        return embedding

    except Exception as e:
        # Log error and update status
        print(f"❌ Embedding generation failed for message {message_id}: {e}")

        try:
            supabase.table('email_messages').update({
                'extraction_status': 'failed'
            }).eq('id', message_id).eq('yacht_id', yacht_id).execute()
        except:
            pass  # Ignore secondary errors

        return None


def generate_embedding_sync(text: str) -> Optional[List[float]]:
    """
    Synchronous version for testing/scripts.

    Args:
        text: Text to generate embedding for

    Returns:
        List of 1536 floats or None on error
    """
    try:
        client = get_openai_client()

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]
        )

        return response.data[0].embedding

    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        return None


def estimate_cost(num_emails: int, avg_preview_length: int = 200) -> dict:
    """
    Estimate costs for embedding generation.

    Args:
        num_emails: Number of emails to process
        avg_preview_length: Average preview text length

    Returns:
        Dictionary with cost breakdown
    """
    # Rough token estimate: 1 token ≈ 4 chars
    tokens_per_email = avg_preview_length // 4
    total_tokens = num_emails * tokens_per_email

    # text-embedding-3-small pricing: $0.02 per 1M tokens
    embedding_cost = (total_tokens / 1_000_000) * 0.02

    # Storage cost: ~12 KB per embedding at $0.024/GB/month (Supabase)
    storage_gb = (num_emails * 12_000) / (1024 ** 3)
    storage_cost_monthly = storage_gb * 0.024

    return {
        'num_emails': num_emails,
        'total_tokens': total_tokens,
        'embedding_cost': embedding_cost,
        'storage_cost_monthly': storage_cost_monthly,
        'total_first_month': embedding_cost + storage_cost_monthly,
        'cost_per_email': embedding_cost / num_emails if num_emails > 0 else 0
    }


if __name__ == '__main__':
    # Test embedding generation
    test_text = "Engine maintenance work order #1234 needs parts from supplier ACME Corp"

    print("Testing embedding generation...")
    embedding = generate_embedding_sync(test_text)

    if embedding:
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   Sample values: [{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}, ...]")

        # Cost estimate
        print("\nCost estimates:")
        for num_emails in [100, 1000, 10000]:
            costs = estimate_cost(num_emails)
            print(f"  {num_emails:,} emails: ${costs['embedding_cost']:.4f} processing + ${costs['storage_cost_monthly']:.4f}/month storage")
    else:
        print("❌ Test failed")
