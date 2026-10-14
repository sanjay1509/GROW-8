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

| Component           | Responsibility                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------- |
| React Frontend      | Provides the user interface for Creators, Contributors, and Admins.                           |
| FastAPI Backend     | Validates requests, handles business logic, exposes REST APIs, and publishes events.          |
| MySQL Database      | Stores users, opportunities, applications, submissions, hours, skills, feedback, and ratings. |
| RabbitMQ            | Routes published events to subscribed consumer services.                                      |
| Creator Service     | Handles notifications about applications and work awaiting verification.                      |
| Contributor Service | Handles opportunity notifications, application decisions, and verified experience updates.    |
| Admin Service       | Handles feedback awaiting review and administrative feedback decisions.                       |

### Event Flow

| Producer Action                | Event                   | Consumer Service    | Resulting Behaviour                                                  |
| ------------------------------ | ----------------------- | ------------------- | -------------------------------------------------------------------- |
| Creator actions                | `OPPORTUNITY_CREATED`   | Contributor Service | Notifies contributors about new opportunities.                       |
| Creator actions                | `APPLICATION_DECIDED`   | Contributor Service | Notifies contributors of application decisions.                      |
| Creator actions                | `WORK_VERIFIED`         | Contributor Service | Updates verified hours and skills.                                   |
| Creator actions                | `WORK_REJECTED`         | Contributor Service | Notifies contributors about rejected work.                           |
| Contributor actions            | `APPLICATION_SUBMITTED` | Creator Service     | Notifies creators about new applications.                            |
| Contributor actions            | `WORK_SUBMITTED`        | Creator Service     | Notifies creators about work awaiting verification.                  |
| Creator or Contributor actions | `FEEDBACK_SUBMITTED`    | Admin Service       | Alerts admins to feedback awaiting review.                           |
| Admin actions                  | `FEEDBACK_APPROVED`     | All three services  | Updates public ratings and notifies the feedback author and subject. |
| Admin actions                  | `FEEDBACK_REJECTED`     | All three services  | Records the rejection and notifies the feedback author and subject.  |

### Database

GROW8 uses one shared MySQL database instance as a deliberate scope simplification.

The database stores:

- Users and roles
- Opportunities
- Applications
- Work submissions
- Verified hours
- Skills
- Feedback
- Ratings

Failed event publications are retried. A transactional outbox is considered future work.

---

## 3. Technology Stack

| Component       | Technology                                 |
| --------------- | ------------------------------------------ |
| Frontend        | React, TypeScript, Tailwind CSS            |
| Backend         | Python, FastAPI, REST APIs                 |
| Database        | MySQL                                      |
| Event Broker    | RabbitMQ                                   |
| Testing         | Postman, manual testing, execution reports |
| Version Control | GitHub                                     |
| Deployment      | Docker                                     |

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

GROW8 is being developed as a team project for ENSF 607/ ENSF 608.

The application will combine a React-based frontend, FastAPI backend, MySQL database, and RabbitMQ event broker to support opportunity management, applications, work verification, feedback, and administrative review.

More implementation details, setup instructions, and usage documentation can be added as development progresses.

---

## 9. Useful Links

- [ENSF 607 Submission]()
- [ENSF 607 Submission]()
- [User Stories](https://docs.google.com/document/d/1muAfw88L-geIDE3aOM3-dn9aTc-V78F9JkT1dOCExAI/edit?usp=sharing "Google Doc File")
- [ER Diagram](https://drive.google.com/drive/folders/1QxEIjlInno7MfMk9ziQp9i9-fl-NeeVU?usp=sharing "draw.io Import File")
- [Data Dictionary](https://docs.google.com/spreadsheets/d/10z_qGlHWLnbuE7DJr4je_tGaTtfz8Kyzln5PdvFpMBU/edit?usp=sharing "Google Sheet File")
