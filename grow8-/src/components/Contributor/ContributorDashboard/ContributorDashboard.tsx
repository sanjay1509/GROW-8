
import {
  ArrowRight,
  BriefcaseBusiness,
  Clock3,
  CheckCircle2,
  Timer,
  ClipboardList,
} from "lucide-react";
import { Link } from "react-router-dom";
import FeaturedOpportunities from "../../FeaturedOpportunities/FeaturedOpportunities";
import "./ContributorDashboard.css";

const stats = [
  {
    label: "Applied",
    value: "—",
    icon: ClipboardList,
    color: "blue",
  },
  {
    label: "In Progress",
    value: "—",
    icon: Clock3,
    color: "amber",
  },
  {
    label: "Completed",
    value: "—",
    icon: CheckCircle2,
    color: "green",
  },
  {
    label: "Verified Hours",
    value: "—",
    icon: Timer,
    color: "cyan",
  },
];

export default function ContributorDashboard() {
  const userName = localStorage.getItem("user_name") || "Contributor";

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
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
