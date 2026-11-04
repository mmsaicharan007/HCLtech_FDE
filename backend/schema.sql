-- Backend-only private schema; deliberately outside the public Data API schema.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS support;
CREATE TABLE IF NOT EXISTS support.tickets (
    ticket_id text PRIMARY KEY,
    category text NOT NULL,
    subject text NOT NULL,
    description text NOT NULL,
    tags text[] NOT NULL DEFAULT '{}',
    created_at date NOT NULL,
    status text NOT NULL,
    embedding vector(384) NOT NULL,
    embedding_model text NOT NULL,
    search_document tsvector GENERATED ALWAYS AS
      (to_tsvector('english', subject || ' ' || description)) STORED
);
CREATE INDEX IF NOT EXISTS tickets_search_idx ON support.tickets USING gin(search_document);
CREATE INDEX IF NOT EXISTS tickets_created_idx ON support.tickets(created_at);
-- Exact cosine search is sufficient for this demo; benchmark before adding ANN indexes.
CREATE TABLE IF NOT EXISTS support.resolution_attempts (
    attempt_id text PRIMARY KEY,
    ticket_id text NOT NULL REFERENCES support.tickets(ticket_id) ON DELETE CASCADE,
    notes text NOT NULL
);
CREATE TABLE IF NOT EXISTS support.outcome_feedback (
    attempt_id text NOT NULL REFERENCES support.resolution_attempts(attempt_id) ON DELETE CASCADE,
    source text NOT NULL CHECK (source IN ('synthetic_demo', 'user')),
    outcome text NOT NULL CHECK (outcome IN ('confirmed_resolved','confirmed_unresolved')),
    comment text NOT NULL,
    PRIMARY KEY (attempt_id, source)
);
REVOKE ALL ON SCHEMA support FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA support FROM PUBLIC;
