import { Link } from "react-router-dom";
import { BriefcaseBusiness, Building2, Palette } from "lucide-react";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import type { Opportunity } from "../../data/creatorDashboardData";
import Status from "./Status";

export default function OpportunityGrid({ opportunities }: { opportunities: Opportunity[] }) {
  const { applications } = useCreatorWorkspace();

  return (
    <div className="creator-opportunity-grid">
      {opportunities.map((opportunity) => {
        const Icon = opportunity.category === "community"
          ? Building2
          : opportunity.category === "creative" ? Palette : BriefcaseBusiness;

        return (
          <Link
            className="creator-opportunity-card"
            key={opportunity.id}
            to="/creator/opportunities"
            aria-label={`View ${opportunity.title}`}
          >
            <span className={`creator-icon-tile ${opportunity.category === "community" ? "is-coral" : "is-green"}`}>
              <Icon size={27} strokeWidth={1.9} />
            </span>
            <span className="creator-opportunity-content">
              <span className="creator-opportunity-title">{opportunity.title}</span>
              <span className="creator-opportunity-applications">
                {applications.filter((application) => application.opportunityId === opportunity.id).length} Applications
              </span>
              <Status>{opportunity.status}</Status>
            </span>
          </Link>
        );
      })}
    </div>
  );
}
