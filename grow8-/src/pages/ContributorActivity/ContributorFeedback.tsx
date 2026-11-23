import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";

import FeedbackPanel from "../../components/FeedbackPanel/FeedbackPanel";
import { getMyApplications } from "../../services/applications";
import type { Application } from "../../services/applications";
import { errorMessage } from "../../services/formErrors";
import "./ContributorActivity.css";

/**
 * /contributor/feedback: every application whose work was verified, with the feedback
 * the contributor gave the organization and the feedback they received (ADR 0015).
 */
export default function ContributorFeedback() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getMyApplications({ status: "accepted", limit: 100 })
      .then((result) => {
        if (!active) return;
        setApplications(
          result.items.filter(
            (item) => item.work_status === "completed" || item.work_status === "work_rejected"
          )
        );
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "Your feedback could not be loaded."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reload]);

  return (
    <div className="act-page">
      <header className="act-header">
        <div>
          <span className="act-eyebrow">CONTRIBUTOR WORKSPACE</span>
          <h1>Feedback</h1>
          <p>
            Rate the organizations you worked with, and see what they said about you. An admin
            reviews every feedback before it's published.
          </p>
        </div>
        <button type="button" className="act-button" onClick={() => setReload((n) => n + 1)} disabled={loading}>
          <RefreshCw size={15} className={loading ? "act-spin" : ""} /> Refresh
        </button>
      </header>

      {error && (
        <p className="act-error" role="alert">
          {error}
        </p>
      )}
      {loading && <p className="act-muted">Loading...</p>}

      {!loading && applications.length === 0 && !error && (
        <div className="act-card act-empty">
          <p>Feedback opens once an organization has verified your work.</p>
          <Link to="/contributor/applications" className="act-button">
            Go to My Applications
          </Link>
        </div>
      )}

      <div className="act-stack">
        {applications.map((application) => (
          <section key={application.application_id} className="act-card">
            <div className="act-card-title">
              <div>
                <h2>{application.opportunity.title}</h2>
                <span>{application.opportunity.organization.name}</span>
              </div>
              <span className={`act-pill is-${application.work_status}`}>
                {application.work_status === "completed" ? "Work approved" : "Work not approved"}
              </span>
            </div>
            <FeedbackPanel
              applicationId={application.application_id}
              subjectLabel={application.opportunity.organization.name}
              workVerified
            />
          </section>
        ))}
      </div>
    </div>
  );
}
