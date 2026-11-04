#!/bin/sh
# DEVELOPMENT ONLY. Creates an empty `grow8_test` database for the API integration
# tests, so running tests never changes the shared dev data in MYSQL_DATABASE.
# The tests load 001_schema.sql and 002_seed.sql into it themselves.
# Runs during MySQL's first start, against the temporary socket-only server.
set -e

mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" <<EOSQL
CREATE DATABASE IF NOT EXISTS grow8_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON grow8_test.* TO '${MYSQL_USER}'@'%';
EOSQL
