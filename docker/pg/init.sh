#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE ROLE rodhaj WITH LOGIN PASSWORD "$RODHAJ_PASSWORD";
  CREATE DATABASE rodhaj OWNER rodhaj;
EOSQL