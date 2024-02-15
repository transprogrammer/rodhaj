-- Revision Version: V6
-- Revises: V5
-- Creation Date: 2024-02-09 06:46:23.126029 UTC
-- Reason: timer schema

CREATE TABLE IF NOT EXISTS timers (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    expires TIMESTAMP,
    created TIMESTAMP DEFAULT (now() at time zone 'utc'),
    event TEXT,
);

CREATE INDEX IF NOT EXISTS timers_expires_idx ON timers (expires);