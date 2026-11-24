
import {
  ArrowRight,
  BriefcaseBusiness,
  Clock3,
  CheckCircle2,
  Timer,
  ClipboardList,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import FeaturedOpportunities from "../../FeaturedOpportunities/FeaturedOpportunities";
import { getMyApplications } from "../../../services/applications";
import type { Application, ApplicationStatus } from "../../../services/applications";
import { getApplicationSubmission } from "../../../services/submissions";
import type { Submission } from "../../../services/submissions";
import "./ContributorDashboard.css";

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  pending: "Under review",
  accepted: "Accepted",
  rejected: "Not selected",
  withdrawn: "Withdrawn",
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

export default function ContributorDashboard() {
  const userName = localStorage.getItem("user_name") || "Contributor";
  // null until loaded; stays null if the API can't be reached, so the placeholders show.
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [verifiedSubmissions, setVerifiedSubmissions] = useState<Submission[]>([]);

  useEffect(() => {
    let active = true;
    // Newest first; 100 is enough for the counts on a student account.
    getMyApplications({ limit: 100 })
      .then((page) => {
        if (active) {
          setApplications(page.items);
          setTotal(page.total);
          const completed = page.items.filter((application) => application.work_status === "completed");
          void Promise.all(completed.map((application) =>
            getApplicationSubmission(application.application_id).catch(() => null)
          )).then((rows) => {
            if (active) setVerifiedSubmissions(rows.filter((row): row is Submission =>
              row !== null && row.verification?.decision === "approved"
            ));
          });
        }
      })
      .catch(() => {
        // Not signed in or the API is down: keep the placeholders.
      });
    return () => {
      active = false;
    };
  }, []);

  const count = (status: ApplicationStatus) =>
    applications ? String(applications.filter((application) =>
      application.status === status &&
      (status !== "accepted" || application.opportunity.status !== "cancelled") &&
      (status !== "accepted" || application.work_status !== "completed")
    ).length) : "—";

  const completedCount = applications?.filter((application) => application.work_status === "completed").length;
  const verifiedHours = verifiedSubmissions.reduce(
    (sum, submission) => sum + Number(submission.verification?.verified_hours ?? 0), 0
  );
  const stats = [
    {
      label: "Applied",
      value: total !== null ? String(total) : "—",
      icon: ClipboardList,
      color: "blue",
    },
    {
      label: "In Progress",
      value: count("accepted"),
      icon: Clock3,
      color: "amber",
    },
    {
      label: "Completed",
      value: completedCount === undefined ? "—" : String(completedCount),
      icon: CheckCircle2,
      color: "green",
    },
    {
      label: "Verified Hours",
      value: String(verifiedHours),
      icon: Timer,
      color: "cyan",
    },
  ];
  const recent = (applications ?? []).slice(0, 5);

  return (
    <div className="contributor-dashboard">
      <section className="contributor-welcome">
        <div>
          <h1>Welcome back, {userName}!</h1>
          <p>Find new opportunities and keep growing.</p>
        </div>

        <Link
          to="/opportunities"
          className="contributor-welcome-action"
        >
          <BriefcaseBusiness size={18} />
          Explore opportunities
        </Link>
      </section>

      <section
        className="contributor-stats-grid"
        aria-label="Your activity statistics"
      >
        {stats.map(({ label, value, icon: Icon, color }) => (
          <article className="contributor-stat-card" key={label}>
            <span className={`contributor-stat-icon ${color}`}>
              <Icon size={23} strokeWidth={2.2} />
            </span>

            <div className="contributor-stat-info">
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          </article>
        ))}
      </section>

      <section className="contributor-recommendations">
        <div className="contributor-section-heading">
          <div>
            <h2>Recommended Opportunities</h2>
            <p>Find opportunities that help you learn and grow.</p>
          </div>

          <Link to="/opportunities" className="contributor-view-all">
            View All <ArrowRight size={16} />
          </Link>
        </div>

        <FeaturedOpportunities />
      </section>

      <section className="contributor-recent-applications">
        <div className="contributor-section-heading">
          <div>
            <h2>My Recent Applications</h2>
            <p>Keep track of the opportunities you have applied for.</p>
          </div>

          <Link
            to="/contributor/applications"
            className="contributor-view-all"
          >
            View All <ArrowRight size={16} />
          </Link>
        </div>

        <div className="contributor-applications-table-wrapper">
          <table className="contributor-applications-table">
            <thead>
              <tr>
                <th>Opportunity</th>
                <th>Organization</th>
                <th>Status</th>
                <th>Applied Date</th>
              </tr>
            </thead>

            <tbody>
              {recent.map((application) => (
                <tr key={application.application_id}>
                  <td>{application.opportunity.title}</td>
                  <td>{application.opportunity.organization.name}</td>
                  <td>{application.opportunity.status === "cancelled" ? "Closed" : application.work_status === "completed" ? "Completed" : application.work_status === "awaiting_verification" ? "Work submitted" : STATUS_LABELS[application.status]}</td>
                  <td>{formatDate(application.submitted_at)}</td>
                </tr>
              ))}
              {recent.length === 0 && (
              <tr>
                <td colSpan={4} className="contributor-empty-applications">
                  <span className="contributor-empty-icon">
                    <ClipboardList size={25} />
                  </span>
                  <strong>Your recent applications will appear here</strong>
                  <span>
                    Browse opportunities and apply to start building your
                    experience.
                  </span>
                  <Link to="/opportunities">
                    Browse Opportunities <ArrowRight size={15} />
                  </Link>
                </td>
              </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
