
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BriefcaseBusiness,
  CircleCheck,
  ClipboardList,
  Clock3,
  Plus,
} from "lucide-react";

import ApplicationTable from "../../components/CreatorDashboard/ApplicationTable";
import CreatorPageHeading from "../../components/CreatorDashboard/CreatorPageHeading";
import OpportunityGrid from "../../components/CreatorDashboard/OpportunityGrid";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";

export default function CreatorDashboard() {
  const { opportunities, applications, creatorName, loading, error, refresh } =
    useCreatorWorkspace();
  const { apiApplications } = useCreatorWorkspace();

  // In progress: contributors accepted for an opportunity that is still running.
  const inProgress = apiApplications.filter(
    (application) =>
      application.status === "accepted" &&
      application.work_status !== "completed" &&
      opportunities.find((opportunity) => opportunity.id === application.opportunity.opportunity_id)
        ?.status === "Open"
  ).length;
  const completed = apiApplications.filter((application) => application.work_status === "completed").length;

  const stats = [
    {
      label: "Total Opportunities",
      value: opportunities.length,
      icon: BriefcaseBusiness,
      color: "is-blue",
    },
    {
      label: "Total Applications",
      value: applications.length,
      icon: ClipboardList,
      color: "is-yellow",
    },
    {
      label: "In Progress",
      value: inProgress,
      icon: Clock3,
      color: "is-yellow",
    },
    {
      label: "Completed",
      value: completed,
      icon: CircleCheck,
      color: "is-green",
    },
  ];

  return (
    <>
      <CreatorPageHeading
        title={`Welcome, ${creatorName}!`}
        description="Manage your opportunities and find great contributors."
      >
        <Link
          className="creator-button is-primary"
          to="/creator/opportunities/create"
        >
          <Plus size={19} />
          Create Opportunity
        </Link>
      </CreatorPageHeading>

      {error && (
        <p className="creator-load-error" role="alert">
          {error}{" "}
          <button type="button" onClick={() => void refresh()}>
            Try again
          </button>
        </p>
      )}

      <div className="creator-stats" aria-label="Creator overview" aria-busy={loading}>
        {stats.map(({ label, value, icon: Icon, color }) => (
          <article className="creator-stat-card" key={label}>
            <span className={`creator-icon-tile ${color}`}>
              <Icon size={23} strokeWidth={2.2} />
            </span>
            <div>
              <p className="creator-stat-value">{value}</p>
              <p className="creator-stat-label">{label}</p>
            </div>
          </article>
        ))}
      </div>

      <section
        className="creator-section"
        aria-labelledby="creator-recent-title"
      >
        <div className="creator-section-heading">
          <h2 id="creator-recent-title">Recent Applications</h2>
        </div>

        {applications.length > 0 ? (
          <ApplicationTable
            applications={applications.slice(0, 4)}
            label="Recent applications"
          />
        ) : (
          <p className="creator-empty-note">
            {loading ? "Loading applications..." : "No applications yet."}
          </p>
        )}
      </section>

      <section
        className="creator-section"
        aria-labelledby="creator-opportunities-title"
      >
        <div className="creator-section-heading">
          <h2 id="creator-opportunities-title">My Opportunities</h2>

          <Link className="creator-text-link" to="/creator/opportunities">
            View All <ArrowRight size={15} />
          </Link>
        </div>

        {opportunities.length > 0 ? (
          <OpportunityGrid opportunities={opportunities.slice(0, 3)} />
        ) : (
          <p className="creator-empty-note">
            {loading ? "Loading opportunities..." : "You haven't created any opportunities yet."}
          </p>
        )}
      </section>
    </>
  );
}
