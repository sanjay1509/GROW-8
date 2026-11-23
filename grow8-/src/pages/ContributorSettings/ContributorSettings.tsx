import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Eye, EyeOff, KeyRound, UserRound } from "lucide-react";

import {
  changePassword,
  getMe,
  passwordByteLength,
  passwordErrorMessage,
} from "../../services/account";
import type { Me } from "../../services/account";
import "../ContributorProfile/ContributorProfile.css";
import "./ContributorSettings.css";

/** /contributor/settings: account details and password change. */
export default function ContributorSettings() {
  const [me, setMe] = useState<Me | null>(null);
  const [loadError, setLoadError] = useState("");

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    getMe()
      .then((data) => {
        if (active) setMe(data);
      })
      .catch(() => {
        if (active) setLoadError("Your account details could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, []);

  function validate(): string {
    if (!current) return "Enter your current password.";
    if (next.length < 8) return "The new password must be at least 8 characters.";
    if (passwordByteLength(next) > 72) return "The new password is too long (72 bytes at most).";
    if (next === current) return "Your new password must be different from the current one.";
    if (next !== confirm) return "The new passwords don't match.";
    return "";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    const problem = validate();
    setError(problem);
    if (problem) return;

    setSaving(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setNotice("Your password was changed.");
    } catch (err) {
      setError(passwordErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const inputType = show ? "text" : "password";

  return (
    <div className="cp-page">
      <header className="cp-header">
        <span className="cp-eyebrow">CONTRIBUTOR WORKSPACE</span>
        <h1>Settings</h1>
        <p>Manage your account and sign-in details.</p>
      </header>

      <div className="cs-sections">
        <section className="cp-card" aria-labelledby="cs-account-title">
          <div className="cp-card-heading">
            <h2 id="cs-account-title">
              <UserRound size={17} /> Account
            </h2>
          </div>
          {loadError && <p className="cp-error">{loadError}</p>}
          {!loadError && (
            <dl className="cs-details">
              <div>
                <dt>Name</dt>
                <dd>{me?.full_name ?? "…"}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{me?.email ?? "…"}</dd>
              </div>
              <div>
                <dt>Account type</dt>
                <dd>{me ? me.role.charAt(0).toUpperCase() + me.role.slice(1) : "…"}</dd>
              </div>
            </dl>
          )}
        </section>

        <section className="cp-card" aria-labelledby="cs-password-title">
          <div className="cp-card-heading">
            <h2 id="cs-password-title">
              <KeyRound size={17} /> Change password
            </h2>
            <p>8 to 72 characters. You stay signed in after changing it.</p>
          </div>

          <form className="cs-form" onSubmit={handleSubmit} noValidate>
            <label>
              Current password
              <input
                type={inputType}
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                disabled={saving}
              />
            </label>
            <label>
              New password
              <input
                type={inputType}
                autoComplete="new-password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                disabled={saving}
              />
            </label>
            <label>
              Confirm new password
              <input
                type={inputType}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                disabled={saving}
              />
            </label>

            <div className="cs-form-footer">
              <button type="button" className="cp-link-button cs-show" onClick={() => setShow((v) => !v)}>
                {show ? <EyeOff size={15} /> : <Eye size={15} />}
                {show ? "Hide passwords" : "Show passwords"}
              </button>
              <button type="submit" className="cp-button is-primary" disabled={saving}>
                {saving ? "Saving..." : "Change password"}
              </button>
            </div>

            {error && (
              <p className="cp-error" role="alert">
                {error}
              </p>
            )}
            {notice && (
              <p className="cp-notice" role="status">
                {notice}
              </p>
            )}
          </form>
        </section>
      </div>
    </div>
  );
}
