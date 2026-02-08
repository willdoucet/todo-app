#!/bin/bash
# Create a separate test database for integration tests
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE todo_app_test;
EOSQL
