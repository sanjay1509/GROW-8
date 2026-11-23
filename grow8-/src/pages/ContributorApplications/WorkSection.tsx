import { useEffect, useState } from "react";
import { CheckCircle2, Clock3, Download, Paperclip, Send, XCircle } from "lucide-react";

import FeedbackPanel from "../../components/FeedbackPanel/FeedbackPanel";
import SubmitWorkDialog from "../../components/SubmitWorkDialog/SubmitWorkDialog";
import {
  WORK_MESSAGES,
  downloadAttachment,
  formatHours,
  getApplicationSubmission,
} from "../../services/submissions";
import type { Submission, WorkStatus } from "../../services/submissions";
import { errorMessage } from "../../services/formErrors";

type Props = {
  applicationId: number;
  opportunityTitle: string;
  opportunityStatus?: string;
  workStatus: WorkStatus;
  /** Called after work is submitted, so the list can refresh. */
  onChanged: () => void;
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

/**
 * The work part of an accepted application: submit work, see whether it's awaiting
 * verification, approved (with the verified hours) or rejected, then leave feedback.
 */
export default function WorkSection({
  applicationId,
  opportunityTitle,
  opportunityStatus,
  workStatus,
  onChanged,
}: Props) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    if (workStatus === "not_submitted") return;
    let active = true;
    getApplicationSubmission(applicationId)
      .then((result) => {
        if (active) setSubmission(result);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, "Your submitted work could not be loaded.", WORK_MESSAGES));
      });
    return () => {
      active = false;
    };
  }, [applicationId, workStatus]);

  async function handleDownload(attachmentIndex: number) {
    if (!submission) return;
    setError("");
    try {
      await downloadAttachment(submission.submission_id, submission.attachments[attachmentIndex]);
    } catch (err) {
      setError(errorMessage(err, "The file could not be downloaded.", WORK_MESSAGES));
    }
  }

  if (workStatus === "not_submitted") {
    if (opportunityStatus === "cancelled") {
      return (
        <div className="ca-work is-muted">
          This opportunity was cancelled, so work can't be submitted.
        </div>
      );
    }
    return (
      <div className="ca-work">
        <div>
          <strong>You're accepted. Submit your work when it's done.</strong>
          <p>The organization verifies it, and the approved hours and skills go on your profile.</p>
        </div>
        <button type="button" className="ca-submit-work-button" onClick={() => setDialogOpen(true)}>
          <Send size={15} /> Submit work
        </button>
        {dialogOpen && (
          <SubmitWorkDialog
            applicationId={applicationId}
            opportunityTitle={opportunityTitle}
            onClose={() => setDialogOpen(false)}
            onSubmitted={() => {
              setDialogOpen(false);
              onChanged();
            }}
          />
        )}
      </div>
    );
  }

  const verification = submission?.verification;

  return (
    <div className="ca-work-block">
      <div className={`ca-work is-${workStatus}`}>
        <div>
          {workStatus === "awaiting_verification" && (
            <strong>
              <Clock3 size={15} /> Work submitted, awaiting verification
            </strong>
          )}
          {workStatus === "completed" && (
            <strong>
              <CheckCircle2 size={15} /> Work approved
              {verification?.verified_hours && ` · ${formatHours(verification.verified_hours)} verified hours`}
            </strong>
          )}
          {workStatus === "work_rejected" && (
            <strong>
              <XCircle size={15} /> Work not approved
            </strong>
          )}

          {submission && (
            <p>
              Submitted {formatDate(submission.submitted_at)} · {formatHours(submission.hours_claimed)} hours claimed
            </p>
          )}
          {verification?.comment && (
            <p className="ca-work-comment">Organization's comment: “{verification.comment}”</p>
          )}
          {submission && submission.attachments.length > 0 && (
            <div className="ca-work-files">
              {submission.attachments.map((attachment, index) => (
                <button key={attachment.attachment_id} type="button" onClick={() => void handleDownload(index)}>
                  <Paperclip size={13} /> {attachment.file_name} <Download size={13} />
                </button>
              ))}
            </div>
          )}
          {error && <p className="ca-work-error">{error}</p>}
        </div>
      </div>

      <FeedbackPanel
        applicationId={applicationId}
        subjectLabel="the organization"
        workVerified={workStatus === "completed" || workStatus === "work_rejected"}
      />
    </div>
  );
}
