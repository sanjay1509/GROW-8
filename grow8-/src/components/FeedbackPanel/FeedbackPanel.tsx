import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { AlertTriangle, CheckCircle2, Clock3, MessageSquareText, XCircle } from "lucide-react";

import { StarInput, Stars } from "../Rating/Rating";
import {
  FEEDBACK_MESSAGES,
  getApplicationFeedback,
  leaveFeedback,
} from "../../services/feedback";
import type { ApplicationFeedback, Feedback } from "../../services/feedback";
import { errorMessage, fieldErrorsFrom } from "../../services/formErrors";
import "./FeedbackPanel.css";

const COMMENT_LIMIT = 2000;

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

function StatusLine({ feedback }: { feedback: Feedback }) {
  if (feedback.status === "pending") {
    return (
      <span className="fb-status is-pending">
        <Clock3 size={13} /> Pending review: an admin checks every feedback before it's published.
      </span>
    );
  }
  if (feedback.status === "approved") {
    return (
      <span className="fb-status is-approved">
        <CheckCircle2 size={13} /> Published {feedback.review ? formatDate(feedback.review.reviewed_at) : ""}
      </span>
    );
  }
  return (
    <span className="fb-status is-rejected">
      <XCircle size={13} /> Not published
      {feedback.review?.reason ? `: ${feedback.review.reason}` : ""}
    </span>
  );
}

function FeedbackView({ feedback, title }: { feedback: Feedback; title: string }) {
  return (
    <div className="fb-item">
      <div className="fb-item-head">
        <strong>{title}</strong>
        <Stars value={feedback.rating} />
      </div>
      {feedback.comment && <p className="fb-comment">“{feedback.comment}”</p>}
      {feedback.reports_discrepancy && (
        <span className="fb-flag">
          <AlertTriangle size={13} /> Reported a discrepancy
        </span>
      )}
      <span className="fb-meta">
        {feedback.author.full_name} · {formatDate(feedback.created_at)}
      </span>
    </div>
  );
}

type Props = {
  applicationId: number;
  /** Who the feedback is about, e.g. "the organization" or "Alex Chen". */
  subjectLabel: string;
  /** Feedback opens once the work is verified (approved or rejected). */
  workVerified: boolean;
};

/**
 * Feedback on one application (ADR 0015), for either side: the feedback you gave with
 * its review status, the feedback you received once an admin approved it, and the form.
 */
export default function FeedbackPanel({ applicationId, subjectLabel, workVerified }: Props) {
  const [data, setData] = useState<ApplicationFeedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [discrepancy, setDiscrepancy] = useState(false);
  const [formError, setFormError] = useState("");
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await getApplicationFeedback(applicationId));
    } catch (err) {
      setError(errorMessage(err, "Feedback could not be loaded.", FEEDBACK_MESSAGES));
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    if (workVerified) {
      void load();
    } else {
      setLoading(false);
    }
  }, [load, workVerified]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError("");
    if (rating < 1) {
      setFormError("Choose a rating from 1 to 5 stars.");
      return;
    }
    if (comment.trim().length > COMMENT_LIMIT) {
      setFormError(`Keep the comment under ${COMMENT_LIMIT} characters.`);
      return;
    }

    setSending(true);
    try {
      const given = await leaveFeedback(applicationId, {
        rating,
        ...(comment.trim() ? { comment: comment.trim() } : {}),
        reports_discrepancy: discrepancy,
      });
      setData((current) => ({ given, received: current?.received ?? null }));
    } catch (err) {
      const fields = fieldErrorsFrom(err);
      setFormError(
        fields.comment || fields.rating || errorMessage(err, "Your feedback could not be sent.", FEEDBACK_MESSAGES)
      );
      if ((err as { code?: string }).code === "FEEDBACK_ALREADY_SUBMITTED") {
        void load();
      }
    } finally {
      setSending(false);
    }
  }

  if (!workVerified) {
    return (
      <div className="fb-panel is-locked">
        <MessageSquareText size={16} />
        <span>Feedback opens once the work has been verified.</span>
      </div>
    );
  }

  return (
    <div className="fb-panel">
      <h4>
        <MessageSquareText size={16} /> Feedback
      </h4>

      {loading && <p className="fb-muted">Loading feedback...</p>}
      {error && (
        <p className="fb-error" role="alert">
          {error}{" "}
          <button type="button" className="fb-link" onClick={() => void load()}>
            Try again
          </button>
        </p>
      )}

      {!loading && data && (
        <div className="fb-columns">
          <div>
            {data.given ? (
              <>
                <FeedbackView feedback={data.given} title={`Your feedback for ${subjectLabel}`} />
                <StatusLine feedback={data.given} />
              </>
            ) : (
              <form className="fb-form" onSubmit={(event) => void handleSubmit(event)}>
                <strong>Rate {subjectLabel}</strong>
                <StarInput value={rating} onChange={setRating} disabled={sending} />
                <label>
                  <span>Comment (optional)</span>
                  <textarea
                    rows={3}
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="What went well, and what could be better?"
                    disabled={sending}
                  />
                  <small className={comment.length > COMMENT_LIMIT ? "is-over" : ""}>
                    {comment.length} / {COMMENT_LIMIT}
                  </small>
                </label>
                <label className="fb-check">
                  <input
                    type="checkbox"
                    checked={discrepancy}
                    onChange={(event) => setDiscrepancy(event.target.checked)}
                    disabled={sending}
                  />
                  <span>
                    Report a discrepancy: what happened didn't match the posting (for example
                    hours, pay or duties). An admin looks at these first.
                  </span>
                </label>
                <p className="fb-muted">
                  Feedback can't be changed once sent. It's published after an admin reviews it.
                </p>
                {formError && (
                  <p className="fb-error" role="alert">
                    {formError}
                  </p>
                )}
                <button type="submit" className="fb-submit" disabled={sending}>
                  {sending ? "Sending..." : "Send feedback"}
                </button>
              </form>
            )}
          </div>

          <div>
            {data.received ? (
              <FeedbackView feedback={data.received} title="Feedback you received" />
            ) : (
              <p className="fb-muted fb-received-empty">
                Feedback about you appears here once an admin has approved it.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
