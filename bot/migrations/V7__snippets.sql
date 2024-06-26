-- Revision Version: V7
-- Revises: V6
-- Creation Date: 2024-06-25 22:08:13.554817 UTC
-- Reason: snippets

CREATE TABLE IF NOT EXISTS snippets (
    id SERIAL PRIMARY KEY,
    name TEXT,
    content TEXT,
    uses INTEGER DEFAULT (0),
    owner_id BIGINT,
    location_id BIGINT, 
    created_at TIMESTAMPTZ DEFAULT (now() at time zone 'utc')
);

-- Create indices to speed up regular and trigram searches
CREATE INDEX IF NOT EXISTS snippets_name_idx ON snippets (name);
CREATE INDEX IF NOT EXISTS snippets_location_id_idx ON snippets (location_id);
CREATE INDEX IF NOT EXISTS snippets_name_trgm_idx ON snippets USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS snippets_name_lower_idx ON snippets (LOWER(name));
CREATE UNIQUE INDEX IF NOT EXISTS snippets_uniq_idx ON snippets (LOWER(name), location_id);

CREATE TABLE IF NOT EXISTS snippets_lookup (
    id SERIAL PRIMARY KEY,
    name TEXT,
    location_id BIGINT,
    owner_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT (now() at time zone 'utc'),
    snippets_id INTEGER REFERENCES snippets (id) ON DELETE CASCADE ON UPDATE NO ACTION
);

CREATE INDEX IF NOT EXISTS snippets_lookup_name_idx ON snippets_lookup (name);
CREATE INDEX IF NOT EXISTS snippets_lookup_location_id_idx ON snippets_lookup (location_id);
CREATE INDEX IF NOT EXISTS snippets_lookup_name_trgm_idx ON snippets_lookup USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS snippets_lookup_name_lower_idx ON snippets_lookup (LOWER(name));
CREATE UNIQUE INDEX IF NOT EXISTS snippets_lookup_uniq_idx ON snippets_lookup (LOWER(name), location_id);