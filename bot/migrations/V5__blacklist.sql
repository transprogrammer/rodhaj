-- Revision Version: V5
-- Revises: V4
-- Creation Date: 2024-02-08 00:45:11.293618 UTC
-- Reason: blacklist


CREATE TABLE IF NOT EXISTS blacklist (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    entity_id BIGINT,
    UNIQUE (guild_id, entity_id)
);

CREATE INDEX IF NOT EXISTS blacklist_guild_id_idx ON blacklist (guild_id);
CREATE INDEX IF NOT EXISTS blacklist_entity_id_idx ON blacklist (entity_id);