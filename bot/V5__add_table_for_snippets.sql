-- Revision Version: V5
-- Revises: V4
-- Creation Date: 2024-03-10 05:51:39.252162 UTC
-- Reason: add table for snippets

CREATE TABLE IF NOT EXISTS snippets
(
    guild_id bigint NOT NULL,
    name     VARCHAR(100),
    content  TEXT,
    PRIMARY KEY (guild_id, name)
);
