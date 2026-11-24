import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Clock3, Flag, RefreshCw, XCircle } from "lucide-react";

import { getMyReports, reasonLabel } from "../../services/reports";
import type { OpportunityReport } from "../../services/reports";
import { errorMessage } from "../../services/formErrors";
import "./ContributorActivity.css";

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

function Outcome({ report }: { report: OpportunityReport }) {
  if (report.status === "pending") {
    return (
      <span className="act-pill is-pending">
        <Clock3 size={13} /> Waiting for an admin
      </span>
    );
  }
  if (report.status === "upheld") {
    return (
      <span className="act-pill is-upheld">
        <CheckCircle2 size={13} /> Taken down
      </span>
    );
  }
  return (
    <span className="act-pill is-dismissed">
      <XCircle size={13} /> Dismissed
    </span>
  );
}

/** /contributor/reports: the opportunities this contributor reported and what was decided. */
export default function ContributorReports() {
  const [reports, setReports] = useState<OpportunityReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getMyReports(100)
      .then((result) => {
        if (active) setReports(result.items);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "Your reports could not be loaded."));
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
          <h1>My Reports</h1>
          <p>
            Opportunities you reported as misleading or unsafe, and what an admin decided. The
            organization never sees who reported.
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

      {!loading && reports.length === 0 && !error && (
        <div className="act-card act-empty">
          <Flag size={22} />
          <p>
            You haven't reported anything. If an opportunity looks wrong, open its details and use
            "Report this opportunity".
          </p>
          <Link to="/opportunities" className="act-button">
            Browse opportunities
          </Link>
        </div>
      )}

      <div className="act-stack">
        {reports.map((report) => (
          <section key={report.report_id} className="act-card">
            <div className="act-card-title">
              <div>
                <h2>{report.opportunity.title}</h2>
                <span>
                  {reasonLabel(report.reason)} · reported {formatDate(report.created_at)}
                </span>
              </div>
              <Outcome report={report} />
            </div>
            {report.details && <p className="act-quote">Your details: “{report.details}”</p>}
            {report.review && (
              <p className="act-review">
                {report.status === "upheld"
                  ? "The opportunity was taken down"
                  : "The report was dismissed"}{" "}
                on {formatDate(report.review.reviewed_at)}
                {report.review.reason ? `. Admin's note: “${report.review.reason}”` : "."}
              </p>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
