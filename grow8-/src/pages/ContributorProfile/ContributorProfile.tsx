import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Download, FileText, Mail, Trash2, Upload, UserRound } from "lucide-react";

import {
  RESUME_MAX_BYTES,
  deleteResume,
  downloadMyResume,
  formatFileSize,
  getMyResume,
  resumeErrorMessage,
  uploadResume,
} from "../../services/resume";
import type { Resume } from "../../services/resume";
import { getMe } from "../../services/account";
import type { Me } from "../../services/account";
import "./ContributorProfile.css";

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

/**
 * /contributor/profile: account details (GET /auth/me) and the resume (ADR 0008): one
 * optional PDF, at most 10 MB, that creators see on the contributor's applications.
 * Editing headline, bio, institution, city and skills needs backend issue #19.
 */
export default function ContributorProfile() {
  const [me, setMe] = useState<Me | null>(null);
  const userName = me?.full_name || localStorage.getItem("user_name") || "Contributor";

  const [resume, setResume] = useState<Resume | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    getMe()
      .then((data) => {
        if (active) setMe(data);
      })
      .catch(() => {
        // The name from sign-in is shown instead.
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    getMyResume()
      .then((result) => {
        if (active) setResume(result);
      })
      .catch((err) => {
        if (active) setError(resumeErrorMessage(err, "Your resume could not be loaded."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow picking the same file again
    if (!file) {
      return;
    }

    setError("");
    setNotice("");
    // Quick checks before uploading; the server checks the real file content too.
    if (file.size === 0) {
      setError("That file is empty.");
      return;
    }
    if (file.size > RESUME_MAX_BYTES) {
      setError("That file is larger than 10 MB.");
      return;
    }
    if (file.type && file.type !== "application/pdf") {
      setError("Only PDF files can be uploaded.");
      return;
    }

    setBusy(true);
    setProgress(0);
    try {
      const saved = await uploadResume(file, setProgress);
      setNotice(resume ? "Your resume was replaced." : "Your resume was uploaded.");
      setResume(saved);
    } catch (err) {
      setError(resumeErrorMessage(err, "Your resume could not be uploaded."));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  async function handleDownload() {
    if (!resume) {
      return;
    }
    setError("");
    try {
      await downloadMyResume(resume.file_name);
    } catch (err) {
      setError(resumeErrorMessage(err, "Your resume could not be downloaded."));
    }
  }

  async function handleDelete() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await deleteResume();
      setResume(null);
      setNotice("Your resume was removed.");
    } catch (err) {
      setError(resumeErrorMessage(err, "Your resume could not be removed."));
    } finally {
      setBusy(false);
      setConfirmDelete(false);
    }
  }

  return (
    <div className="cp-page">
      <header className="cp-header">
        <span className="cp-eyebrow">CONTRIBUTOR WORKSPACE</span>
        <h1>{userName}</h1>
        <p>Your profile as organizations see it when you apply.</p>
      </header>

      <section className="cp-card cp-identity" aria-label="Account">
        <span className="cp-avatar" aria-hidden="true">
          {userName
            .split(/\s+/)
            .slice(0, 2)
            .map((part) => part[0]?.toUpperCase() ?? "")
            .join("")}
        </span>
        <div className="cp-identity-info">
          <strong>{userName}</strong>
          <span>
            <UserRound size={14} /> Contributor
          </span>
          {me?.email && (
            <span>
              <Mail size={14} /> {me.email}
            </span>
          )}
        </div>
        <p className="cp-muted cp-identity-note">
          Headline, bio, school, city and skills will be editable here once the profile
          endpoints are added to the backend.
        </p>
      </section>

      <section className="cp-card" aria-labelledby="cp-resume-title">
        <div className="cp-card-heading">
          <div>
            <h2 id="cp-resume-title">Resume</h2>
            <p>
              Optional. One PDF, up to 10 MB. Organizations you apply to can download your
              current resume.
            </p>
          </div>
        </div>

        {loading && <p className="cp-muted">Loading...</p>}

        {!loading && resume && (
          <div className="cp-file">
            <span className="cp-file-icon">
              <FileText size={22} />
            </span>
            <div className="cp-file-info">
              <strong>{resume.file_name}</strong>
              <span>
                {formatFileSize(resume.size_bytes)} · uploaded {formatDate(resume.uploaded_at)}
              </span>
            </div>
            <div className="cp-file-actions">
              <button type="button" className="cp-button" onClick={() => void handleDownload()} disabled={busy}>
                <Download size={15} /> Download
              </button>
              {!confirmDelete ? (
                <button
                  type="button"
                  className="cp-button is-danger"
                  onClick={() => setConfirmDelete(true)}
                  disabled={busy}
                >
                  <Trash2 size={15} /> Remove
                </button>
              ) : (
                <span className="cp-confirm">
                  Remove it?
                  <button
                    type="button"
                    className="cp-button is-danger"
                    onClick={() => void handleDelete()}
                    disabled={busy}
                  >
                    Yes, remove
                  </button>
                  <button
                    type="button"
                    className="cp-link-button"
                    onClick={() => setConfirmDelete(false)}
                    disabled={busy}
                  >
                    Cancel
                  </button>
                </span>
              )}
            </div>
          </div>
        )}

        {!loading && !resume && (
          <p className="cp-muted">You haven't uploaded a resume yet.</p>
        )}

        {!loading && (
          <div className="cp-upload">
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => void handleFile(event)}
              hidden
            />
            <button
              type="button"
              className="cp-button is-primary"
              onClick={() => fileInput.current?.click()}
              disabled={busy}
            >
              <Upload size={16} /> {resume ? "Replace resume" : "Upload resume"}
            </button>

            {progress !== null && (
              <div
                className="cp-progress"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progress}
                aria-label="Upload progress"
              >
                <span style={{ width: `${progress}%` }} />
                <em>{progress}%</em>
              </div>
            )}
          </div>
        )}

        {notice && (
          <p className="cp-notice" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="cp-error" role="alert">
            {error}
          </p>
        )}
      </section>
    </div>
  );
}
