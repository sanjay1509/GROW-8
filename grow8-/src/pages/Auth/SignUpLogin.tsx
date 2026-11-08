
import { useState, type FormEvent } from "react";
import {
  Leaf,
  Users,
  Landmark,
  Eye,
  EyeOff,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import "./SignUpLogin.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type UserRole = "contributor" | "creator";

type LoginResponse = {
  access_token?: string;
  role?: string;
  user?: {
    role?: string;
  };
  error?: {
    message?: string;
  };
  detail?: string;
  message?: string;
};

export default function SignUpLogin() {
  const navigate = useNavigate();

  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [role, setRole] = useState<UserRole>("contributor");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isAdminLogin, setIsAdminLogin] = useState(false);

  function switchMode(nextMode: "signup" | "login") {
    setMode(nextMode);
    setIsAdminLogin(false);
    setError("");
    setSuccess("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (mode === "signup") {
      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }

      setError(
        "Account registration is not connected yet. Please use an existing account to log in."
      );
      return;
    }

    if (!email.trim() || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const data: LoginResponse = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.error?.message ||
            data.detail ||
            data.message ||
            "Login failed. Please check your credentials."
        );
      }

      const token = data.access_token;

      if (!token) {
        throw new Error(
          "Login response did not include an access token. Check the API response."
        );
      }

      const currentRole = (
        data.user?.role || data.role || ""
      ).toLowerCase();

      if (isAdminLogin && currentRole !== "admin") {
        throw new Error(
          "This account does not have administrator access."
        );
      }

      if (
        !isAdminLogin &&
        currentRole &&
        currentRole !== role
      ) {
        throw new Error(
          `This account is registered as ${currentRole}. Please select the correct role.`
        );
      }

      // Store the token only after role checks pass.
      localStorage.setItem("access_token", token);

      setSuccess("Login successful! Redirecting...");

      window.setTimeout(() => {
        if (currentRole === "creator") {
          navigate("/creator/dashboard");
        } else if (currentRole === "admin") {
          navigate("/admin");
        } else {
          navigate("/");
        }
      }, 500);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while logging in."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleAdminLogin() {
    setMode("login");
    setIsAdminLogin(true);
    setError("");
    setSuccess("");
    setPassword("");
  }

  return (
    <main className="grow8-auth-page">
      <section className="grow8-auth-card">
        <div className="grow8-auth-form-panel">
          {/* Close button */}
          <button
            type="button"
            className="grow8-auth-close"
            onClick={() => navigate("/")}
            aria-label="Close login"
            title="Back to Home"
          >
            ×
          </button>

          {/* Brand */}
          <div className="grow8-auth-brand">
            <Leaf size={25} strokeWidth={2.5} />
            <span>Grow8</span>
          </div>

          {/* Heading */}
          <div className="grow8-auth-heading">
            <h1>
              {isAdminLogin
                ? "Administrator Login"
                : mode === "signup"
                  ? "Welcome to Grow8"
                  : "Welcome back"}
            </h1>

            <p>
              {isAdminLogin
                ? "Sign in with your administrator account"
                : mode === "signup"
                  ? "Create an account to get started"
                  : "Log in to continue making an impact"}
            </p>
          </div>

          {/* Only Contributor and Creator cards */}
          {!isAdminLogin && (
            <div
              className="grow8-role-grid"
              aria-label="Choose your role"
            >
              <button
                type="button"
                className={`grow8-role-card ${
                  role === "contributor" ? "selected" : ""
                }`}
                onClick={() => {
                  setRole("contributor");
                  setError("");
                }}
                aria-pressed={role === "contributor"}
              >
                <span className="grow8-role-icon contributor-icon">
                  <Users size={22} />
                </span>
                <strong>Contributor</strong>
                <small>Find opportunities</small>
              </button>

              <button
                type="button"
                className={`grow8-role-card ${
                  role === "creator" ? "selected" : ""
                }`}
                onClick={() => {
                  setRole("creator");
                  setError("");
                }}
                aria-pressed={role === "creator"}
              >
                <span className="grow8-role-icon creator-icon">
                  <Landmark size={22} />
                </span>
                <strong>Creator</strong>
                <small>Post opportunities</small>
              </button>
            </div>
          )}

          {/* Login / Signup form */}
          <form
            className="grow8-auth-form"
            onSubmit={handleSubmit}
          >
            {mode === "signup" && !isAdminLogin && (
              <input
                type="text"
                placeholder="Full Name"
                aria-label="Full Name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                autoComplete="name"
                required
              />
            )}

            <input
              type="email"
              placeholder="Email"
              aria-label="Email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />

            <div className="grow8-password-field">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                aria-label="Password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={
                  mode === "signup" ? "new-password" : "current-password"
                }
                required
              />

              <button
                type="button"
                className="grow8-password-toggle"
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
                onClick={() =>
                  setShowPassword((visible) => !visible)
                }
              >
                {showPassword ? (
                  <EyeOff size={17} />
                ) : (
                  <Eye size={17} />
                )}
              </button>
            </div>

            {mode === "signup" && !isAdminLogin && (
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Confirm Password"
                aria-label="Confirm Password"
                value={confirmPassword}
                onChange={(event) =>
                  setConfirmPassword(event.target.value)
                }
                autoComplete="new-password"
                required
              />
            )}

            {error && (
              <p className="grow8-auth-message error" role="alert">
                {error}
              </p>
            )}

            {success && (
              <p
                className="grow8-auth-message success"
                role="status"
              >
                {success}
              </p>
            )}

            <button
              type="submit"
              className="grow8-auth-submit"
              disabled={loading}
            >
              {loading
                ? "Please wait..."
                : mode === "signup" && !isAdminLogin
                  ? "Sign Up"
                  : isAdminLogin
                    ? "Login as Admin"
                    : "Login"}
            </button>
          </form>

          {/* Admin login entry point */}
          {!isAdminLogin && (
            <button
              type="button"
              className="grow8-admin-login"
              onClick={handleAdminLogin}
              disabled={loading}
            >
              Login as Admin
            </button>
          )}

          {/* Signup/login switch */}
          {!isAdminLogin ? (
            <p className="grow8-auth-switch">
              {mode === "signup"
                ? "Already have an account?"
                : "Don't have an account?"}{" "}
              <button
                type="button"
                onClick={() =>
                  switchMode(
                    mode === "signup" ? "login" : "signup"
                  )
                }
              >
                {mode === "signup" ? "Login" : "Sign Up"}
              </button>
            </p>
          ) : (
            <p className="grow8-auth-switch">
              Administrator access only.{" "}
              <button
                type="button"
                onClick={() => {
                  setIsAdminLogin(false);
                  setMode("login");
                  setError("");
                  setSuccess("");
                }}
              >
                Back to Login
              </button>
            </p>
          )}
        </div>

        {/* Right-side visual panel */}
        <aside className="grow8-auth-visual">
          <div className="grow8-visual-overlay" />

          <div className="grow8-visual-content">
            <span className="grow8-visual-tag">
              GROW TOGETHER
            </span>

            <h2>
              Opportunities
              <br />
              for a stronger
              <br />
              community
            </h2>

            <p>
              Connect. Contribute. Grow.
              <br />
              Be part of a platform that
              <br />
              creates real impact.
            </p>

            <div
              className="grow8-slide-indicators"
              aria-label="Slide 1 of 3"
            >
              <span className="active" />
              <span />
              <span />
              <span />
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
