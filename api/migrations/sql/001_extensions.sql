-- =========================================================
-- MARAMARA - Migration 001: Enable required extensions
-- =========================================================

-- pgvector for voice embeddings and semantic memory
CREATE EXTENSION IF NOT EXISTS vector;

-- uuid generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgcrypto for hashing / encryption helpers
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- trigram search for phrase mining
CREATE EXTENSION IF NOT EXISTS pg_trgm;
