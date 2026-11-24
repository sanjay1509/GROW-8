import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { KeyRound, Save, UserRound } from "lucide-react";

import {
  changePassword,
  getMe,
  passwordByteLength,
  passwordErrorMessage,
} from "../../services/account";
import type { Me } from "../../services/account";
import { rememberUserName, updateMyName } from "../../services/organization";
import { errorMessage } from "../../services/formErrors";
import "./AdminPages.css";

/** /admin/profile and /admin/settings: the admin's name and password. */
export default function AdminAccount({ section }: { section: "profile" | "settings" }) {
  const [me, setMe] = useState<Me | null>(null);
  const [name, setName] = useState("");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameError, setNameError] = useState("");
  const [nameNotice, setNameNotice] = useState("");

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwNotice, setPwNotice] = useState("");

  useEffect(() => {
    let active = true;
    getMe()
      .then((result) => {
        if (!active) return;
        setMe(result);
        setName(result.full_name);
      })
      .catch((err) => {
        if (active) setNameError(errorMessage(err, "Your account could not be loaded."));
      });
    return () => {
      active = false;
    };
  }, []);

  async function saveName(event: FormEvent) {
    event.preventDefault();
    setNameError("");
    setNameNotice("");
    if (!name.trim()) {
      setNameError("Your name can't be empty.");
      return;
    }
    if (name.trim().length > 150) {
      setNameError("Keep your name under 150 characters.");
      return;
    }
    setNameSaving(true);
    try {
      const updated = await updateMyName(name);
      setMe(updated);
      setName(updated.full_name);
      rememberUserName(updated.full_name);
      setNameNotice("Your name was saved.");
    } catch (err) {
      setNameError(errorMessage(err, "Your name could not be saved."));
    } finally {
      setNameSaving(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPwNotice("");
    let problem = "";
    if (!current) problem = "Enter your current password.";
    else if (next.length < 8) problem = "The new password must be at least 8 characters.";
    else if (passwordByteLength(next) > 72) problem = "The new password is too long (72 bytes at most).";
    else if (next === current) problem = "Your new password must be different from the current one.";
    else if (next !== confirm) problem = "The new passwords don't match.";
    setPwError(problem);
    if (problem) return;

    setPwSaving(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setPwNotice("Your password was changed.");
    } catch (err) {
      setPwError(passwordErrorMessage(err));
    } finally {
      setPwSaving(false);
    }
  }

  return (
    <section className="adm-page adm-account">
      <header className="adm-head">
        <div>
          <span className="adm-eyebrow">ADMIN</span>
          <h1>{section === "profile" ? "Profile" : "Settings"}</h1>
          <p>{section === "profile" ? "Your name as it appears in Grow8." : "Your password."}</p>
        </div>
      </header>

      {section === "profile" && (
        <form className="adm-card" onSubmit={(event) => void saveName(event)}>
          <h2>
            <UserRound size={18} /> Account
          </h2>
          <label className="adm-field">
            <span>Full name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} disabled={nameSaving || !me} />
          </label>
          <label className="adm-field">
            <span>Email</span>
            <input value={me?.email ?? ""} readOnly disabled title="Email can't be changed" />
            <small>Email can't be changed.</small>
          </label>
          <div className="adm-actions">
            <button type="submit" className="adm-button is-primary" disabled={nameSaving || !me || name.trim() === me.full_name}>
              <Save size={15} /> {nameSaving ? "Saving..." : "Save name"}
            </button>
          </div>
          {nameNotice && (
            <p className="adm-notice" role="status">
              {nameNotice}
            </p>
          )}
          {nameError && (
            <p className="adm-error" role="alert">
              {nameError}
            </p>
          )}
        </form>
      )}

      {section === "settings" && (
        <form className="adm-card" onSubmit={(event) => void savePassword(event)}>
          <h2>
            <KeyRound size={18} /> Change password
          </h2>
          <label className="adm-field">
            <span>Current password</span>
            <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" disabled={pwSaving} />
          </label>
          <label className="adm-field">
            <span>New password</span>
            <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" disabled={pwSaving} />
            <small>At least 8 characters.</small>
          </label>
          <label className="adm-field">
            <span>Confirm new password</span>
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" disabled={pwSaving} />
          </label>
          <div className="adm-actions">
            <button type="submit" className="adm-button is-primary" disabled={pwSaving}>
              {pwSaving ? "Saving..." : "Change password"}
            </button>
          </div>
          {pwNotice && (
            <p className="adm-notice" role="status">
              {pwNotice}
            </p>
          )}
          {pwError && (
            <p className="adm-error" role="alert">
              {pwError}
            </p>
          )}
        </form>
      )}
    </section>
  );
}
