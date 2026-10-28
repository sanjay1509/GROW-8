
import { useEffect, useState, type FormEvent } from "react";
import {
  UserRound,
  Mail,
  LockKeyhole,
  Eye,
  EyeOff,
  Pencil,
  Save,
  X,
  ShieldCheck,
} from "lucide-react";
import "./CreatorProfile.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type Creator = {
  id?: string | number;
  name: string;
  email: string;
};

type PasswordForm = {
  current_password: string;
  new_password: string;
  confirm_password: string;
};

type ApiResponse = {
  message?: string;
  detail?: string;
  error?: { message?: string };
  user?: Record<string, unknown>;
  data?: Record<string, unknown>;
  full_name?: string;
  name?: string;
  display_name?: string;
  username?: string;
  email?: string;
};

function getToken() {
  return localStorage.getItem("access_token");
}

async function apiRequest(path: string, options: RequestInit = {}) {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data?.error?.message ||
        data?.detail ||
        data?.message ||
        `Request failed (${response.status}).`,
    );
  }

  return data;
}

function parseCreator(data: ApiResponse): Creator {
  const user =
    data.user && typeof data.user === "object"
      ? data.user
      : data.data && typeof data.data === "object"
        ? data.data
        : data;

  return {
    id: user.id as string | number | undefined,
    name: String(
      user.full_name ?? user.name ?? user.display_name ?? user.username ?? "",
    ),
    email: String(user.email ?? ""),
  };
}

function getInitials(name: string) {
  return (
    name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join("") || "CR"
  );
}

export default function CreatorProfile() {
  const [creator, setCreator] = useState<Creator>({
    name: "",
    email: "",
  });

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");

  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [passwordForm, setPasswordForm] = useState<PasswordForm>({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        if (!getToken()) {
          throw new Error("Please log in to view your profile.");
        }

        const data = await apiRequest("/auth/me");

        if (!active) return;

        const profile = parseCreator(data as ApiResponse);
        setCreator(profile);
        setName(profile.name);
        setEmail(profile.email);
      } catch (error) {
        if (active) {
          setProfileError(
            error instanceof Error
              ? error.message
              : "Unable to load your profile.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadProfile();

    return () => {
      active = false;
    };
  }, []);

  async function handleProfileSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileError("");
    setProfileSuccess("");

    if (!name.trim() || !email.trim()) {
      setProfileError("Name and email are required.");
      return;
    }

    setSavingProfile(true);

    try {
      // Requires a backend endpoint that updates the authenticated user's profile.
      const data = await apiRequest("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: name.trim(),
          email: email.trim(),
        }),
      });

      const updated =
        data && typeof data === "object"
          ? parseCreator(data as ApiResponse)
          : { name: name.trim(), email: email.trim() };

      const nextCreator = {
        ...creator,
        name: updated.name || name.trim(),
        email: updated.email || email.trim(),
      };

      setCreator(nextCreator);
      setName(nextCreator.name);
      setEmail(nextCreator.email);
      setEditing(false);
      setProfileSuccess("Your profile has been updated.");
    } catch (error) {
      setProfileError(
        error instanceof Error
          ? error.message
          : "Unable to update your profile.",
      );
    } finally {
      setSavingProfile(false);
    }
  }

  function closePasswordModal() {
    if (savingPassword) return;

    setPasswordModalOpen(false);
    setPasswordError("");
    setPasswordSuccess("");
    setPasswordForm({
      current_password: "",
      new_password: "",
      confirm_password: "",
    });
    setShowPasswords({ current: false, new: false, confirm: false });
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");

    if (
      !passwordForm.current_password ||
      !passwordForm.new_password ||
      !passwordForm.confirm_password
    ) {
      setPasswordError("Please complete all password fields.");
      return;
    }

    if (passwordForm.new_password.length < 8) {
      setPasswordError("Your new password must contain at least 8 characters.");
      return;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("The new passwords do not match.");
      return;
    }

    if (passwordForm.current_password === passwordForm.new_password) {
      setPasswordError("Your new password must differ from your current password.");
      return;
    }

    setSavingPassword(true);

    try {
      // This endpoint must verify the current password and securely update
      // the password hash in the database on the backend.
      await apiRequest("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      });

      setPasswordSuccess("Password changed successfully.");
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });

      window.setTimeout(() => {
        setPasswordModalOpen(false);
        setPasswordSuccess("");
      }, 1000);
    } catch (error) {
      setPasswordError(
        error instanceof Error
          ? error.message
          : "Unable to change your password.",
      );
    } finally {
      setSavingPassword(false);
    }
  }

  const displayName = creator.name || "Creator";
  const initials = getInitials(displayName);

  return (
    <main className="creator-profile-page">
      <header className="creator-profile-heading">
        <div>
          <span className="creator-profile-eyebrow">ACCOUNT SETTINGS</span>
          <h1>My Profile</h1>
          <p>Manage your personal information and account security.</p>
        </div>
        <div className="creator-profile-heading-icon">
          <UserRound size={26} />
        </div>
      </header>

      {profileError && (
        <div className="creator-profile-alert error" role="alert">
          {profileError}
        </div>
      )}

      {profileSuccess && (
        <div className="creator-profile-alert success" role="status">
          {profileSuccess}
        </div>
      )}

      {loading ? (
        <div className="creator-profile-loading">Loading your profile...</div>
      ) : (
        <>
          <section className="creator-profile-hero">
            <div className="creator-profile-avatar">{initials}</div>
            <div className="creator-profile-hero-info">
              <span className="creator-profile-role">
                <ShieldCheck size={15} /> Creator account
              </span>
              <h2>{displayName}</h2>
              <p>{creator.email || "No email available"}</p>
            </div>
            {!editing && (
              <button
                className="creator-profile-secondary-button"
                type="button"
                onClick={() => {
                  setName(creator.name);
                  setEmail(creator.email);
                  setProfileError("");
                  setProfileSuccess("");
                  setEditing(true);
                }}
              >
                <Pencil size={16} /> Edit profile
              </button>
            )}
          </section>

          <section className="creator-profile-card">
            <div className="creator-profile-card-heading">
              <div className="creator-profile-section-icon">
                <UserRound size={20} />
              </div>
              <div>
                <h2>Personal information</h2>
                <p>Your name and email address.</p>
              </div>
            </div>

            <form onSubmit={handleProfileSave}>
              <div className="creator-profile-fields">
                <label className="creator-profile-field">
                  <span>Full name</span>
                  <div className="creator-profile-input-wrap">
                    <UserRound size={17} />
                    <input
                      type="text"
                      value={editing ? name : creator.name}
                      onChange={(event) => setName(event.target.value)}
                      placeholder="Your full name"
                      autoComplete="name"
                      disabled={!editing || savingProfile}
                      required
                    />
                  </div>
                </label>

                <label className="creator-profile-field">
                  <span>Email address</span>
                  <div className="creator-profile-input-wrap">
                    <Mail size={17} />
                    <input
                      type="email"
                      value={editing ? email : creator.email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="you@example.com"
                      autoComplete="email"
                      disabled={!editing || savingProfile}
                      required
                    />
                  </div>
                </label>
              </div>

              {editing && (
                <div className="creator-profile-form-actions">
                  <button
                    className="creator-profile-secondary-button"
                    type="button"
                    disabled={savingProfile}
                    onClick={() => {
                      setName(creator.name);
                      setEmail(creator.email);
                      setEditing(false);
                      setProfileError("");
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    className="creator-profile-primary-button"
                    type="submit"
                    disabled={savingProfile}
                  >
                    <Save size={16} />
                    {savingProfile ? "Saving..." : "Save changes"}
                  </button>
                </div>
              )}
            </form>
          </section>

          <section className="creator-profile-card creator-profile-security-card">
            <div className="creator-profile-card-heading">
              <div className="creator-profile-section-icon security">
                <LockKeyhole size={20} />
              </div>
              <div>
                <h2>Password & security</h2>
                <p>Keep your account secure with a strong password.</p>
              </div>
            </div>

            <div className="creator-profile-security-row">
              <div>
                <strong>Password</strong>
                <p>Change your password whenever you need to.</p>
              </div>
              <button
                type="button"
                className="creator-profile-primary-button"
                onClick={() => {
                  setPasswordError("");
                  setPasswordSuccess("");
                  setPasswordModalOpen(true);
                }}
              >
                <LockKeyhole size={16} /> Change password
              </button>
            </div>
          </section>
        </>
      )}

      {passwordModalOpen && (
        <div
          className="creator-password-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closePasswordModal();
          }}
        >
          <section
            className="creator-password-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="creator-password-title"
          >
            <button
              type="button"
              className="creator-password-close"
              onClick={closePasswordModal}
              disabled={savingPassword}
              aria-label="Close change password dialog"
            >
              <X size={20} />
            </button>

            <div className="creator-password-modal-icon">
              <LockKeyhole size={24} />
            </div>
            <h2 id="creator-password-title">Change password</h2>
            <p className="creator-password-modal-description">
              Enter your current password, then choose a new one.
            </p>

            <form onSubmit={handlePasswordChange}>
              {(
                [
                  ["current_password", "Current password", "current"],
                  ["new_password", "New password", "new"],
                  ["confirm_password", "Confirm new password", "confirm"],
                ] as const
              ).map(([field, label, key]) => (
                <label className="creator-password-field" key={field}>
                  <span>{label}</span>
                  <div className="creator-password-input-wrap">
                    <input
                      type={showPasswords[key] ? "text" : "password"}
                      value={passwordForm[field]}
                      onChange={(event) =>
                        setPasswordForm((previous) => ({
                          ...previous,
                          [field]: event.target.value,
                        }))
                      }
                      autoComplete={
                        key === "current" ? "current-password" : "new-password"
                      }
                      required
                      disabled={savingPassword}
                    />
                    <button
                      type="button"
                      aria-label={
                        showPasswords[key] ? `Hide ${label}` : `Show ${label}`
                      }
                      onClick={() =>
                        setShowPasswords((previous) => ({
                          ...previous,
                          [key]: !previous[key],
                        }))
                      }
                    >
                      {showPasswords[key] ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>
                </label>
              ))}

              <p className="creator-password-hint">
                Use at least 8 characters. Your new password must differ from
                your current password.
              </p>

              {passwordError && (
                <p className="creator-profile-alert error" role="alert">
                  {passwordError}
                </p>
              )}
              {passwordSuccess && (
                <p className="creator-profile-alert success" role="status">
                  {passwordSuccess}
                </p>
              )}

              <div className="creator-password-modal-actions">
                <button
                  type="button"
                  className="creator-profile-secondary-button"
                  onClick={closePasswordModal}
                  disabled={savingPassword}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="creator-profile-primary-button"
                  disabled={savingPassword}
                >
                  {savingPassword ? "Updating..." : "Update password"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
