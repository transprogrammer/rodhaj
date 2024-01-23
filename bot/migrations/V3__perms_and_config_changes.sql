-- Revision Version: V3
-- Revises: V2
-- Creation Date: 2024-01-23 08:41:08.795638 UTC
-- Reason: perms and config changes

-- Remove this column as it was never used
ALTER TABLE IF EXISTS guild_config DROP COLUMN locked;

-- Also in lieu with permissions based commands, 
-- we don't need to store perms levels on users
ALTER TABLE IF EXISTS user_config DROP COLUMN permission_level;

-- Allow for custom prefixes to be stored. This is simply setup work
-- for another feature
ALTER TABLE IF EXISTS guild_config ADD COLUMN prefix TEXT[];