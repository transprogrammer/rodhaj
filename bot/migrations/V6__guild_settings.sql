-- Revision Version: V6
-- Revises: V5
-- Creation Date: 2024-05-21 04:12:28.443725 UTC
-- Reason: guild_settings

-- The guild settings is just an jsonb column that stores extra settings for the guild.
-- Misc settings like enabling an certain feature, etc.
-- Of course, the settings are highly structured
ALTER TABLE IF EXISTS guild_config ADD COLUMN settings JSONB DEFAULT ('{}'::jsonb) NOT NULL;