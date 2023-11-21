-- Revision Version: V1
-- Revises: V0
-- Creation Date: 2023-11-18 20:27:05.564110 UTC
-- Reason: Initial migration

CREATE TABLE IF NOT EXISTS guild_config (
    id BIGINT PRIMARY KEY,
    category_id BIGINT, -- Needed in order to delete it if still exists
    ticket_channel_id BIGINT,
    logging_channel_id BIGINT,
    logging_broadcast_url TEXT,
    locked BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS user_config (
  id BIGINT PRIMARY KEY,
  current_tickets INT,
  webhook_id TEXT,
  permission_level INT
);

CREATE TABLE IF NOT EXISTS tickets (
  id SERIAL PRIMARY KEY,
  thread_id BIGINT,
  owner_id BIGINT REFERENCES user_config (id),
  assignee_id BIGINT,
  tags TEXT[]
);

CREATE INDEX IF NOT EXISTS tickets_owner_id_idx ON tickets (owner_id);
CREATE INDEX IF NOT EXISTS tickets_assignee_id_idx ON tickets (assignee_id);
CREATE INDEX IF NOT EXISTS tickets_tags_idx ON tickets USING GIN (tags);
