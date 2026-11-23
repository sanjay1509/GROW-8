import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Download,
  Paperclip,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import { RatingBadge } from "../../components/Rating/Rating";
import {
  WORK_MESSAGES,
  downloadAttachment,
  formatHours,
  getReceivedSubmissions,
  isValidHours,
  verifySubmission,
} from "../../services/submissions";
import type { Submission, SubmissionStatus } from "../../services/submissions";
import { formatFileSize } from "../../services/resume";
import { errorMessage } from "../../services/formErrors";
import "./CreatorSubmissions.css";

type Tab = SubmissionStatus | "all";

const TABS: { value: Tab; label: string }[] = [
  { value: "awaiting", label: "Awaiting review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "all", label: "All" },
];

const PAGE_SIZE = 20;

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

type ReviewMode = "approve" | "reject" | null;

/** One submission with its attachments and the approve / reject form. */
function SubmissionCard({
  submission,
  onReviewed,
}: {
  submission: Submission;
  onReviewed: (updated: Submission) => void;
}) {
  const [mode, setMode] = useState<ReviewMode>(null);
  const [hours, setHours] = useState(formatHours(submission.hours_claimed));
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const verification = submission.verification;
  const cancelled = submission.opportunity.status === "cancelled";

  async function handleDownload(index: number) {
    setError("");
    try {
      await downloadAttachment(submission.submission_id, submission.attachments[index]);
    } catch (err) {
      setError(errorMessage(err, "The file could not be downloaded.", WORK_MESSAGES));
    }
  }

  async function handleReview(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (mode === "approve") {
      if (!isValidHours(hours)) {
        setError("Enter the verified hours, e.g. 6 or 6.5 (up to 2 decimals).");
        return;
      }
      if (Number(hours) > Number(submission.hours_claimed)) {
        setError(`Verified hours can't be more than the ${formatHours(submission.hours_claimed)} hours claimed.`);
        return;
      }
    }
    if (mode === "reject" && !comment.trim()) {
      setError("Explain why the work is rejected. The contributor will see it.");
      return;
    }
    if (comment.trim().length > 2000) {
      setError("Keep the comment under 2000 characters.");
      return;
    }

    setSaving(true);
    try {
      const updated = await verifySubmission(
        submission.submission_id,
        mode === "approve"
          ? { decision: "approved", verified_hours: hours.trim(), ...(comment.trim() ? { comment: comment.trim() } : {}) }
          : { decision: "rejected", comment: comment.trim() }
      );
      setMode(null);
      onReviewed(updated);
    } catch (err) {
      setError(errorMessage(err, "The decision could not be saved.", WORK_MESSAGES));
      if ((err as { code?: string }).code === "SUBMISSION_ALREADY_VERIFIED") {
        onReviewed(submission);
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className={`cs-sub-card is-${submission.status}`}>
      <header className="cs-sub-head">
        <div>
          <h3>{submission.opportunity.title}</h3>
          <p>
            <strong>{submission.applicant.full_name}</strong>{" "}
            <RatingBadge userId={submission.applicant.user_id} compact />
            <span> · submitted {formatDate(submission.submitted_at)}</span>
          </p>
        </div>
        <span className={`cs-sub-status is-${submission.status}`}>
          {submission.status === "awaiting" && (
            <>
              <Clock3 size={13} /> Awaiting review
            </>
          )}
          {submission.status === "approved" && (
            <>
              <CheckCircle2 size={13} /> Approved
            </>
          )}
          {submission.status === "rejected" && (
            <>
              <XCircle size={13} /> Rejected
            </>
          )}
        </span>
      </header>

      <div className="cs-sub-body">
        <p className="cs-sub-description">{submission.description}</p>
        <dl className="cs-sub-facts">
          <div>
            <dt>Hours claimed</dt>
            <dd>{formatHours(submission.hours_claimed)}</dd>
          </div>
          {verification?.decision === "approved" && (
            <div>
              <dt>Hours verified</dt>
              <dd>{formatHours(verification.verified_hours)}</dd>
            </div>
          )}
          {verification && (
            <div>
              <dt>Reviewed</dt>
              <dd>{formatDate(verification.verified_at)}</dd>
            </div>
          )}
        </dl>

        {submission.attachments.length > 0 ? (
          <ul className="cs-sub-files">
            {submission.attachments.map((attachment, index) => (
              <li key={attachment.attachment_id}>
                <button type="button" onClick={() => void handleDownload(index)}>
                  <Paperclip size={14} />
                  <span>{attachment.file_name}</span>
                  <small>{formatFileSize(attachment.size_bytes)}</small>
                  <Download size={14} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="cs-sub-muted">No files attached.</p>
        )}

        {verification?.comment && <p className="cs-sub-comment">Your comment: “{verification.comment}”</p>}
      </div>

      {submission.status === "awaiting" && (
        <footer className="cs-sub-actions">
          {cancelled ? (
            <p className="cs-sub-muted">This opportunity was cancelled, so the work can't be verified.</p>
          ) : mode === null ? (
            <>
              <button type="button" className="cs-sub-button is-approve" onClick={() => setMode("approve")}>
                <CheckCircle2 size={15} /> Approve
              </button>
              <button type="button" className="cs-sub-button is-reject" onClick={() => setMode("reject")}>
                <XCircle size={15} /> Reject
              </button>
            </>
          ) : (
            <form className="cs-sub-form" onSubmit={(event) => void handleReview(event)}>
              {mode === "approve" && (
                <label className="cs-sub-hours">
                  <span>Verified hours</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={hours}
                    onChange={(event) => setHours(event.target.value)}
                    disabled={saving}
                  />
                  <small>Up to {formatHours(submission.hours_claimed)} (the hours claimed).</small>
                </label>
              )}
              <label>
                <span>{mode === "approve" ? "Comment (optional)" : "Why is it rejected? (required)"}</span>
                <textarea
                  rows={3}
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder={
                    mode === "approve"
                      ? "Thank them, or explain fewer hours."
                      : "Explain what's missing, so the contributor understands."
                  }
                  disabled={saving}
                />
              </label>
              <p className="cs-sub-muted">
                This decision is final. Approved hours and the opportunity's skills go on the
                contributor's verified record.
              </p>
              <div className="cs-sub-form-actions">
                <button type="button" className="cs-sub-button" onClick={() => setMode(null)} disabled={saving}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`cs-sub-button ${mode === "approve" ? "is-approve-solid" : "is-reject-solid"}`}
                  disabled={saving}
                >
                  {saving ? "Saving..." : mode === "approve" ? "Approve work" : "Reject work"}
                </button>
              </div>
            </form>
          )}
        </footer>
      )}

      {error && (
        <p className="cs-sub-error" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}

/**
 * /creator/submissions: the review queue (ADR 0013). The creator downloads the files,
 * then approves the work with verified hours or rejects it with a comment.
 */
export default function CreatorSubmissions() {
  const { apiOpportunities, refresh } = useCreatorWorkspace();
  const [searchParams, setSearchParams] = useSearchParams();
  const opportunityParam = Number(searchParams.get("opportunity")) || undefined;

  const [tab, setTab] = useState<Tab>("awaiting");
  const [items, setItems] = useState<Submission[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await getReceivedSubmissions({
        status: tab === "all" ? undefined : tab,
        opportunity_id: opportunityParam,
        limit: PAGE_SIZE,
        offset,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(errorMessage(err, "Submissions could not be loaded.", WORK_MESSAGES));
    } finally {
      setLoading(false);
    }
  }, [tab, opportunityParam, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  function handleReviewed(updated: Submission) {
    if (updated.verification) {
      setNotice(
        updated.verification.decision === "approved"
          ? `Approved ${formatHours(updated.verification.verified_hours)} hours for ${updated.applicant.full_name}. They've been notified.`
          : `Rejected the work from ${updated.applicant.full_name}. They've been notified.`
      );
    }
    void load();
    void refresh();
  }

  function chooseOpportunity(value: string) {
    setOffset(0);
    const next = new URLSearchParams(searchParams);
    if (value) next.set("opportunity", value);
    else next.delete("opportunity");
    setSearchParams(next, { replace: true });
  }

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <section className="cs-sub-page">
      <header className="cs-sub-page-head">
        <div>
          <span className="cs-sub-eyebrow">CREATOR WORKSPACE</span>
          <h1>Submissions</h1>
          <p>Review the work contributors sent. Approved hours become their verified experience.</p>
        </div>
        <button type="button" className="cs-sub-button" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={15} className={loading ? "cs-sub-spin" : ""} /> Refresh
        </button>
      </header>

      <div className="cs-sub-filters">
        <div className="cs-sub-tabs" role="tablist" aria-label="Submission status">
          {TABS.map((item) => (
            <button
              key={item.value}
              type="button"
              role="tab"
              aria-selected={tab === item.value}
              className={tab === item.value ? "is-active" : ""}
              onClick={() => {
                setTab(item.value);
                setOffset(0);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
        <select
          aria-label="Filter by opportunity"
          value={opportunityParam ?? ""}
          onChange={(event) => chooseOpportunity(event.target.value)}
        >
          <option value="">All opportunities</option>
          {apiOpportunities
            .filter((item) => item.status !== "draft")
            .map((item) => (
              <option key={item.opportunity_id} value={item.opportunity_id}>
                {item.title}
              </option>
            ))}
        </select>
      </div>

      {notice && (
        <p className="cs-sub-notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="cs-sub-error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="cs-sub-muted">Loading submissions...</p>
      ) : items.length === 0 ? (
        <div className="cs-sub-empty">
          <ClipboardCheck size={28} />
          <h2>{tab === "awaiting" ? "Nothing to review" : "No submissions here"}</h2>
          <p>
            {tab === "awaiting"
              ? "When an accepted contributor submits their work, it appears here."
              : "Try another filter."}
          </p>
        </div>
      ) : (
        <div className="cs-sub-list">
          {items.map((submission) => (
            <SubmissionCard
              key={`${submission.submission_id}-${submission.status}`}
              submission={submission}
              onReviewed={handleReviewed}
            />
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="cs-sub-pages">
          <span>
            Page {page} of {pages}
          </span>
          <button type="button" className="cs-sub-button" onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))} disabled={offset === 0}>
            Previous
          </button>
          <button
            type="button"
            className="cs-sub-button"
            onClick={() => setOffset((v) => v + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}
