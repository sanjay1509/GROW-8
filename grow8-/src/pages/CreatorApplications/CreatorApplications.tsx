import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Building2,
  Check,
  ChevronDown,
  ChevronUp,
  Download,
  GraduationCap,
  MapPin,
  RefreshCw,
  Search,
  X,
} from "lucide-react";

import CreatorPageHeading from "../../components/CreatorDashboard/CreatorPageHeading";
import { RatingBadge } from "../../components/Rating/Rating";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import {
  decideApplication,
  downloadApplicationResume,
} from "../../services/applications";
import type {
  Application as ApiApplication,
  ApplicationStatus as ApiApplicationStatus,
} from "../../services/applications";
import { formatDate, friendlyError } from "../../services/creatorWorkspace";
import "./CreatorApplications.css";

type Filter = "all" | ApiApplicationStatus;

const WORK_LABELS: Record<string, string> = {
  not_submitted: "Work not submitted yet",
  awaiting_verification: "Work submitted, waiting for your review",
  completed: "Work approved",
  work_rejected: "Work rejected",
};

const FILTERS: { value: Filter; label: string }[] = [
  { value: "pending", label: "To review" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
  { value: "all", label: "All" },
];

const STATUS_LABELS: Record<ApiApplicationStatus, string> = {
  pending: "Under review",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

/**
 * /creator/applications: every application to the creator's opportunities
 * (GET /applications/received), with accept/reject and the applicant's resume.
 * ?opportunity=<id> preselects one opportunity.
 */
export default function CreatorApplications() {
  const { apiApplications, apiOpportunities, loading, error, refresh } = useCreatorWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();

  const [filter, setFilter] = useState<Filter>("pending");
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirm, setConfirm] = useState<{ id: number; decision: "accepted" | "rejected" } | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const opportunityFilter = searchParams.get("opportunity") ?? "all";

  const counts = useMemo(() => {
    const scoped = apiApplications.filter(
      (a) => opportunityFilter === "all" || String(a.opportunity.opportunity_id) === opportunityFilter
    );
    const result: Record<Filter, number> = {
      all: scoped.length,
      pending: 0,
      accepted: 0,
      rejected: 0,
      withdrawn: 0,
    };
    scoped.forEach((a) => {
      result[a.status] += 1;
    });
    return result;
  }, [apiApplications, opportunityFilter]);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return apiApplications.filter((a) => {
      const matchesOpportunity =
        opportunityFilter === "all" || String(a.opportunity.opportunity_id) === opportunityFilter;
      const matchesStatus = filter === "all" || a.status === filter;
      const matchesSearch =
        !term ||
        `${a.applicant.full_name} ${a.applicant.headline ?? ""} ${a.applicant.institution ?? ""} ${a.opportunity.title} ${a.applicant.skills
          .map((s) => s.name)
          .join(" ")}`
          .toLowerCase()
          .includes(term);
      return matchesOpportunity && matchesStatus && matchesSearch;
    });
  }, [apiApplications, filter, search, opportunityFilter]);

  // Opportunities that can receive applications (everything except drafts).
  const opportunityOptions = apiOpportunities.filter((o) => o.status !== "draft");

  async function decide(application: ApiApplication, decision: "accepted" | "rejected") {
    setBusyId(application.application_id);
    setMessage(null);
    try {
      await decideApplication(application.application_id, decision);
      setMessage({
        kind: "ok",
        text: `${application.applicant.full_name} was ${decision === "accepted" ? "accepted" : "rejected"} for ${application.opportunity.title}. They have been notified.`,
      });
      setConfirm(null);
      await refresh();
    } catch (err) {
      setMessage({ kind: "error", text: friendlyError(err, "The decision could not be saved.") });
    } finally {
      setBusyId(null);
    }
  }

  async function handleResume(application: ApiApplication) {
    setMessage(null);
    try {
      await downloadApplicationResume(application.application_id);
    } catch (err) {
      setMessage({ kind: "error", text: friendlyError(err, "The resume could not be downloaded.") });
    }
  }

  return (
    <>
      <CreatorPageHeading
        title="Applications"
        description="Review who applied to your opportunities and choose your contributors."
      >
        <button
          type="button"
          className="creator-button"
          onClick={() => void refresh()}
          disabled={loading}
        >
          <RefreshCw size={17} /> Refresh
        </button>
      </CreatorPageHeading>

      <div className="capp-toolbar">
        <div className="capp-filters" role="tablist" aria-label="Filter by status">
          {FILTERS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={filter === value}
              className={`capp-filter${filter === value ? " is-active" : ""}`}
              onClick={() => setFilter(value)}
            >
              {label} <span>{counts[value]}</span>
            </button>
          ))}
        </div>

        <div className="capp-controls">
          <label className="capp-select">
            <span className="capp-visually-hidden">Opportunity</span>
            <select
              value={opportunityFilter}
              onChange={(event) => {
                const value = event.target.value;
                setSearchParams(value === "all" ? {} : { opportunity: value });
              }}
            >
              <option value="all">All opportunities</option>
              {opportunityOptions.map((o) => (
                <option key={o.opportunity_id} value={String(o.opportunity_id)}>
                  {o.title}
                  {o.status !== "open" ? ` (${o.status})` : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="capp-search">
            <Search size={16} />
            <input
              type="search"
              placeholder="Search applicants or skills"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>
      </div>

      {message && (
        <p className={`capp-message is-${message.kind}`} role={message.kind === "error" ? "alert" : "status"}>
          {message.text}
        </p>
      )}

      {error && (
        <p className="capp-message is-error" role="alert">
          {error}
        </p>
      )}

      {loading && apiApplications.length === 0 && <p className="creator-empty-note">Loading applications...</p>}

      {!loading && !error && visible.length === 0 && (
        <p className="creator-empty-note">
          {apiApplications.length === 0
            ? "No one has applied to your opportunities yet."
            : "No applications match these filters."}
        </p>
      )}

      {visible.length > 0 && (
        <ul className="capp-list">
          {visible.map((application) => {
            const { applicant, opportunity } = application;
            const expanded = expandedId === application.application_id;
            const busy = busyId === application.application_id;
            const cancelled = opportunity.status === "cancelled";
            const canDecide = application.status === "pending" && !cancelled;
            const confirming = confirm?.id === application.application_id ? confirm.decision : null;

            return (
              <li className="capp-card" key={application.application_id}>
                <div className="capp-card-main">
                  <span className="capp-avatar" aria-hidden="true">
                    {applicant.full_name
                      .split(/\s+/)
                      .slice(0, 2)
                      .map((p) => p[0])
                      .join("")
                      .toUpperCase()}
                  </span>

                  <div className="capp-who">
                    <strong>{applicant.full_name}</strong>
                    <RatingBadge userId={applicant.user_id} />
                    <span>{applicant.headline || "Contributor"}</span>
                    <span className="capp-meta">
                      {applicant.institution && (
                        <>
                          <GraduationCap size={13} /> {applicant.institution}
                        </>
                      )}
                      {applicant.city && (
                        <>
                          <MapPin size={13} /> {applicant.city}
                        </>
                      )}
                    </span>
                  </div>

                  <div className="capp-for">
                    <span className="capp-label">Applied for</span>
                    <span>
                      <Building2 size={13} /> {opportunity.title}
                    </span>
                    <span className="capp-label">{formatDate(application.submitted_at)}</span>
                  </div>

                  <span className={`capp-status is-${application.status}`}>
                    {STATUS_LABELS[application.status]}
                  </span>
                </div>

                {applicant.skills.length > 0 && (
                  <div className="capp-skills">
                    {applicant.skills.map((skill) => (
                      <span key={skill.code}>{skill.name}</span>
                    ))}
                  </div>
                )}

                {expanded && (
                  <div className="capp-details">
                    <h3>Why they applied</h3>
                    <p>{application.motivation || "No message was included."}</p>
                    {application.application_details && (
                      <div className="capp-applicant-details">
                        <h3>Application details</h3>
                        {Object.entries(application.application_details).map(([label, value]) => (
                          <p key={label}><strong>{label === "name" ? "Name" : label === "email" ? "Email" : label === "phone" ? "Phone" : label === "study" ? "Study" : label === "experience" ? "Experience" : "Achievements"}:</strong> {value || "—"}</p>
                        ))}
                      </div>
                    )}
                    {application.decided_at && (
                      <p className="capp-label">Decided {formatDate(application.decided_at)}</p>
                    )}
                  </div>
                )}

                {application.status === "accepted" && application.work_status !== "not_submitted" && (
                  <p className={`capp-work is-${application.work_status}`}>
                    {WORK_LABELS[application.work_status]}
                    {application.work_status === "awaiting_verification" && (
                      <>
                        {" · "}
                        <Link to={`/creator/submissions?opportunity=${opportunity.opportunity_id}`}>
                          Review it
                        </Link>
                      </>
                    )}
                  </p>
                )}

                {cancelled && (
                  <p className="capp-note">This opportunity was cancelled, so applications can't be decided.</p>
                )}

                <div className="capp-actions">
                  <button
                    type="button"
                    className="capp-link"
                    onClick={() => setExpandedId(expanded ? null : application.application_id)}
                    aria-expanded={expanded}
                  >
                    {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                    {expanded ? "Hide details" : "View details"}
                  </button>

                  {applicant.has_resume && (
                    <button type="button" className="capp-button" onClick={() => void handleResume(application)}>
                      <Download size={15} /> Resume
                    </button>
                  )}

                  {canDecide && !confirming && (
                    <>
                      <button
                        type="button"
                        className="capp-button is-reject"
                        onClick={() => setConfirm({ id: application.application_id, decision: "rejected" })}
                        disabled={busyId !== null}
                      >
                        <X size={15} /> Reject
                      </button>
                      <button
                        type="button"
                        className="capp-button is-accept"
                        onClick={() => setConfirm({ id: application.application_id, decision: "accepted" })}
                        disabled={busyId !== null}
                      >
                        <Check size={15} /> Accept
                      </button>
                    </>
                  )}

                  {canDecide && confirming && (
                    <span className="capp-confirm">
                      {confirming === "accepted" ? "Accept" : "Reject"} {applicant.full_name}? This can't be changed.
                      <button
                        type="button"
                        className={`capp-button ${confirming === "accepted" ? "is-accept" : "is-reject"}`}
                        onClick={() => void decide(application, confirming)}
                        disabled={busy}
                      >
                        {busy ? "Saving..." : `Yes, ${confirming === "accepted" ? "accept" : "reject"}`}
                      </button>
                      <button
                        type="button"
                        className="capp-link"
                        onClick={() => setConfirm(null)}
                        disabled={busy}
                      >
                        Cancel
                      </button>
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
