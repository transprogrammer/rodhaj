-- Revision Version: V4
-- Revises: V3
-- Creation Date: 2024-01-24 02:54:39.500620 UTC
-- Reason: custom prefix support

-- Allow for custom prefixes to be stored. This is simply setup work
-- for another feature
ALTER TABLE IF EXISTS guild_config ADD COLUMN prefix TEXT[];

