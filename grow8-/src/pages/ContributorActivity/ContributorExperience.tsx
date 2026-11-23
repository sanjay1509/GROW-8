import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Award, BadgeCheck, Briefcase, Clock3, RefreshCw } from "lucide-react";

import { getMyApplications } from "../../services/applications";
import type { Application } from "../../services/applications";
import { formatHours, getApplicationSubmission } from "../../services/submissions";
import type { Submission } from "../../services/submissions";
import { getMyProfile } from "../../services/profile";
import type { ProfileSkill } from "../../services/profile";
import { errorMessage } from "../../services/formErrors";
import "./ContributorActivity.css";

type CompletedWork = { application: Application; submission: Submission };

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
 */
export default function ContributorExperience() {
  const [work, setWork] = useState<CompletedWork[]>([]);
  const [skills, setSkills] = useState<ProfileSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [applications, profile] = await Promise.all([
          getMyApplications({ status: "accepted", limit: 100 }),
          getMyProfile(),
        ]);
        const completed = applications.items.filter((item) => item.work_status === "completed");
        const submissions = await Promise.all(
          completed.map((application) => getApplicationSubmission(application.application_id))
        );
        if (!active) return;
        setWork(
          completed
            .map((application, index) => ({ application, submission: submissions[index] }))
            .sort((a, b) =>
              (b.submission.verification?.verified_at ?? "").localeCompare(
                a.submission.verification?.verified_at ?? ""
              )
            )
        );
        setSkills(profile.skills.filter((skill) => skill.verified));
      } catch (err) {
        if (active) setError(errorMessage(err, "Your experience could not be loaded."));
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [reload]);

  const totalHours = work.reduce(
    (sum, item) => sum + Number(item.submission.verification?.verified_hours ?? 0),
    0
  );
  const organizations = new Set(work.map((item) => item.application.opportunity.organization.name));

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
          <strong>{loading ? "—" : formatHours(totalHours)}</strong>
          <span>verified hours</span>
        </div>
        <div>
          <Briefcase size={20} />
          <strong>{loading ? "—" : work.length}</strong>
          <span>completed {work.length === 1 ? "opportunity" : "opportunities"}</span>
        </div>
        <div>
          <Award size={20} />
          <strong>{loading ? "—" : organizations.size}</strong>
          <span>{organizations.size === 1 ? "organization" : "organizations"}</span>
        </div>
        <div>
          <BadgeCheck size={20} />
          <strong>{loading ? "—" : skills.length}</strong>
          <span>verified skills</span>
        </div>
      </section>

      <section className="act-card">
        <h2>Verified skills</h2>
        {!loading && skills.length === 0 && (
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
        {!loading && work.length === 0 && (
          <div className="act-empty">
            <p>No verified work yet. Once you're accepted, submit your work from My Applications.</p>
            <Link to="/contributor/applications" className="act-button">
              Go to My Applications
            </Link>
          </div>
        )}
        <ul className="act-list">
          {work.map(({ application, submission }) => (
            <li key={application.application_id}>
              <div className="act-list-main">
                <strong>{application.opportunity.title}</strong>
                <span>{application.opportunity.organization.name}</span>
                <p>{submission.description}</p>
                {submission.verification?.comment && (
                  <p className="act-quote">“{submission.verification.comment}”</p>
                )}
              </div>
              <div className="act-list-side">
                <strong>{formatHours(submission.verification?.verified_hours)} h</strong>
                <span>verified {formatDate(submission.verification?.verified_at)}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
