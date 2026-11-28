# Individual Contributions — Grow8 (ENSF 608, Group 2)

Each member's contributions to the database work, with the evidence in the repository's git history (commits on `main` and merged pull requests).

The evidence is in the repository: `git log --author="<name>"` and the pull requests on GitHub (sanjay1509/GROW-8). Commit counts show where each person's changes are; they do not measure effort.

| Member | Role | Database contributions (ENSF 608) | Evidence |
|---|---|---|---|
| **Vineeth Donthamsetty** | Database and backend; normalization and relationship validation | Relationship validation and functional dependency / BCNF analysis; the integrity triggers (role, application window and applicant limit, verifier, feedback participants, point source) and derived-value views; data dictionary; physical ERD and relational schema generator; updates to the conceptual ERD; workflow seed data; SQL for the eight database questions; database test report; this final artifact package (3NF normalization document, implementation scripts, operations file with stored procedures and evidence). | 50 commits on `main`; PRs #7, #8, #12, #20, #44, #45, #52 |
| **Maheen Hoque** | Backend and frontend | Backend scaffold, the shared seed and test database (ADR 0002), and the schema changes and ADRs for most backend features (ADRs 0001, 0002, 0004–0011, 0013, 0015–0021): application lifecycle and resumes, work verification, feedback and admin review, reports and takedown with the `opportunity_report` and `report_review` tables, contributor profiles, organizations, earned skills in `v_contributor_skill`, resume copies and re-applying. Each came with the ENSF 608 doc and diagram updates. | 96 commits on `main`; PRs #13, #17, #28, #30, #32, #34, #35, #36, #51 |
| **Arman Hossain Dipu Khan** | Backend and frontend | The `notification` table: schema, ORM model and ADR 0003, and the notifications API. The work submission schema, enum, relationships and repository (`work_submission`, `submission_attachment`; ADR 0012). | 22 commits on `main`; PRs #2, #26 |
| **Lila Sanjay Kumar Gorlie** | Frontend, backend and team management | Project management. Application lifecycle and resume flows end to end, including fixes to the application resume and notification flows; frontend migration to Vite and TypeScript. | 34 commits on `main`; PRs #5, #27, #43 |
| **Ashwin Chockalingam Shanmugam** | Frontend and backend | The original conceptual ER diagram (Chen notation), the class diagram and the architecture diagram; creator dashboard frontend. | 10 commits on `main` |
| **Aparna Ayyalasomayajula** | Requirements analysis, manual testing and artifact creation | Requirements and testing artifacts, and the QA automation suite (Playwright smoke tests and test reports).| 15 commits on `main`; PR #54 (QA suite and ENSF 607 test artifacts) |

## Use of generative AI tools

Generative AI use is disclosed in section 11 of the repository README.
