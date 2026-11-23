import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Flag, ShieldCheck } from "lucide-react";

import { REPORT_MESSAGES, REPORT_REASONS, reportOpportunity } from "../../services/reports";
import type { ReportReason } from "../../services/reports";
import { errorMessage } from "../../services/formErrors";
import "./ReportOpportunity.css";

const DETAILS_LIMIT = 2000;

type Props = {
  opportunityId: number;
  alreadyReported: boolean;
  onReported: (opportunityId: number) => void;
};

/**
 * "Report this opportunity" for signed-in contributors (ADR 0016). One report per
 * opportunity, ever. The organization never sees who reported.
 */
export default function ReportOpportunity({ opportunityId, alreadyReported, onReported }: Props) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason | "">("");
  const [details, setDetails] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);

  if (alreadyReported || done) {
    return (
      <div className="ro-reported" role="status">
        <ShieldCheck size={16} />
        <span>
          You reported this opportunity. You can follow what happens in{" "}
          <Link to="/contributor/reports">My reports</Link>.
        </span>
      </div>
    );
  }

  if (!open) {
    return (
      <button type="button" className="ro-open" onClick={() => setOpen(true)}>
        <Flag size={14} /> Report this opportunity
      </button>
    );
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!reason) {
      setError("Choose what's wrong with this opportunity.");
      return;
    }
    if (details.trim().length > DETAILS_LIMIT) {
      setError(`Keep the details under ${DETAILS_LIMIT} characters.`);
      return;
    }

    setSending(true);
    try {
      await reportOpportunity(opportunityId, reason, details);
      setDone(true);
      onReported(opportunityId);
    } catch (err) {
      if ((err as { code?: string }).code === "OPPORTUNITY_ALREADY_REPORTED") {
        setDone(true);
        onReported(opportunityId);
        return;
      }
      setError(errorMessage(err, "Your report could not be sent.", REPORT_MESSAGES));
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="ro-form" onSubmit={(event) => void handleSubmit(event)}>
      <h3>
        <Flag size={15} /> Report this opportunity
      </h3>
      <p className="ro-note">
        An admin will review your report. The organization won't see who reported it.
      </p>

      <fieldset>
        <legend>What's wrong?</legend>
        {REPORT_REASONS.map((item) => (
          <label key={item.value} className={reason === item.value ? "is-selected" : ""}>
            <input
              type="radio"
              name={`report-reason-${opportunityId}`}
              value={item.value}
              checked={reason === item.value}
              onChange={() => {
                setReason(item.value);
                setError("");
              }}
              disabled={sending}
            />
            <span>
              <strong>{item.label}</strong>
              <small>{item.hint}</small>
            </span>
          </label>
        ))}
      </fieldset>

      <label className="ro-details">
        <span>Details (optional)</span>
        <textarea
          rows={3}
          value={details}
          onChange={(event) => setDetails(event.target.value)}
          placeholder="What did you notice?"
          disabled={sending}
        />
        <small className={details.length > DETAILS_LIMIT ? "is-over" : ""}>
          {details.length} / {DETAILS_LIMIT}
        </small>
      </label>

      {error && (
        <p className="ro-error" role="alert">
          {error}
        </p>
      )}

      <div className="ro-actions">
        <button type="button" className="ro-cancel" onClick={() => setOpen(false)} disabled={sending}>
          Cancel
        </button>
        <button type="submit" className="ro-submit" disabled={sending}>
          {sending ? "Sending..." : "Send report"}
        </button>
      </div>
    </form>
  );
}
