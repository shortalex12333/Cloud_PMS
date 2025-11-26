-- Migration: 00_enable_extensions
-- Enable required Postgres extensions

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for text search optimization
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable btree_gin for multi-column indexes
CREATE EXTENSION IF NOT EXISTS btree_gin;
