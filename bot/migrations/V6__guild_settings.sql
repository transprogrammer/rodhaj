-- Revision Version: V6
-- Revises: V5
-- Creation Date: 2024-05-21 04:12:28.443725 UTC
-- Reason: guild_settings

-- We can't store intervals properly in JSON format without doing some janky stuff
-- So these needs to be separate columns
ALTER TABLE IF EXISTS guild_config ADD COLUMN account_age INTERVAL DEFAULT ('2 hours'::interval) NOT NULL;
ALTER TABLE IF EXISTS guild_config ADD COLUMN guild_age INTERVAL DEFAULT ('2 days':: interval) NOT NULL;

-- The guild settings is just an jsonb column that stores extra settings for the guild.
-- Misc settings like enabling an certain feature, etc.
-- Of course, the settings are highly structured
ALTER TABLE IF EXISTS guild_config ADD COLUMN settings JSONB DEFAULT ('{}'::jsonb) NOT NULL;