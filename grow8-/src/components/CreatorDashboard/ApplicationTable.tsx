import { Link } from "react-router-dom";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import type { Application } from "../../data/creatorDashboardData";
import Status from "./Status";

interface Props {
  applications: Application[];
  label: string;
}

export default function ApplicationTable({ applications, label }: Props) {
  const { opportunities } = useCreatorWorkspace();

  return (
    <div className="creator-table-wrap">
      <table className="creator-table" aria-label={label}>
        <thead>
          <tr>
            <th scope="col">Applicant</th>
            <th scope="col">Opportunity</th>
            <th scope="col">Status</th>
            <th scope="col">Applied Date</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {applications.map((application) => (
            <tr key={application.id}>
              <td>{application.name}</td>
              <td>{opportunities.find((opportunity) => opportunity.id === application.opportunityId)?.title}</td>
              <td><Status>{application.status}</Status></td>
              <td className="creator-date">{application.appliedDate}</td>
              <td>
                {/* TODO: Open this application’s details when the Applications page is implemented. */}
                <Link
                  className="creator-text-link"
                  to="/creator/applications"
                  aria-label={`View ${application.name}’s application`}
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
