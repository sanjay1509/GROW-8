
import { useEffect, useState, type FormEvent } from "react";
import {
  UserRound,
  Mail,
  LockKeyhole,
  Eye,
  EyeOff,
  Bell,
  ShieldCheck,
  Save,
  Pencil,
  X,
  Eye as VisibilityIcon,
} from "lucide-react";
import "./CreatorSettings.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

type SettingsTab = "profile" | "security" | "notifications" | "privacy";

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

async function apiRequest(
  path: string,
  options: RequestInit = {}
) {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token
        ? { Authorization: `Bearer ${token}` }
        : {}),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data?.error?.message ||
        data?.detail ||
        data?.message ||
        `Request failed (${response.status}).`
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
      user.full_name ??
        user.name ??
        user.display_name ??
        user.username ??
        ""
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

export default function CreatorSettings() {
  const [activeTab, setActiveTab] =
    useState<SettingsTab>("profile");

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

  const [passwordModalOpen, setPasswordModalOpen] =
    useState(false);

  const [passwordForm, setPasswordForm] =
    useState<PasswordForm>({
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

  const [notifications, setNotifications] = useState({
    emailUpdates: true,
    applicationUpdates: true,
    contributorMessages: true,
    feedbackNotifications: true,
    announcements: false,
  });

  const [privacy, setPrivacy] = useState({
    publicProfile: true,
    showOrganization: true,
    allowMessages: true,
  });

  const [settingsMessage, setSettingsMessage] = useState("");

  // Load the same authenticated profile as CreatorProfile.tsx.
  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        if (!getToken()) {
          throw new Error("Please log in to view your settings.");
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
              : "Unable to load your profile."
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

  // Update authenticated creator profile.
  async function handleProfileSave(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setProfileError("");
    setProfileSuccess("");

    if (!name.trim() || !email.trim()) {
      setProfileError("Name and email are required.");
      return;
    }

    setSavingProfile(true);

    try {
      const data = await apiRequest("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: name.trim(),
          email: email.trim(),
        }),
      });

      const updated = parseCreator(data as ApiResponse);

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
          : "Unable to update your profile."
      );
    } finally {
      setSavingProfile(false);
    }
  }

  // Password modal.
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

    setShowPasswords({
      current: false,
      new: false,
      confirm: false,
    });
  }

  async function handlePasswordChange(
    event: FormEvent<HTMLFormElement>
  ) {
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
      setPasswordError(
        "Your new password must contain at least 8 characters."
      );
      return;
    }

    if (
      passwordForm.new_password !==
      passwordForm.confirm_password
    ) {
      setPasswordError("The new passwords do not match.");
      return;
    }

    if (
      passwordForm.current_password ===
      passwordForm.new_password
    ) {
      setPasswordError(
        "Your new password must differ from your current password."
      );
      return;
    }

    setSavingPassword(true);

    try {
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
          : "Unable to change your password."
      );
    } finally {
      setSavingPassword(false);
    }
  }

  function updateNotification(
    key: keyof typeof notifications
  ) {
    setNotifications((previous) => ({
      ...previous,
      [key]: !previous[key],
    }));
  }

  function updatePrivacy(key: keyof typeof privacy) {
    setPrivacy((previous) => ({
      ...previous,
      [key]: !previous[key],
    }));
  }

  function savePreferences(section: string) {
    // Preferences are currently local state only.
    setSettingsMessage(
      `${section} preferences updated for this session. Backend persistence is not yet connected.`
    );
  }

  const initials = getInitials(creator.name || "Creator");

  const tabs = [
    { id: "profile", label: "Profile Settings", icon: UserRound },
    { id: "security", label: "Account & Security", icon: LockKeyhole },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "privacy", label: "Privacy", icon: ShieldCheck },
  ] as const;

  const renderToggle = (
    checked: boolean,
    onChange: () => void,
    label: string,
    description: string
  ) => (
    <div className="cs-toggle-row">
      <div className="cs-toggle-info">
        <strong>{label}</strong>
        <p>{description}</p>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        className={`cs-switch ${checked ? "active" : ""}`}
        onClick={onChange}
        aria-label={label}
      >
        <span />
      </button>
    </div>
  );

  return (
    <main className="creator-settings-page">
      <header className="cs-header">
        <div>
          <div className="cs-breadcrumb">
            Creator Dashboard <span>/</span> Settings
          </div>

          <h1>Settings</h1>
          <p>
            Manage your profile, account preferences and security.
          </p>
        </div>
      </header>

      {settingsMessage && (
        <div className="cs-message" role="status">
          <p>{settingsMessage}</p>
          <button
            type="button"
            onClick={() => setSettingsMessage("")}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="cs-layout">
        <aside className="cs-sidebar">
          <div className="cs-sidebar-heading">
            SETTINGS MENU
          </div>

          {tabs.map((tab) => {
            const Icon = tab.icon;

            return (
              <button
                type="button"
                key={tab.id}
                className={`cs-nav-item ${
                  activeTab === tab.id ? "active" : ""
                }`}
                onClick={() => {
                  setActiveTab(tab.id);
                  setSettingsMessage("");
                }}
              >
                <Icon size={17} />
                {tab.label}
                <span className="cs-nav-arrow">›</span>
              </button>
            );
          })}
        </aside>

        <div className="cs-main">
          {activeTab === "profile" && (
            <section className="cs-section">
              <div className="cs-section-heading">
                <div>
                  <h2>Profile Information</h2>
                  <p>
                    Your information is loaded from your GROW8 account.
                  </p>
                </div>
                <div className="cs-section-icon">
                  <UserRound size={21} />
                </div>
              </div>

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
                <div className="creator-profile-loading">
                  Loading your profile...
                </div>
              ) : (
                <>
                  <div className="cs-profile-preview">
                    <div className="cs-profile-avatar">
                      {initials}
                    </div>

                    <div>
                      <strong>{creator.name || "Creator"}</strong>
                      <span>{creator.email || "No email available"}</span>
                      <small>
                        <ShieldCheck size={13} /> Creator account
                      </small>
                    </div>
                  </div>

                  <form onSubmit={handleProfileSave}>
                    <div className="cs-form-grid">
                      <div className="cs-field">
                        <label htmlFor="cs-name">Full Name</label>
                        <div className="cs-input-wrap">
                          <UserRound size={16} />
                          <input
                            id="cs-name"
                            type="text"
                            value={editing ? name : creator.name}
                            onChange={(event) =>
                              setName(event.target.value)
                            }
                            placeholder="Your full name"
                            disabled={!editing || savingProfile}
                            required
                          />
                        </div>
                      </div>

                      <div className="cs-field">
                        <label htmlFor="cs-email">Email Address</label>
                        <div className="cs-input-wrap">
                          <Mail size={16} />
                          <input
                            id="cs-email"
                            type="email"
                            value={editing ? email : creator.email}
                            onChange={(event) =>
                              setEmail(event.target.value)
                            }
                            placeholder="Your email address"
                            disabled={!editing || savingProfile}
                            required
                          />
                        </div>
                      </div>
                    </div>

                    <div className="cs-actions">
                      {!editing ? (
                        <button
                          type="button"
                          className="cs-save-button"
                          onClick={() => {
                            setName(creator.name);
                            setEmail(creator.email);
                            setEditing(true);
                            setProfileError("");
                            setProfileSuccess("");
                          }}
                        >
                          <Pencil size={16} /> Edit Profile
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="cs-secondary-button"
                            disabled={savingProfile}
                            onClick={() => {
                              setName(creator.name);
                              setEmail(creator.email);
                              setEditing(false);
                              setProfileError("");
                            }}
                          >
                            <X size={16} /> Cancel
                          </button>

                          <button
                            type="submit"
                            className="cs-save-button"
                            disabled={savingProfile}
                          >
                            <Save size={16} />
                            {savingProfile
                              ? "Saving..."
                              : "Save Changes"}
                          </button>
                        </>
                      )}
                    </div>
                  </form>
                </>
              )}
            </section>
          )}

          {activeTab === "security" && (
            <section className="cs-section">
              <div className="cs-section-heading">
                <div>
                  <h2>Account & Security</h2>
                  <p>
                    Manage your account password and security.
                  </p>
                </div>
                <div className="cs-section-icon">
                  <LockKeyhole size={21} />
                </div>
              </div>

              <div className="cs-security-notice">
                <ShieldCheck size={19} />
                <p>
                  Keep your GROW8 account secure with a strong,
                  unique password.
                </p>
              </div>

              <div className="cs-security-row">
                <div>
                  <strong>Password</strong>
                  <p>Change your account password.</p>
                </div>

                <button
                  type="button"
                  className="cs-save-button"
                  onClick={() => {
                    setPasswordModalOpen(true);
                    setPasswordError("");
                    setPasswordSuccess("");
                  }}
                >
                  <LockKeyhole size={16} />
                  Change Password
                </button>
              </div>
            </section>
          )}

          {activeTab === "notifications" && (
            <section className="cs-section">
              <div className="cs-section-heading">
                <div>
                  <h2>Notification Preferences</h2>
                  <p>
                    Choose which updates you want to receive.
                  </p>
                </div>
                <div className="cs-section-icon">
                  <Bell size={21} />
                </div>
              </div>

              <div className="cs-settings-group">
                <h3>Email Notifications</h3>
                <p className="cs-group-description">
                  Manage your email notification preferences.
                </p>

                {renderToggle(
                  notifications.emailUpdates,
                  () => updateNotification("emailUpdates"),
                  "Email Notifications",
                  "Receive important account updates through email."
                )}

                {renderToggle(
                  notifications.applicationUpdates,
                  () => updateNotification("applicationUpdates"),
                  "Application Updates",
                  "Get notified about new applications."
                )}

                {renderToggle(
                  notifications.contributorMessages,
                  () => updateNotification("contributorMessages"),
                  "Contributor Messages",
                  "Receive notifications about Contributor messages."
                )}

                {renderToggle(
                  notifications.feedbackNotifications,
                  () => updateNotification("feedbackNotifications"),
                  "Feedback & Reviews",
                  "Get updates about feedback received and submitted."
                )}

                {renderToggle(
                  notifications.announcements,
                  () => updateNotification("announcements"),
                  "Platform Announcements",
                  "Receive GROW8 news and announcements."
                )}
              </div>

              <div className="cs-actions">
                <button
                  type="button"
                  className="cs-save-button"
                  onClick={() => savePreferences("Notification")}
                >
                  <Save size={16} /> Save Preferences
                </button>
              </div>
            </section>
          )}

          {activeTab === "privacy" && (
            <section className="cs-section">
              <div className="cs-section-heading">
                <div>
                  <h2>Privacy Settings</h2>
                  <p>
                    Control how Contributors interact with your profile.
                  </p>
                </div>
                <div className="cs-section-icon">
                  <ShieldCheck size={21} />
                </div>
              </div>

              <div className="cs-settings-group">
                <h3>Profile Visibility</h3>
                <p className="cs-group-description">
                  Manage the visibility of your Creator profile.
                </p>

                {renderToggle(
                  privacy.publicProfile,
                  () => updatePrivacy("publicProfile"),
                  "Public Profile",
                  "Allow Contributors to view your profile."
                )}

                {renderToggle(
                  privacy.showOrganization,
                  () => updatePrivacy("showOrganization"),
                  "Show Organization Details",
                  "Display your organization information."
                )}

                {renderToggle(
                  privacy.allowMessages,
                  () => updatePrivacy("allowMessages"),
                  "Allow Messages",
                  "Allow Contributors to contact you through GROW8."
                )}
              </div>

              <div className="cs-actions">
                <button
                  type="button"
                  className="cs-save-button"
                  onClick={() => savePreferences("Privacy")}
                >
                  <Save size={16} /> Save Privacy Settings
                </button>
              </div>
            </section>
          )}
        </div>
      </div>

      {passwordModalOpen && (
        <div
          className="creator-password-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              if (!savingPassword) setPasswordModalOpen(false);
            }
          }}
        >
          <section
            className="creator-password-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cs-password-title"
          >
            <button
              type="button"
              className="creator-password-close"
              onClick={() => setPasswordModalOpen(false)}
              disabled={savingPassword}
              aria-label="Close"
            >
              <X size={20} />
            </button>

            <div className="creator-password-modal-icon">
              <LockKeyhole size={24} />
            </div>

            <h2 id="cs-password-title">Change Password</h2>

            <p className="creator-password-modal-description">
              Enter your current password and choose a new one.
            </p>

            <form onSubmit={handlePasswordChange}>
              {(
                [
                  ["current_password", "Current Password", "current"],
                  ["new_password", "New Password", "new"],
                  ["confirm_password", "Confirm New Password", "confirm"],
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
                        key === "current"
                          ? "current-password"
                          : "new-password"
                      }
                      required
                      disabled={savingPassword}
                    />

                    <button
                      type="button"
                      aria-label={
                        showPasswords[key]
                          ? `Hide ${label}`
                          : `Show ${label}`
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
                Use at least 8 characters and choose a password
                different from your current one.
              </p>

              {passwordError && (
                <div className="creator-profile-alert error">
                  {passwordError}
                </div>
              )}

              {passwordSuccess && (
                <div className="creator-profile-alert success">
                  {passwordSuccess}
                </div>
              )}

              <div className="creator-password-modal-actions">
                <button
                  type="button"
                  className="cs-secondary-button"
                  onClick={closePasswordModal}
                  disabled={savingPassword}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="cs-save-button"
                  disabled={savingPassword}
                >
                  {savingPassword
                    ? "Updating..."
                    : "Update Password"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
