-- =============================================================================
-- GROW8 - ENSF 608 implementation, step 0: create an empty database.
--
-- Creates the database grow8_608 from scratch. It uses its own name so it never
-- touches the application's `grow8` database in Docker.
-- WARNING: drops grow8_608 first if it already exists.
-- =============================================================================

DROP DATABASE IF EXISTS grow8_608;
CREATE DATABASE grow8_608 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE grow8_608;
