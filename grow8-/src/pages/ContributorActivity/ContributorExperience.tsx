import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Award, BadgeCheck, Briefcase, Clock3, RefreshCw } from "lucide-react";

import { getMyExperience } from "../../services/experience";
import type { Experience } from "../../services/experience";
import { formatHours } from "../../services/submissions";
import { errorMessage } from "../../services/formErrors";
import "./ContributorActivity.css";

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

/**
 * /contributor/experience: the verified record that GROW8 exists for (SDG 8.6):
 * hours an organization approved, the work behind them, and the skills it proved.
 * One call; the totals come from the v_contributor_verified_hours view.
 */
export default function ContributorExperience() {
  const [experience, setExperience] = useState<Experience | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getMyExperience()
      .then((result) => {
        if (active) setExperience(result);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "Your experience could not be loaded."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reload]);

  const work = experience?.completed_work ?? [];
  const skills = experience?.verified_skills ?? [];
  const completed = experience?.completed_opportunities ?? 0;
  const organizations = experience?.organizations ?? 0;
  const ready = !loading && experience !== null;

  return (
    <div className="act-page">
      <header className="act-header">
        <div>
          <span className="act-eyebrow">CONTRIBUTOR WORKSPACE</span>
          <h1>My Experience</h1>
          <p>Work that organizations verified. This is your record of real experience.</p>
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

      <section className="act-stats" aria-label="Summary">
        <div>
          <Clock3 size={20} />
          <strong>{ready ? formatHours(experience.verified_hours) : "—"}</strong>
          <span>verified hours</span>
        </div>
        <div>
          <Briefcase size={20} />
          <strong>{ready ? completed : "—"}</strong>
          <span>completed {completed === 1 ? "opportunity" : "opportunities"}</span>
        </div>
        <div>
          <Award size={20} />
          <strong>{ready ? organizations : "—"}</strong>
          <span>{organizations === 1 ? "organization" : "organizations"}</span>
        </div>
        <div>
          <BadgeCheck size={20} />
          <strong>{ready ? skills.length : "—"}</strong>
          <span>verified skills</span>
        </div>
      </section>

      <section className="act-card">
        <h2>Verified skills</h2>
        {ready && skills.length === 0 && (
          <p className="act-muted">Skills become verified when an organization approves your work.</p>
        )}
        <ul className="act-chips">
          {skills.map((skill) => (
            <li key={skill.code}>
              <BadgeCheck size={14} /> {skill.name}
              <small>since {formatDate(skill.verified_at)}</small>
            </li>
          ))}
        </ul>
      </section>

      <section className="act-card">
        <h2>Completed work</h2>
        {loading && <p className="act-muted">Loading...</p>}
        {ready && work.length === 0 && (
          <div className="act-empty">
            <p>No verified work yet. Once you're accepted, submit your work from My Applications.</p>
            <Link to="/contributor/applications" className="act-button">
              Go to My Applications
            </Link>
          </div>
        )}
        <ul className="act-list">
          {work.map((item) => (
            <li key={item.submission_id}>
              <div className="act-list-main">
                <strong>{item.opportunity.title}</strong>
                <span>{item.organization.name}</span>
                <p>{item.description}</p>
                {item.comment && <p className="act-quote">“{item.comment}”</p>}
              </div>
              <div className="act-list-side">
                <strong>{formatHours(item.verified_hours)} h</strong>
                <span>verified {formatDate(item.verified_at)}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
