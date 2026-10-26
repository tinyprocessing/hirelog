-- Semantic search: one 384-dim vector per note (multilingual MiniLM), cosine distance, HNSW index.
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE note ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE note ADD COLUMN IF NOT EXISTS embedded_at timestamptz;
CREATE INDEX IF NOT EXISTS note_embedding_hnsw ON note USING hnsw (embedding vector_cosine_ops);
