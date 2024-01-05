-- Revision Version: V2
-- Revises: V1
-- Creation Date: 2023-12-03 01:12:48.072364 UTC
-- Reason: config_changes

-- Include the ticket broadcast url as this is needed to send to the different threads
ALTER TABLE guild_config ADD COLUMN ticket_broadcast_url TEXT;

-- Never going to get used, so remove it
ALTER TABLE user_config DROP COLUMN webhook_id;
ALTER TABLE user_config ALTER COLUMN permission_level SET DEFAULT 1;
ALTER TABLE user_config ALTER COLUMN current_tickets SET DEFAULT 0;
ALTER TABLE user_config ADD COLUMN current_ticket BIGINT REFERENCES tickets (id);
CREATE INDEX IF NOT EXISTS user_config_current_ticket_idx ON user_config (current_ticket);

-- Make the tickets associated with each guild
-- This way, if we ever want to expand Rodhaj into multiple servers, we can
ALTER TABLE tickets ADD COLUMN location_id BIGINT REFERENCES guild_config (id);
CREATE INDEX IF NOT EXISTS tickets_location_id_idx ON tickets (location_id);

-- Remake the ticket indexes as they need to be unique per owner
DROP INDEX IF EXISTS tickets_owner_id_idx;
CREATE UNIQUE INDEX IF NOT EXISTS tickets_owner_id_idx ON tickets (owner_id);