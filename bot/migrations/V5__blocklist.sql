-- Revision Version: V5
-- Revises: V4
-- Creation Date: 2024-03-03 03:34:28.886003 UTC
-- Reason: blocklist

CREATE TABLE IF NOT EXISTS blocklist (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    entity_id BIGINT,
    dispatch_zone TEXT,
    expires TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT (now() at time zone 'utc'),
    UNIQUE (guild_id, entity_id)
);

CREATE INDEX IF NOT EXISTS blocklist_guild_id_idx ON blocklist (guild_id);
CREATE INDEX IF NOT EXISTS blocklist_entity_id_idx ON blocklist (entity_id);
CREATE INDEX IF NOT EXISTS blocklist_dispatch_zone_idx ON blocklist (dispatch_zone);
CREATE INDEX IF NOT EXISTS blocklist_expires_idx ON blocklist (expires);

-- One feature of the blocklist is to lock tickets.
-- Thus we need to add an column in the tickets table to account for this
ALTER TABLE IF EXISTS tickets ADD COLUMN locked BOOLEAN DEFAULT FALSE;