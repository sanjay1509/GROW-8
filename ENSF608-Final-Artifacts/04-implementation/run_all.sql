-- =============================================================================
-- GROW8 - ENSF 608: create and populate the whole database in one command.
--
-- Run from inside this folder (SOURCE paths are relative to where mysql starts):
--     cd ENSF608-Final-Artifacts/04-implementation
--     mysql -u root -p < run_all.sql
-- =============================================================================

SOURCE 00_create_database.sql;
SOURCE 01_create_schema.sql;
SOURCE 02_populate_reference_and_core_data.sql;
SOURCE 03_populate_workflow_history.sql;
SOURCE 04_verify_database.sql;
