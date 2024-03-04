-- Revision Version: V5
-- Revises: V4
-- Creation Date: 2024-03-03 03:34:28.886003 UTC
-- Reason: blocklist

CREATE TABLE IF NOT EXISTS blocklist (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    entity_id BIGINT,
    expires TIMESTAMP,
    created TIMESTAMP DEFAULT (now() at time zone 'utc'),
    event TEXT,
    UNIQUE (guild_id, entity_id)
);

CREATE INDEX IF NOT EXISTS blocklist_guild_id_idx ON blocklist (guild_id);
CREATE INDEX IF NOT EXISTS blocklist_entity_id_idx ON blocklist (entity_id);
CREATE INDEX IF NOT EXISTS blocklist_expires_idx ON blocklist (expires);