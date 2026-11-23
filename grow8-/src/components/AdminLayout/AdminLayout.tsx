import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Flag,
  HomeIcon,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  Settings,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import RequireRole from "../RequireRole/RequireRole";
import "./AdminLayout.css";

const NAVIGATION = [
  { path: "/", label: "Home", icon: HomeIcon },
  { path: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { path: "/admin/feedback", label: "Feedback review", icon: MessageSquareText },
  { path: "/admin/reports", label: "Reports", icon: Flag },
  { path: "/admin/profile", label: "Profile", icon: UserRound },
  { path: "/admin/settings", label: "Settings", icon: Settings },
];

/** The admin area: only admins get past RequireRole. */
export default function AdminLayout() {
  const navigate = useNavigate();
  const [name, setName] = useState(localStorage.getItem("user_name") || "Admin");

  useEffect(() => {
    function handleNameChange() {
      setName(localStorage.getItem("user_name") || "Admin");
    }
    window.addEventListener("grow8:user-name-changed", handleNameChange);
    return () => window.removeEventListener("grow8:user-name-changed", handleNameChange);
  }, []);

  function signOut() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_name");
    navigate("/login");
  }

  return (
    <RequireRole role="admin">
      <div className="adm-app">
        <header className="adm-topbar">
          <Link to="/admin" className="adm-brand">
            <ShieldCheck size={22} /> Grow8 <span>Admin</span>
          </Link>
          <div className="adm-user">
            <span className="adm-avatar" aria-hidden="true">
              {name
                .split(/\s+/)
                .slice(0, 2)
                .map((part) => part[0]?.toUpperCase() ?? "")
                .join("")}
            </span>
            <span className="adm-user-name">
              <strong>{name}</strong>
              <small>Administrator</small>
            </span>
            <button type="button" className="adm-signout" onClick={signOut}>
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </header>

        <div className="adm-body">
          <aside className="adm-sidebar">
            <nav aria-label="Admin navigation">
              {NAVIGATION.map(({ path, label, icon: Icon, end }) => (
                <NavLink
                  key={path}
                  to={path}
                  end={end}
                  className={({ isActive }) => `adm-nav-link${isActive && path !== "/" ? " active" : ""}`}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </aside>
          <main className="adm-main">
            <Outlet />
          </main>
        </div>
      </div>
    </RequireRole>
  );
}
