import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const schemaPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../grow8-backend/db/init/001_schema.sql",
);
const schema = readFileSync(schemaPath, "utf8");

test("DB-SRC-001 @smoke Schema source declares the current domain tables", () => {
  const tables = [...schema.matchAll(/CREATE TABLE\s+([a-z_]\w*)\s*\(/gi)]
    .map((match) => match[1])
    .sort();

  expect(tables).toEqual([
    "admin_review",
    "application",
    "badge",
    "contributor_badge",
    "contributor_profile",
    "contributor_resume",
    "contributor_skill",
    "creator_organization",
    "feedback",
    "notification",
    "opportunity",
    "opportunity_category",
    "opportunity_skill",
    "point_transaction",
    "skill",
    "submission_attachment",
    "user_account",
    "work_submission",
    "work_verification",
  ]);
});

test("DB-SRC-002 @sanity Schema source defines current derived views and integrity procedures", () => {
  const views = [...schema.matchAll(/CREATE OR REPLACE VIEW\s+([a-z_]\w*)/gi)]
    .map((match) => match[1])
    .sort();
  const procedures = [...schema.matchAll(/CREATE PROCEDURE\s+([a-z_]\w*)/gi)]
    .map((match) => match[1])
    .sort();

  expect(views).toEqual([
    "v_contributor_skill",
    "v_contributor_verified_hours",
    "v_feedback_status",
    "v_leaderboard",
    "v_user_rating",
  ]);
  expect(procedures).toEqual([
    "grow8_require_accepted_application",
    "grow8_require_application_capacity",
    "grow8_require_application_identity",
    "grow8_require_application_status_change_allowed",
    "grow8_require_feedback_participants",
    "grow8_require_point_source",
    "grow8_require_role",
    "grow8_require_role_change_allowed",
    "grow8_require_verifier",
  ]);
});
