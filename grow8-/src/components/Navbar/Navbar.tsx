
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ChevronDown,
  CircleUserRound,
  LayoutDashboard,
  LogOut,
  Settings,
} from "lucide-react";
import "./Navbar.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type NavbarUser = {
  name: string;
  email: string;
  role: string;
};

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);

  if (parts.length === 0) return "U";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function getUserDetails(data: unknown): NavbarUser | null {
  if (!data || typeof data !== "object") return null;

  const response = data as Record<string, unknown>;

  const nestedUser =
    response.user && typeof response.user === "object"
      ? (response.user as Record<string, unknown>)
      : response.data && typeof response.data === "object"
        ? (response.data as Record<string, unknown>)
        : response;

  const name =
    nestedUser.full_name ??
    nestedUser.name ??
    nestedUser.display_name ??
    nestedUser.username;

  return {
    name: typeof name === "string" ? name : "",
    email: typeof nestedUser.email === "string" ? nestedUser.email : "",
    role: typeof nestedUser.role === "string" ? nestedUser.role : "",
  };
}

export default function Navbar() {
  const [user, setUser] = useState<NavbarUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();

    async function loadUser() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setUser(null);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        });

        if (response.status === 401) {
          localStorage.removeItem("access_token");
          setUser(null);
          return;
        }

        if (!response.ok) {
          console.error("Unable to load signed-in user.");
          return;
        }

        const data: unknown = await response.json();
        setUser(getUserDetails(data));
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }

        console.error("Unable to load user profile:", error);
      }
    }

    void loadUser();

    return () => controller.abort();
  }, []);

  // Close the menu when the user clicks outside it.
  useEffect(() => {
    if (!menuOpen) return;

    function handleOutsideClick(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !menuRef.current?.contains(event.target)
      ) {
        setMenuOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    document.addEventListener("pointerdown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("pointerdown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [menuOpen]);

  const role = user?.role.toLowerCase();

  const dashboardPath =
    role === "admin"
      ? "/admin"
      : role === "creator"
        ? "/creator/dashboard"
        : "/contributor-dashboard";

  const profilePath =
    role === "admin"
      ? "/admin/profile"
      : role === "creator"
        ? "/creator/profile"
        : "/contributor-profile";

  const settingsPath =
    role === "admin"
      ? "/admin/settings"
      : role === "creator"
        ? "/creator/settings"
        : "/contributor-settings";

  const displayName = user?.name || user?.email || "My Account";

  function handleLogout() {
    localStorage.removeItem("access_token");
    setUser(null);
    setMenuOpen(false);
    navigate("/");
  }

  return (
    <header className="grow8-navbar">
      <Link to="/" className="grow8-brand">
        <span className="grow8-brand-icon">🌱</span>
        <span>Grow8</span>
      </Link>

      <nav className="grow8-nav-links">
        <Link to="/">Home</Link>
        <Link to="/opportunities">Opportunities</Link>
        <Link to="/about">About</Link>
        <Link to="/contact">Contact</Link>
      </nav>

      <div className="grow8-nav-actions">
        {!user ? (
          <>
            <Link to="/login" className="grow8-nav-button grow8-login">
              Login
            </Link>

            <Link to="/login" className="grow8-nav-button grow8-signup">
              Sign Up
            </Link>
          </>
        ) : (
          <div className="grow8-profile-menu" ref={menuRef}>
            <button
              type="button"
              className="grow8-profile-trigger"
              onClick={() => setMenuOpen((current) => !current)}
              aria-label="Open account menu"
              aria-expanded={menuOpen}
              aria-haspopup="menu"
            >
              <span className="grow8-profile-avatar">
                {getInitials(displayName)}
              </span>

              <span className="grow8-profile-label">
                <strong>{displayName}</strong>
                <span>
                  {role === "admin"
                    ? "Admin"
                    : role === "creator"
                      ? "Creator"
                      : "Contributor"}
                  <ChevronDown size={12} />
                </span>
              </span>
            </button>

            {menuOpen && (
              <div className="grow8-profile-dropdown" role="menu">
                <div className="grow8-dropdown-user">
                  <div className="grow8-dropdown-avatar">
                    {getInitials(displayName)}
                  </div>

                  <div className="grow8-dropdown-user-info">
                    <strong>{displayName}</strong>
                    <span>{user.email}</span>
                    <small>
                      {role
                        ? role.charAt(0).toUpperCase() + role.slice(1)
                        : "Member"}
                    </small>
                  </div>
                </div>

                <div className="grow8-dropdown-divider" />

                <Link
                  to={dashboardPath}
                  className="grow8-dropdown-item"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <LayoutDashboard size={18} />
                  Dashboard
                </Link>

                <Link
                  to={profilePath}
                  className="grow8-dropdown-item"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <CircleUserRound size={18} />
                  Profile
                </Link>

                <Link
                  to={settingsPath}
                  className="grow8-dropdown-item"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <Settings size={18} />
                  Settings
                </Link>

                <div className="grow8-dropdown-divider" />

                <button
                  type="button"
                  className="grow8-dropdown-item grow8-dropdown-logout"
                  role="menuitem"
                  onClick={handleLogout}
                >
                  <LogOut size={18} />
                  Logout
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
