import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight, Flag, MessageSquareText, RefreshCw } from "lucide-react";

import { getFeedbackQueue, getReportQueue } from "../../services/admin";
import { errorMessage } from "../../services/formErrors";
import "./AdminPages.css";

type Counts = { feedback: number; discrepancies: number; reports: number };

/** /admin: what's waiting for review. */
export default function AdminDashboard() {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const name = localStorage.getItem("user_name") || "Admin";

  useEffect(() => {
    let active = true;
    setError("");
    // limit=1: only the totals are needed.
    Promise.all([
      getFeedbackQueue({ status: ["pending"], limit: 1 }),
      getFeedbackQueue({ status: ["pending"], discrepancy: true, limit: 1 }),
      getReportQueue({ status: ["pending"], limit: 1 }),
    ])
      .then(([feedback, discrepancies, reports]) => {
        if (active) {
          setCounts({
            feedback: feedback.total,
            discrepancies: discrepancies.total,
            reports: reports.total,
          });
        }
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "The review queues could not be loaded."));
      });
    return () => {
      active = false;
    };
  }, [reload]);

  return (
    <section className="adm-page">
      <header className="adm-head">
        <div>
          <span className="adm-eyebrow">ADMIN</span>
          <h1>Welcome, {name.split(" ")[0]}</h1>
          <p>
            Feedback is only published after you approve it, and reported opportunities stay up
            until you decide.
          </p>
        </div>
        <button type="button" className="adm-button" onClick={() => setReload((n) => n + 1)}>
          <RefreshCw size={15} /> Refresh
        </button>
      </header>

      {error && (
        <p className="adm-error" role="alert">
          {error}
        </p>
      )}

      <div className="adm-stat-grid">
        <Link to="/admin/feedback" className="adm-stat">
          <MessageSquareText size={22} />
          <strong>{counts ? counts.feedback : "—"}</strong>
          <span>feedback waiting for review</span>
          <em>
            Review feedback <ArrowRight size={14} />
          </em>
        </Link>
        <Link to="/admin/feedback?discrepancy=1" className="adm-stat is-warn">
          <AlertTriangle size={22} />
          <strong>{counts ? counts.discrepancies : "—"}</strong>
          <span>of them report a discrepancy</span>
          <em>
            See discrepancies first <ArrowRight size={14} />
          </em>
        </Link>
        <Link to="/admin/reports" className="adm-stat is-danger">
          <Flag size={22} />
          <strong>{counts ? counts.reports : "—"}</strong>
          <span>reported opportunities waiting</span>
          <em>
            Review reports <ArrowRight size={14} />
          </em>
        </Link>
      </div>

      <div className="adm-card">
        <h2>How reviews work</h2>
        <ul className="adm-howto">
          <li>
            <strong>Feedback:</strong> approve it to publish it and count it in the person's public
            rating, or reject it with a reason. Discrepancy reports come first.
          </li>
          <li>
            <strong>Reports:</strong> dismiss a report, or take the opportunity down. Taking it down
            cancels it, tells its applicants, tells the organization your reason, and closes every
            other open report on it.
          </li>
          <li>Each decision is final, and the people involved are notified.</li>
        </ul>
      </div>
    </section>
  );
}
