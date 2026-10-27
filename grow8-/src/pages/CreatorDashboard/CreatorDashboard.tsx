
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
import {
  creatorProfile,
  summaryWork,
} from "../../data/creatorDashboardData";

export default function CreatorDashboard() {
  const { opportunities, applications } = useCreatorWorkspace();

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
      value: summaryWork.inProgress,
      icon: Clock3,
      color: "is-yellow",
    },
    {
      label: "Completed",
      value: summaryWork.completed,
      icon: CircleCheck,
      color: "is-green",
    },
  ];

  return (
    <>
      <CreatorPageHeading
        title={`Welcome, ${creatorProfile.name}!`}
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

      <div className="creator-stats" aria-label="Creator overview">
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

        <ApplicationTable
          applications={applications.slice(0, 4)}
          label="Recent applications"
        />
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

        <OpportunityGrid opportunities={opportunities.slice(0, 3)} />
      </section>
    </>
  );
}
