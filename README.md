# GROW8 – Earn, Learn and Grow

**Course:** ENSF 607 / ENSF 608 – Team Project  
**Selected UN Sustainable Development Goal:** SDG 8 – Decent Work and Economic Growth  
**Team:** Group 2

## Team Members

- Ashwin Chockalingam Shanmugam
- Lila Sanjay Kumar Gorlie
- Arman Hossain Dipu Khan
- Maheen Hoque
- Vineeth Donthamsetty
- Aparna Ayyalasomayajula

---

## 1. Introduction

Students and early-career workers often struggle to gain their first verifiable work experience, while small businesses, nonprofits, and event organizers have short-term tasks they lack the time or budget to complete. These tasks may include digitizing records, organizing data, and supporting events.

**GROW8** is a web platform designed to connect people who need short-term work completed with students and early-career workers seeking practical experience, skill development, and potential earnings.

The platform has three main user roles:

- **Creator:** Local businesses, nonprofits, and event organizers who post short-term work opportunities.
- **Contributor:** Students and early-career workers who apply for opportunities and complete assigned work.
- **Admin:** Administrators who review feedback, investigate discrepancies, and flag misleading opportunities or inappropriate behaviour.

### Types of Opportunities

GROW8 supports two categories of opportunities:

1. **Knowledge-based opportunities:** Digital support, data organization, record digitization, and similar tasks.
2. **Community opportunities:** Physical tasks, community activities, and event-based support.

Creators specify the requirements, duration, expected hours, compensation, applicant limits, deadlines, working conditions, safety information, and accessibility details for each opportunity.

The system validates mandatory information before an opportunity can be published. Creators can select applicants and verify completed work, allowing the platform to update contributors' verified hours and skills.

Admins review feedback, investigate discrepancies between published and actual working conditions, and flag misleading opportunities or inappropriate behaviour. Only approved feedback affects public ratings.

### Project Scope

- Compensation is disclosed on the platform but arranged off-platform.
- GROW8 does not process payments.
- Points, badges, and a public leaderboard are considered stretch goals.

---

## 2. Proposed Architecture

GROW8 follows an **event-driven architecture** using FastAPI as the event producer, RabbitMQ as the message broker, and three Python consumer services.

FastAPI validates user actions and commits changes to MySQL before publishing the corresponding events. RabbitMQ routes events to the subscribed services, which perform the required actions.

### Architecture Components

| Component | Responsibility |
| --- | --- |
| React Frontend | Provides the user interface for Creators, Contributors, and Admins. |
| FastAPI Backend | Validates requests, handles business logic, exposes REST APIs, and publishes events. |
| MySQL Database | Stores users, opportunities, applications, submissions, hours, skills, feedback, ratings, and notifications. |
| File Storage | A Docker volume for uploaded files (contributor resumes and work submission attachments), behind a storage interface that could later be swapped for cloud storage. |
| RabbitMQ | Routes published events to subscribed consumer services, with delayed retries and a dead-letter queue per service. |
| Creator Service | Notifies creators when their opportunity is published, when someone applies or withdraws, and when work awaits verification. |
| Contributor Service | Notifies contributors of matching opportunities, application decisions, cancellations, and whether their work was verified. Verified hours and skills are computed from approved work. |
| Admin Service | Notifies admins of feedback awaiting review (discrepancy reports first) and of reported opportunities. |

### Event Flow

| Producer Action | Event | Consumer Service | Resulting Behaviour | Status |
| --- | --- | --- | --- | --- |
| Creator actions | `OPPORTUNITY_CREATED` | Contributor Service, Creator Service | Notifies matching contributors about the new opportunity, and confirms to the creator that it was published. | Implemented |
| Creator actions | `APPLICATION_DECIDED` | Contributor Service | Notifies contributors of application decisions. | Implemented |
| Creator actions | `OPPORTUNITY_CANCELLED` | Contributor Service | Notifies pending and accepted applicants that the opportunity was cancelled. | Implemented |
| Creator actions | `WORK_VERIFIED` | Contributor Service | Notifies contributors that their work was verified, with the hours; it now counts toward their verified hours and skills. | Implemented |
| Creator actions | `WORK_REJECTED` | Contributor Service | Notifies contributors about rejected work, with the creator's comment. | Implemented |
| Contributor actions | `APPLICATION_SUBMITTED` | Creator Service | Notifies creators about new applications. | Implemented |
| Contributor actions | `APPLICATION_WITHDRAWN` | Creator Service | Notifies creators when an applicant withdraws, and whether a place opened up. | Implemented |
| Contributor actions | `WORK_SUBMITTED` | Creator Service | Notifies creators about work awaiting verification. | Implemented |
| Creator or Contributor actions | `FEEDBACK_SUBMITTED` | Admin Service | Alerts admins to feedback awaiting review, flagging discrepancy reports. | Implemented |
| Admin actions | `FEEDBACK_APPROVED` | Creator Service, Contributor Service | Notifies the author that the feedback was published and the subject that they received a rating; it now counts toward the public rating. | Implemented |
| Contributor actions | `OPPORTUNITY_REPORTED` | Admin Service | Alerts admins that an opportunity was reported, with the reason. | Implemented |
| Admin actions | `OPPORTUNITY_TAKEN_DOWN` | Creator Service, Contributor Service | Tells the creator why their opportunity was taken down, tells its applicants it won't go ahead, and thanks the reporters. | Implemented |
| Admin actions | `REPORT_DISMISSED` | Contributor Service | Tells the reporter the opportunity stays up, with the admin's note. | Implemented |
| Admin actions | `FEEDBACK_REJECTED` | Creator Service, Contributor Service | Notifies the feedback author, with the admin's reason. The subject is not told. | Implemented |

Event payloads, queues and failure handling are documented in [grow8-backend/docs/events.md](grow8-backend/docs/events.md).

### Database

GROW8 uses one shared MySQL database instance as a deliberate scope simplification.

The database stores:

- Users and roles
- Opportunities
- Applications
- Contributor resumes (metadata; the files themselves are on the file storage volume)
- Work submissions
- Verified hours
- Skills
- Feedback
- Ratings
- Notifications

The schema has 19 tables. Business rules (such as applicant limits and deadlines) are enforced by both the API and database triggers. See the [data dictionary](docs/db/data-dictionary.md) and [relational schema](docs/db/relational-schema.md).

Failed event publications are retried. A consumer whose handler fails retries the event after 5 s, 30 s and 120 s (through RabbitMQ retry queues) before moving it to its dead-letter queue. A transactional outbox is considered future work.

---

## 3. Technology Stack

| Component | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, CSS, lucide-react icons |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, REST APIs |
| Database | MySQL 8.4 |
| Event Broker | RabbitMQ |
| File Storage | Docker volume |
| Testing | pytest (about 400 automated API and consumer tests against a real MySQL), Postman/Newman end-to-end collection, manual testing, execution reports |
| Version Control | GitHub |
| Deployment | Docker Compose |

---

## 4. Alignment with UN Sustainable Development Goal

GROW8 supports **SDG 8 – Decent Work and Economic Growth** by connecting students and early-career workers with short-term opportunities that build practical skills and verifiable experience.

| SDG 8 Target                                         | Tier       | How GROW8 Supports the Target                                                                                                                              | Measurable Indicator                                                                                           |
| ---------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 8.2 – Productivity through technology and innovation | Supporting | Enables knowledge-based opportunities that support digital improvements in organizations.                                                                  | Number and share of completed opportunities in the knowledge-based category.                                   |
| 8.3 – Entrepreneurship and MSME development          | Supporting | Connects small businesses with contributors to support productive business activities.                                                                     | Number of small-business Creators with at least one completed opportunity.                                     |
| 8.5 – Productive employment and decent work          | Core       | Provides opportunities with transparent compensation, expected hours, working conditions, and accessibility information.                                   | Share of published opportunities passing validation with all mandatory fields disclosed.                       |
| 8.6 – Youth employment and training                  | Core       | Enables students and early-career workers to gain practical skills and verified work experience.                                                           | Verified experience hours, acquired skills, and completed opportunities recorded per Contributor.              |
| 8.8 – Labour rights and workplace safety             | Core       | Requires safety information when opportunities are created and allows Admins to review feedback for discrepancies between published and actual conditions. | Safety information recorded per opportunity; number of Admin-reviewed discrepancy reports and resulting flags. |

---

## 5. Team Roles

| Team Member                   | Responsibilities                                             |
| ----------------------------- | ------------------------------------------------------------ |
| Ashwin Chockalingam Shanmugam | Frontend and Backend Development                             |
| Lila Sanjay Kumar Gorlie      | Frontend, Backend, and Team Management                       |
| Arman Hossain Dipu Khan       | Backend and Frontend Development                             |
| Maheen Hoque                  | Backend and Frontend Development                             |
| Vineeth Donthamsetty          | Database and Backend Development                             |
| Aparna Ayyalasomayajula       | Requirements Analysis, Manual Testing, and Artifact Creation |

---

## 6. Project Objectives

- Connect students and early-career workers with short-term work opportunities.
- Help contributors develop practical skills and gain verifiable work experience.
- Enable creators to publish opportunities with clear requirements and working conditions.
- Maintain verified records of completed work, experience hours, and acquired skills.
- Use event-driven communication to notify users about relevant system activities.
- Support responsible feedback review and transparent public ratings.
- Promote decent work and economic growth in alignment with UN SDG 8.

---

## 7. Future Enhancements

The following features may be considered as future enhancements, subject to project scope and available time:

- Points and badges for completed opportunities.
- A public contributor leaderboard.
- A transactional outbox for more reliable event publishing.
- Additional enhancements to notifications and user experience.

---

## 8. Project Status

GROW8 is being developed as a team project for ENSF 607 / ENSF 608. The whole stack runs locally with Docker Compose.

**Implemented (backend):**

- Sign-in with JWT, role-based access (creator, contributor, admin), password change, and changing your name.
- Creator organizations: creators edit their organization's name, type, description, website and city, and every one of their opportunities shows the change.
- Contributor profiles: contributors edit their headline, bio, institution, city and listed skills, and see every skill approved work has verified, including ones they never listed; new skills change which opportunities they're notified about.
- Opportunities: drafts, validation of mandatory disclosures, publishing, public browse with search, filters and sorting, closing and cancelling.
- Applications: apply, review, accept or reject, withdraw, and the creator's view of applications received, with applicant limits and deadlines enforced.
- Optional PDF resume upload for contributors, visible to creators they applied to.
- Work submission: accepted contributors submit their work once, with up to 5 files, for the creator to verify.
- Work verification: creators review submitted work and approve it with verified hours or reject it with a comment; approved work counts toward the contributor's verified hours and skills.
- Feedback and admin review: after verified work, the contributor and the creator rate each other; admins approve or reject each feedback (discrepancy reports first), and public ratings count approved feedback only.
- Reports and takedown: contributors report misleading, unsafe, discriminatory or scam opportunities; admins dismiss reports or take the opportunity down, and the creator never learns who reported.
- Event-driven notifications for publishing, applications, decisions, withdrawals, cancellations, work submissions, verification decisions and feedback review, with delayed retries and dead-letter queues.

**Frontend:** contributor, creator and admin screens are connected to the backend for every feature above.

**Known limitation:** self-service sign-up is not implemented; accounts come from the development seed data (see [docs.md](docs.md)).

**Planned:** the future enhancements in section 7.

**Getting started:** setup, dev accounts, everyday commands and an API walkthrough are in [docs.md](docs.md).

---

## 9. Useful Links

- [ENSF 607 Submission]()
- [ENSF 607 Submission]()
- [Developer guide: setup and usage](docs.md)
- [User Stories](https://docs.google.com/document/d/1muAfw88L-geIDE3aOM3-dn9aTc-V78F9JkT1dOCExAI/edit?usp=sharing "Google Doc File")

### Design and diagrams

- [Architecture diagram, as implemented](docs/diagrams/GROW8-Architecture.png) ([SVG](docs/diagrams/GROW8-Architecture.svg)); original proposal: [architectureDiagram607Project.png](docs/diagrams/architectureDiagram607Project.png)
- [Class diagram](docs/diagrams/class-diagram.drawio.svg)
- [ER diagram, generated from the live schema](docs/diagrams/GROW8-ER-Diagram.svg) ([PDF](docs/diagrams/GROW8-ER-Diagram.pdf)); original hand-drawn version: [ER-diagram.drawio.svg](docs/diagrams/ER-diagram.drawio.svg)
- [Relational schema diagram](docs/diagrams/GROW8-Relational-Schema.svg)

### Database (ENSF 608)

- [Data dictionary](docs/db/data-dictionary.md) (original [Google Sheet](https://docs.google.com/spreadsheets/d/10z_qGlHWLnbuE7DJr4je_tGaTtfz8Kyzln5PdvFpMBU/edit?usp=sharing "Google Sheet File"))
- [Relational schema](docs/db/relational-schema.md)
- [Functional dependencies and normalization](docs/db/functional-dependencies.md)
- [Relationship validation](docs/db/relationship-validation.md)
- [Database test report](docs/db/test-report.md)

### Backend

- [API contract](grow8-backend/docs/api-contract.md)
- [Events](grow8-backend/docs/events.md)
- [Error codes](grow8-backend/docs/error-codes.md)
- [Architecture decision records](grow8-backend/docs/adr/)

## 10. Use of Generative AI Tools

As required by the course policy on generative AI, the team discloses the tools it used and how:

- **Claude (Anthropic)**: used to learn and break down hard concepts (for example normalization, triggers and event-driven messaging), to draft answers and documentation, and to help draft and debug parts of the code and tests.
- **GitHub Copilot**: code completion and suggestions in the editor.

All tool-assisted output was reviewed, tested, changed where needed and committed by the team member responsible for that part. Each member understands and can explain the work they submitted.
