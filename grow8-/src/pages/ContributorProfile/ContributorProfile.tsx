import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import type { ChangeEvent, FormEvent } from "react";
import {
  Download,
  FileText,
  Mail,
  Save,
  Trash2,
  Upload,
  UserRound,
} from "lucide-react";

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
import {
  getMyProfile,
  updateMyProfile,
} from "../../services/profile";
import type { ContributorProfile as Profile } from "../../services/profile";
import { changedFields, errorMessage, fieldErrorsFrom } from "../../services/formErrors";
import type { FieldErrors } from "../../services/formErrors";
import "./ContributorProfile.css";

type ProfileForm = {
  full_name: string;
  headline: string;
  institution: string;
  city: string;
  bio: string;
};

const EMPTY_FORM: ProfileForm = { full_name: "", headline: "", institution: "", city: "", bio: "" };

const LIMITS: Record<keyof ProfileForm, number> = {
  full_name: 150,
  headline: 150,
  institution: 150,
  city: 100,
  bio: 5000,
};

function toForm(profile: Profile): ProfileForm {
  return {
    full_name: profile.full_name ?? "",
    headline: profile.headline ?? "",
    institution: profile.institution ?? "",
    city: profile.city ?? "",
    bio: profile.bio ?? "",
  };
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/**
 * /contributor/profile: the contributor's profile (ADR 0017), their listed and earned
 * skills (ADR 0019) and their resume (ADR 0008). Creators see this profile on applications.
 */
export default function ContributorProfile() {
  // ---------- profile ----------
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<ProfileForm>(EMPTY_FORM);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState("");
  const [profileNotice, setProfileNotice] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [savingProfile, setSavingProfile] = useState(false);

  // ---------- skills ----------

  // ---------- resume ----------
  const [resume, setResume] = useState<Resume | null>(null);
  const [resumeLoading, setResumeLoading] = useState(true);
  const [resumeError, setResumeError] = useState("");
  const [resumeNotice, setResumeNotice] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const userName = profile?.full_name || localStorage.getItem("user_name") || "Contributor";

  // /contributor/profile#skills (the sidebar's "My Skills") scrolls to that section.
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    const sectionId = hash.slice(1);
    let attempts = 0;
    let timer = 0;
    const scrollToSection = () => {
      const section = document.getElementById(sectionId);
      if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      } else if (attempts++ < 20) {
        timer = window.setTimeout(scrollToSection, 50);
      }
    };
    // Wait for route rendering and layout before scrolling to a hash target.
    timer = window.setTimeout(scrollToSection, 0);
    return () => window.clearTimeout(timer);
  }, [hash]);

  useEffect(() => {
    let active = true;
    getMyProfile()
      .then((data) => {
        if (!active) return;
        setProfile(data);
        setForm(toForm(data));
      })
      .catch((err) => {
        if (active) setProfileError(errorMessage(err, "Your profile could not be loaded."));
      })
      .finally(() => {
        if (active) setProfileLoading(false);
      });

    getMyResume()
      .then((result) => {
        if (active) setResume(result);
      })
      .catch((err) => {
        if (active) setResumeError(resumeErrorMessage(err, "Your resume could not be loaded."));
      })
      .finally(() => {
        if (active) setResumeLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  // ---------- profile form ----------

  const changes = useMemo(
    () => (profile ? changedFields(toForm(profile), form) : {}),
    [profile, form]
  );
  const hasChanges = Object.keys(changes).length > 0;
  const isNewProfile = profile !== null && profile.updated_at === null;

  function updateField(field: keyof ProfileForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
    setProfileNotice("");
  }

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!form.full_name.trim()) {
      errors.full_name = "Your name can't be empty.";
    }
    (Object.keys(LIMITS) as (keyof ProfileForm)[]).forEach((field) => {
      if (form[field].trim().length > LIMITS[field]) {
        errors[field] = `Keep this under ${LIMITS[field]} characters.`;
      }
    });
    return errors;
  }

  async function handleSaveProfile(event: FormEvent) {
    event.preventDefault();
    setProfileError("");
    setProfileNotice("");

    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    // The first save creates the profile, so send something even if nothing changed.
    const body = hasChanges ? changes : isNewProfile ? { full_name: form.full_name.trim() } : {};
    if (Object.keys(body).length === 0) {
      setProfileNotice("Nothing to save.");
      return;
    }

    setSavingProfile(true);
    try {
      const saved = await updateMyProfile(body);
      setProfile(saved);
      setForm(toForm(saved));
      localStorage.setItem("user_name", saved.full_name);
      // The navbars read the name when they render; tell them it changed.
      window.dispatchEvent(new Event("grow8:user-name-changed"));
      setProfileNotice(isNewProfile ? "Your profile was created." : "Your profile was saved.");
    } catch (err) {
      setFieldErrors(fieldErrorsFrom(err));
      setProfileError(errorMessage(err, "Your profile could not be saved."));
    } finally {
      setSavingProfile(false);
    }
  }

  // ---------- resume ----------

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow picking the same file again
    if (!file) return;

    setResumeError("");
    setResumeNotice("");
    // Quick checks before uploading; the server checks the real file content too.
    if (file.size === 0) {
      setResumeError("That file is empty.");
      return;
    }
    if (file.size > RESUME_MAX_BYTES) {
      setResumeError("That file is larger than 10 MB.");
      return;
    }
    if (file.type && file.type !== "application/pdf") {
      setResumeError("Only PDF files can be uploaded.");
      return;
    }

    setBusy(true);
    setProgress(0);
    try {
      const saved = await uploadResume(file, setProgress);
      setResumeNotice(resume ? "Your resume was replaced." : "Your resume was uploaded.");
      setResume(saved);
    } catch (err) {
      setResumeError(resumeErrorMessage(err, "Your resume could not be uploaded."));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  async function handleDownload() {
    if (!resume) return;
    setResumeError("");
    try {
      await downloadMyResume(resume.file_name);
    } catch (err) {
      setResumeError(resumeErrorMessage(err, "Your resume could not be downloaded."));
    }
  }

  async function handleDelete() {
    setBusy(true);
    setResumeError("");
    setResumeNotice("");
    try {
      await deleteResume();
      setResume(null);
      setResumeNotice("Your resume was removed.");
    } catch (err) {
      setResumeError(resumeErrorMessage(err, "Your resume could not be removed."));
    } finally {
      setBusy(false);
      setConfirmDelete(false);
    }
  }

  // ---------- render ----------

  function textField(field: keyof ProfileForm, label: string, placeholder: string) {
    const error = fieldErrors[field];
    return (
      <label className={`cp-field ${error ? "has-error" : ""}`}>
        <span>{label}</span>
        <input
          type="text"
          value={form[field]}
          placeholder={placeholder}
          maxLength={LIMITS[field] + 50}
          onChange={(event) => updateField(field, event.target.value)}
          aria-invalid={Boolean(error)}
          disabled={savingProfile}
        />
        {error && <em className="cp-field-error">{error}</em>}
      </label>
    );
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
          {initials(userName)}
        </span>
        <div className="cp-identity-info">
          <strong>{userName}</strong>
          <span>
            <UserRound size={14} /> Contributor
          </span>
          {profile?.email && (
            <span>
              <Mail size={14} /> {profile.email}
            </span>
          )}
        </div>
        {profile?.updated_at && (
          <p className="cp-muted cp-identity-note">Last updated {formatDate(profile.updated_at)}</p>
        )}
      </section>

      {/* ---------- Profile ---------- */}
      <section className="cp-card" id="profile" aria-labelledby="cp-profile-title">
        <div className="cp-card-heading">
          <h2 id="cp-profile-title">Profile</h2>
          <p>Organizations see this when you apply. Leave a field empty to clear it.</p>
        </div>

        {profileLoading && <p className="cp-muted">Loading...</p>}

        {isNewProfile && (
          <p className="cp-callout" role="status">
            Save your profile first. Until then you can't apply to opportunities or upload a resume.
          </p>
        )}

        {!profileLoading && profile && (
          <form className="cp-form" onSubmit={(event) => void handleSaveProfile(event)} noValidate>
            <div className="cp-form-grid">
              {textField("full_name", "Full name", "Your name")}
              {textField("headline", "Headline", "e.g. Software engineering student")}
              {textField("institution", "School or institution", "e.g. University of Calgary")}
              {textField("city", "City", "e.g. Calgary")}
            </div>

            <label className={`cp-field ${fieldErrors.bio ? "has-error" : ""}`}>
              <span>About you</span>
              <textarea
                rows={5}
                value={form.bio}
                placeholder="What you're studying, what you'd like to learn, and what you're good at."
                onChange={(event) => updateField("bio", event.target.value)}
                aria-invalid={Boolean(fieldErrors.bio)}
                disabled={savingProfile}
              />
              <small className={form.bio.length > LIMITS.bio ? "is-over" : ""}>
                {form.bio.length} / {LIMITS.bio}
              </small>
              {fieldErrors.bio && <em className="cp-field-error">{fieldErrors.bio}</em>}
            </label>

            <div className="cp-form-actions">
              <button
                type="submit"
                className="cp-button is-primary"
                disabled={savingProfile || (!hasChanges && !isNewProfile)}
              >
                <Save size={15} />
                {savingProfile ? "Saving..." : isNewProfile ? "Create profile" : "Save changes"}
              </button>
              {hasChanges && !savingProfile && (
                <button
                  type="button"
                  className="cp-link-button"
                  onClick={() => {
                    setForm(toForm(profile));
                    setFieldErrors({});
                  }}
                >
                  Discard changes
                </button>
              )}
            </div>
          </form>
        )}

        {profileNotice && (
          <p className="cp-notice" role="status">
            {profileNotice}
          </p>
        )}
        {profileError && (
          <p className="cp-error" role="alert">
            {profileError}
          </p>
        )}
      </section>

      {/* ---------- Resume ---------- */}
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

        {resumeLoading && <p className="cp-muted">Loading...</p>}

        {!resumeLoading && resume && (
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

        {!resumeLoading && !resume && <p className="cp-muted">You haven't uploaded a resume yet.</p>}

        {!resumeLoading && (
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
              disabled={busy || isNewProfile}
              title={isNewProfile ? "Save your profile first" : undefined}
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

        {resumeNotice && (
          <p className="cp-notice" role="status">
            {resumeNotice}
          </p>
        )}
        {resumeError && (
          <p className="cp-error" role="alert">
            {resumeError}
          </p>
        )}
      </section>
    </div>
  );
}
