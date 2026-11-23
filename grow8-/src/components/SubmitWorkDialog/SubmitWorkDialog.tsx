import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { FileText, Paperclip, Send, X } from "lucide-react";

import {
  ATTACHMENT_ACCEPT,
  MAX_ATTACHMENTS,
  MAX_ATTACHMENT_BYTES,
  WORK_MESSAGES,
  isValidHours,
  submitWork,
} from "../../services/submissions";
import type { Submission } from "../../services/submissions";
import { formatFileSize } from "../../services/resume";
import { errorMessage, fieldErrorsFrom } from "../../services/formErrors";
import "./SubmitWorkDialog.css";

const DESCRIPTION_LIMIT = 5000;

type Props = {
  applicationId: number;
  opportunityTitle: string;
  onClose: () => void;
  onSubmitted: (submission: Submission) => void;
};

/**
 * Submit work for an accepted application (ADR 0012): a description, the hours worked
 * and up to 5 files. It can be sent once, then the organization verifies it.
 */
export default function SubmitWorkDialog({
  applicationId,
  opportunityTitle,
  onClose,
  onSubmitted,
}: Props) {
  const [description, setDescription] = useState("");
  const [hours, setHours] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const firstField = useRef<HTMLTextAreaElement>(null);
  const sending = progress !== null;

  useEffect(() => {
    firstField.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !sending) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, sending]);

  function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = "";
    setError("");

    const tooBig = picked.find((file) => file.size > MAX_ATTACHMENT_BYTES);
    const empty = picked.find((file) => file.size === 0);
    if (tooBig) {
      setErrors((current) => ({ ...current, files: `${tooBig.name} is larger than 5 MB.` }));
      return;
    }
    if (empty) {
      setErrors((current) => ({ ...current, files: `${empty.name} is empty.` }));
      return;
    }
    const next = [...files, ...picked];
    if (next.length > MAX_ATTACHMENTS) {
      setErrors((current) => ({ ...current, files: `You can attach up to ${MAX_ATTACHMENTS} files.` }));
      return;
    }
    setErrors((current) => ({ ...current, files: "" }));
    setFiles(next);
  }

  function validate(): Record<string, string> {
    const result: Record<string, string> = {};
    if (!description.trim()) {
      result.description = "Describe the work you did.";
    } else if (description.trim().length > DESCRIPTION_LIMIT) {
      result.description = `Keep this under ${DESCRIPTION_LIMIT} characters.`;
    }
    if (!isValidHours(hours)) {
      result.hours_claimed = "Enter the hours you worked, e.g. 6 or 6.5 (up to 2 decimals).";
    }
    return result;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    const found = validate();
    setErrors(found);
    if (Object.keys(found).some((key) => found[key])) return;

    setProgress(0);
    try {
      const submission = await submitWork(applicationId, description, hours, files, setProgress);
      onSubmitted(submission);
    } catch (err) {
      setErrors(fieldErrorsFrom(err));
      setError(errorMessage(err, "Your work could not be submitted.", WORK_MESSAGES));
      setProgress(null);
    }
  }

  return (
    <div className="sw-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !sending && onClose()}>
      <div className="sw-dialog" role="dialog" aria-modal="true" aria-labelledby="sw-title">
        <header>
          <div>
            <h2 id="sw-title">Submit your work</h2>
            <p>{opportunityTitle}</p>
          </div>
          <button type="button" className="sw-close" onClick={onClose} disabled={sending} aria-label="Close">
            <X size={18} />
          </button>
        </header>

        <form onSubmit={(event) => void handleSubmit(event)} noValidate>
          <label className={`sw-field ${errors.description ? "has-error" : ""}`}>
            <span>What did you do?</span>
            <textarea
              ref={firstField}
              rows={6}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe the work you completed, so the organization can verify it."
              disabled={sending}
            />
            <small className={description.length > DESCRIPTION_LIMIT ? "is-over" : ""}>
              {description.length} / {DESCRIPTION_LIMIT}
            </small>
            {errors.description && <em>{errors.description}</em>}
          </label>

          <label className={`sw-field sw-hours ${errors.hours_claimed ? "has-error" : ""}`}>
            <span>Hours worked</span>
            <input
              type="text"
              inputMode="decimal"
              value={hours}
              onChange={(event) => setHours(event.target.value)}
              placeholder="e.g. 6.5"
              disabled={sending}
            />
            {errors.hours_claimed && <em>{errors.hours_claimed}</em>}
          </label>

          <div className={`sw-field ${errors.files ? "has-error" : ""}`}>
            <span>Files (optional)</span>
            <p className="sw-hint">
              Up to {MAX_ATTACHMENTS} files, 5 MB each: PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT.
            </p>
            {files.length > 0 && (
              <ul className="sw-files">
                {files.map((file, index) => (
                  <li key={`${file.name}-${index}`}>
                    <FileText size={15} />
                    <span>{file.name}</span>
                    <small>{formatFileSize(file.size)}</small>
                    <button
                      type="button"
                      aria-label={`Remove ${file.name}`}
                      onClick={() => setFiles((current) => current.filter((_, i) => i !== index))}
                      disabled={sending}
                    >
                      <X size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <input ref={fileInput} type="file" multiple accept={ATTACHMENT_ACCEPT} onChange={addFiles} hidden />
            <button
              type="button"
              className="sw-button"
              onClick={() => fileInput.current?.click()}
              disabled={sending || files.length >= MAX_ATTACHMENTS}
            >
              <Paperclip size={15} /> Attach files
            </button>
            {errors.files && <em>{errors.files}</em>}
          </div>

          {progress !== null && (
            <div className="sw-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Upload progress">
              <span style={{ width: `${progress}%` }} />
              <em>{progress}%</em>
            </div>
          )}

          <p className="sw-note">You can submit once. After that, the organization reviews your work.</p>

          {error && (
            <p className="sw-error" role="alert">
              {error}
            </p>
          )}

          <footer>
            <button type="button" className="sw-button" onClick={onClose} disabled={sending}>
              Cancel
            </button>
            <button type="submit" className="sw-button is-primary" disabled={sending}>
              <Send size={15} /> {sending ? "Submitting..." : "Submit work"}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
