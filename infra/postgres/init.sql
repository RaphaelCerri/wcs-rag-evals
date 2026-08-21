CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS vector_indexes (
    index_id text PRIMARY KEY,
    model_id text NOT NULL,
    model_revision text NOT NULL,
    dimensions integer NOT NULL CHECK (dimensions > 0),
    corpus_manifest_sha256 text NOT NULL,
    chunk_count integer NOT NULL CHECK (chunk_count >= 0),
    configuration jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    index_id text NOT NULL REFERENCES vector_indexes(index_id) ON DELETE CASCADE,
    chunk_id text NOT NULL,
    document_id text NOT NULL,
    source_id text NOT NULL,
    source_path text NOT NULL,
    authority text NOT NULL,
    kind text NOT NULL,
    heading text NOT NULL,
    ordinal integer NOT NULL,
    content text NOT NULL,
    embedding vector(384) NOT NULL,
    PRIMARY KEY (index_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS rag_chunks_document_idx
    ON rag_chunks (index_id, document_id);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw_idx
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
