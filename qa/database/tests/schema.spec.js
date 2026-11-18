import mysql from "mysql2/promise";
import { expect, test } from "@playwright/test";

let connection;

test.beforeAll(async () => {
  connection = await mysql.createConnection({
    host: process.env.DB_HOST ?? "127.0.0.1",
    port: Number(process.env.DB_PORT ?? 3307),
    user: process.env.DB_USER ?? "grow8",
    password: process.env.DB_PASSWORD ?? "change-me",
    database: process.env.DB_NAME ?? "grow8",
  });
});

test.afterAll(async () => {
  await connection?.end();
});

test("DB-001 @smoke Current schema contains the application tables", async () => {
  const [rows] = await connection.query(
    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'",
  );
  const actual = rows.map(({ TABLE_NAME }) => TABLE_NAME).sort();
  expect(actual).toEqual([
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

test("DB-002 @sanity Development seed includes expected user roles and reference data", async () => {
  const [users] = await connection.query(
    "SELECT role, COUNT(*) AS count FROM user_account GROUP BY role",
  );
  expect(Object.fromEntries(users.map(({ role, count }) => [role, Number(count)]))).toEqual({
    admin: 1,
    contributor: 3,
    creator: 3,
  });

  const [[{ category_count: categoryCount, skill_count: skillCount }]] = await connection.query(
    "SELECT (SELECT COUNT(*) FROM opportunity_category) AS category_count, (SELECT COUNT(*) FROM skill) AS skill_count",
  );
  expect(Number(categoryCount)).toBe(2);
  expect(Number(skillCount)).toBe(12);
});

test("DB-003 @regression Derived views and business-rule procedures are installed", async () => {
  const [views] = await connection.query(
    "SELECT TABLE_NAME FROM information_schema.VIEWS WHERE TABLE_SCHEMA = DATABASE()",
  );
  expect(views.map(({ TABLE_NAME }) => TABLE_NAME).sort()).toEqual([
    "v_contributor_skill",
    "v_contributor_verified_hours",
    "v_feedback_status",
    "v_leaderboard",
    "v_user_rating",
  ]);

  const [procedures] = await connection.query(
    "SELECT ROUTINE_NAME FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_TYPE = 'PROCEDURE'",
  );
  expect(procedures.map(({ ROUTINE_NAME }) => ROUTINE_NAME).sort()).toEqual([
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

test("DB-004 @regression Resume and notification relationships enforce ownership and cleanup", async () => {
  const [rows] = await connection.query(
    `SELECT TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, DELETE_RULE
     FROM information_schema.REFERENTIAL_CONSTRAINTS
     WHERE CONSTRAINT_SCHEMA = DATABASE()
       AND ((TABLE_NAME = 'contributor_resume' AND CONSTRAINT_NAME = 'fk_contributor_resume_contributor')
         OR (TABLE_NAME = 'notification' AND CONSTRAINT_NAME IN ('fk_notification_user', 'fk_notification_opportunity')))` ,
  );
  expect(rows).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        TABLE_NAME: "contributor_resume",
        CONSTRAINT_NAME: "fk_contributor_resume_contributor",
        REFERENCED_TABLE_NAME: "contributor_profile",
        DELETE_RULE: "CASCADE",
      }),
      expect.objectContaining({
        TABLE_NAME: "notification",
        CONSTRAINT_NAME: "fk_notification_user",
        REFERENCED_TABLE_NAME: "user_account",
        DELETE_RULE: "CASCADE",
      }),
      expect.objectContaining({
        TABLE_NAME: "notification",
        CONSTRAINT_NAME: "fk_notification_opportunity",
        REFERENCED_TABLE_NAME: "opportunity",
        DELETE_RULE: "SET NULL",
      }),
    ]),
  );
});
