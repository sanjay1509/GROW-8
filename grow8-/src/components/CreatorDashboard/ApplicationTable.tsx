import { Link } from "react-router-dom";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import type { Application } from "../../data/creatorDashboardData";
import Status from "./Status";

interface Props {
  applications: Application[];
  label: string;
}

export default function ApplicationTable({ applications, label }: Props) {
  const { opportunities, apiApplications, approvedSubmissions } = useCreatorWorkspace();

  return (
    <div className="creator-table-wrap">
      <table className="creator-table" aria-label={label}>
        <thead>
          <tr>
            <th scope="col">Applicant</th>
            <th scope="col">Opportunity</th>
            <th scope="col">Status</th>
            <th scope="col">Work</th>
            <th scope="col">Verified hours</th>
            <th scope="col">Applied Date</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {applications.map((application) => (
            (() => {
              const apiApplication = apiApplications.find((item) => item.application_id === application.id);
              const submission = approvedSubmissions.find((item) => item.application_id === application.id);
              const workStatus = submission ? "Completed" : apiApplication?.work_status === "awaiting_verification" ? "Under review" : apiApplication?.work_status === "work_rejected" ? "Rejected" : "—";
              return (
            <tr key={application.id}>
              <td>{application.name}</td>
              <td>{opportunities.find((opportunity) => opportunity.id === application.opportunityId)?.title}</td>
              <td><Status>{submission ? "Completed" : application.status}</Status></td>
              <td>{workStatus}</td>
              <td>{submission?.verification?.verified_hours != null ? `${Number(submission.verification.verified_hours)} h` : "—"}</td>
              <td className="creator-date">{application.appliedDate}</td>
              <td>
                <Link
                  className="creator-text-link"
                  to={`/creator/applications?opportunity=${application.opportunityId}`}
                  aria-label={`View ${application.name}’s application`}
                >
                  View
                </Link>
              </td>
            </tr>
              );
            })()
          ))}
        </tbody>
      </table>
    </div>
  );
}
