import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, MessageSquareText, RefreshCw, XCircle } from "lucide-react";

import { Stars } from "../../components/Rating/Rating";
import { ADMIN_MESSAGES, getFeedbackQueue, reviewFeedback } from "../../services/admin";
import type { Feedback, FeedbackStatus } from "../../services/feedback";
import { errorMessage } from "../../services/formErrors";
import "./AdminPages.css";

type Tab = FeedbackStatus | "all";

const TABS: { value: Tab; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "all", label: "All" },
];

const PAGE_SIZE = 20;

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

function FeedbackItem({ feedback, onDone }: { feedback: Feedback; onDone: (message: string) => void }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function decide(decision: "approved" | "rejected", event?: FormEvent) {
    event?.preventDefault();
    setError("");
    if (decision === "rejected" && !reason.trim()) {
      setError("Give a reason. The author will see it.");
      return;
    }
    if (reason.trim().length > 500) {
      setError("Keep the reason under 500 characters.");
      return;
    }
    setSaving(true);
    try {
      await reviewFeedback(feedback.feedback_id, decision, decision === "rejected" ? reason : undefined);
      onDone(
        decision === "approved"
          ? `Published ${feedback.author.full_name}'s feedback about ${feedback.subject.full_name}.`
          : `Rejected ${feedback.author.full_name}'s feedback. They'll see your reason.`
      );
    } catch (err) {
      const code = (err as { code?: string }).code;
      if (code === "FEEDBACK_ALREADY_REVIEWED") {
        onDone(ADMIN_MESSAGES.FEEDBACK_ALREADY_REVIEWED);
        return;
      }
      setError(errorMessage(err, "The decision could not be saved.", ADMIN_MESSAGES));
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className={`adm-card adm-fb ${feedback.reports_discrepancy ? "is-discrepancy" : ""}`}>
      <div className="adm-fb-head">
        <div>
          <h3>
            {feedback.author.full_name} → {feedback.subject.full_name}
          </h3>
          <p className="adm-muted">
            {feedback.opportunity.title} · {formatDate(feedback.created_at)}
          </p>
        </div>
        <div className="adm-fb-tags">
          {feedback.reports_discrepancy && (
            <span className="adm-pill is-flag">
              <AlertTriangle size={13} /> Discrepancy
            </span>
          )}
          <span className={`adm-pill is-${feedback.status}`}>{feedback.status}</span>
        </div>
      </div>

      <div className="adm-fb-body">
        <Stars value={feedback.rating} size={17} />
        <p>{feedback.comment ? `“${feedback.comment}”` : <em className="adm-muted">No comment.</em>}</p>
      </div>

      {feedback.review && (
        <p className="adm-muted">
          {feedback.review.decision === "approved" ? "Approved" : "Rejected"} {formatDate(feedback.review.reviewed_at)}
          {feedback.review.reason ? `: “${feedback.review.reason}”` : ""}
        </p>
      )}

      {feedback.status === "pending" &&
        (rejecting ? (
          <form className="adm-form" onSubmit={(event) => void decide("rejected", event)}>
            <label>
              <span>Why is it rejected? (required, the author sees it)</span>
              <textarea
                rows={2}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="e.g. The comment is abusive, or not about this work."
                disabled={saving}
              />
            </label>
            <div className="adm-actions">
              <button type="button" className="adm-button" onClick={() => setRejecting(false)} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="adm-button is-danger" disabled={saving}>
                {saving ? "Saving..." : "Reject feedback"}
              </button>
            </div>
          </form>
        ) : (
          <div className="adm-actions">
            <button type="button" className="adm-button is-danger-outline" onClick={() => setRejecting(true)} disabled={saving}>
              <XCircle size={15} /> Reject
            </button>
            <button type="button" className="adm-button is-approve" onClick={() => void decide("approved")} disabled={saving}>
              <CheckCircle2 size={15} /> {saving ? "Saving..." : "Approve and publish"}
            </button>
          </div>
        ))}

      {error && (
        <p className="adm-error" role="alert">
          {error}
        </p>
      )}
    </article>
  );
}

/** /admin/feedback: approve or reject feedback before it's published (ADR 0015). */
export default function AdminFeedback() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<Tab>("pending");
  const [discrepancyOnly, setDiscrepancyOnly] = useState(searchParams.get("discrepancy") === "1");
  const [items, setItems] = useState<Feedback[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await getFeedbackQueue({
        status: tab === "all" ? undefined : [tab],
        discrepancy: discrepancyOnly ? true : undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(errorMessage(err, "Feedback could not be loaded.", ADMIN_MESSAGES));
    } finally {
      setLoading(false);
    }
  }, [tab, discrepancyOnly, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="adm-page">
      <header className="adm-head">
        <div>
          <span className="adm-eyebrow">ADMIN</span>
          <h1>Feedback review</h1>
          <p>
            Only approved feedback is shown to the person rated and counts toward their public
            rating. Discrepancy reports are listed first.
          </p>
        </div>
        <button type="button" className="adm-button" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={15} className={loading ? "adm-spin" : ""} /> Refresh
        </button>
      </header>

      <div className="adm-tabs" role="tablist">
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
        <label>
          <input
            type="checkbox"
            checked={discrepancyOnly}
            onChange={(event) => {
              setDiscrepancyOnly(event.target.checked);
              setOffset(0);
            }}
          />
          Discrepancies only
        </label>
      </div>

      {notice && (
        <p className="adm-notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="adm-error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="adm-muted">Loading...</p>
      ) : items.length === 0 ? (
        <div className="adm-empty">
          <MessageSquareText size={28} />
          <h2>{tab === "pending" ? "All caught up" : "Nothing here"}</h2>
          <p>{tab === "pending" ? "There's no feedback waiting for review." : "Try another filter."}</p>
        </div>
      ) : (
        <div className="adm-list">
          {items.map((feedback) => (
            <FeedbackItem
              key={`${feedback.feedback_id}-${feedback.status}`}
              feedback={feedback}
              onDone={(message) => {
                setNotice(message);
                void load();
              }}
            />
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="adm-actions">
          <span className="adm-muted">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <button type="button" className="adm-button" onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))} disabled={offset === 0}>
            Previous
          </button>
          <button type="button" className="adm-button" onClick={() => setOffset((v) => v + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total}>
            Next
          </button>
        </div>
      )}
    </section>
  );
}
