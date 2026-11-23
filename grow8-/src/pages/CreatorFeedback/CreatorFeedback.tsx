import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquareText, RefreshCw, Star } from "lucide-react";

import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import FeedbackPanel from "../../components/FeedbackPanel/FeedbackPanel";
import { RatingBadge } from "../../components/Rating/Rating";
import { getMe } from "../../services/account";
import "./CreatorFeedback.css";

type Filter = "all" | "to_give";

/**
 * /creator/feedback (ADR 0015): for every application whose work was verified, the
 * feedback the creator gave the contributor and the feedback they received. Only
 * feedback an admin approved is published and counts toward ratings.
 */
export default function CreatorFeedback() {
  const { apiApplications, loading, error, refresh } = useCreatorWorkspace();
  const [myUserId, setMyUserId] = useState<number | null>(null);
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    let active = true;
    getMe()
      .then((me) => {
        if (active) setMyUserId(me.user_id);
      })
      .catch(() => {
        // The rest of the page works without the creator's own rating.
      });
    return () => {
      active = false;
    };
  }, []);

  const verified = useMemo(
    () =>
      apiApplications.filter(
        (item) => item.work_status === "completed" || item.work_status === "work_rejected"
      ),
    [apiApplications]
  );

  return (
    <section className="cfb-page">
      <header className="cfb-head">
        <div>
          <span className="cfb-eyebrow">CREATOR WORKSPACE</span>
          <h1>Feedback</h1>
          <p>
            Rate the contributors whose work you verified, and see what they said about you. An
            admin reviews every feedback before it's published.
          </p>
        </div>
        <button type="button" className="cfb-button" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={15} className={loading ? "cfb-spin" : ""} /> Refresh
        </button>
      </header>

      <div className="cfb-summary">
        <div>
          <Star size={20} />
          <span>Your public rating</span>
          {myUserId ? <RatingBadge userId={myUserId} /> : <span className="cfb-muted">—</span>}
        </div>
        <div>
          <MessageSquareText size={20} />
          <span>Verified applications</span>
          <strong>{verified.length}</strong>
        </div>
      </div>

      <div className="cfb-tabs" role="tablist" aria-label="Filter">
        <button
          type="button"
          role="tab"
          aria-selected={filter === "all"}
          className={filter === "all" ? "is-active" : ""}
          onClick={() => setFilter("all")}
        >
          All
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={filter === "to_give"}
          className={filter === "to_give" ? "is-active" : ""}
          onClick={() => setFilter("to_give")}
        >
          Approved work
        </button>
      </div>

      {error && (
        <p className="cfb-error" role="alert">
          {error}
        </p>
      )}
      {loading && <p className="cfb-muted">Loading...</p>}

      {!loading && verified.length === 0 && (
        <div className="cfb-empty">
          <MessageSquareText size={28} />
          <h2>No feedback yet</h2>
          <p>Feedback opens once you've verified a contributor's work.</p>
          <Link to="/creator/submissions" className="cfb-button">
            Review submissions
          </Link>
        </div>
      )}

      <div className="cfb-list">
        {verified
          .filter((item) => filter === "all" || item.work_status === "completed")
          .map((application) => (
            <article key={application.application_id} className="cfb-card">
              <div className="cfb-card-head">
                <div>
                  <h3>{application.applicant.full_name}</h3>
                  <p>
                    {application.opportunity.title} · <RatingBadge userId={application.applicant.user_id} />
                  </p>
                </div>
                <span className={`cfb-pill is-${application.work_status}`}>
                  {application.work_status === "completed" ? "Work approved" : "Work rejected"}
                </span>
              </div>
              <FeedbackPanel
                applicationId={application.application_id}
                subjectLabel={application.applicant.full_name}
                workVerified
              />
            </article>
          ))}
      </div>
    </section>
  );
}
