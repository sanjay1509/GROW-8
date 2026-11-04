import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ArrowRight,
  Bell,
  ChevronDown,
  CircleUserRound,
  Settings,
  Sprout,
  UsersRound,
} from "lucide-react";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import { creatorProfile } from "../../data/creatorDashboardData";
import "./CreatorNavbar.css";

function CreatorNavbarActions() {
  // TODO API: Replace creatorProfile with authenticated creator/organization details.
  const { applications } = useCreatorWorkspace();
  const [popover, setPopover] = useState<"notifications" | "account" | null>(null);
  const actionsRef = useRef<HTMLDivElement>(null);
  const pendingCount = applications.filter(
    (application) => application.status === "Under Review",
  ).length;
  const showApplicationNotifications = pendingCount > 0;

  useEffect(() => {
    if (!popover) return;

    function dismiss(event: PointerEvent) {
      if (event.target instanceof Node && !actionsRef.current?.contains(event.target)) {
        setPopover(null);
      }
    }

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPopover(null);
        actionsRef.current?.querySelector<HTMLButtonElement>(
          `[aria-controls="${popover === "notifications" ? "creator-notifications" : "creator-account-menu"}"]`,
        )?.focus();
      }
    }

    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", onKey);
    };
  }, [popover]);

  function closePopover() {
    setPopover(null);
  }

  function togglePopover(kind: "notifications" | "account") {
    setPopover(popover === kind ? null : kind);
  }

  return (
      <div className="creator-topbar-actions" ref={actionsRef}>
        <button
          type="button"
          className="creator-header-button"
          aria-label={showApplicationNotifications
            ? `Notifications: ${pendingCount} applications under review`
            : "Notifications: no new updates"}
          aria-expanded={popover === "notifications"}
          aria-controls="creator-notifications"
          onClick={() => togglePopover("notifications")}
        >
          <Bell size={22} />
          {showApplicationNotifications && <span className="creator-notification-dot" />}
        </button>

        <button
          type="button"
          className="creator-account"
          aria-expanded={popover === "account"}
          aria-controls="creator-account-menu"
          onClick={() => togglePopover("account")}
        >
          <span className="creator-avatar">{creatorProfile.initials}</span>
          <span className="creator-account-label">
            <strong>{creatorProfile.name}</strong>
            <span>Creator <ChevronDown size={12} /></span>
          </span>
        </button>

        {popover === "notifications" && (
          <div className="creator-popover" id="creator-notifications">
            <h2 className="creator-popover-heading">Notifications</h2>
            {showApplicationNotifications ? (
              <Link
                className="creator-popover-item"
                to="/creator/applications"
                onClick={closePopover}
              >
                <UsersRound size={20} />
                <span>
                  <strong>{pendingCount} applications under review</strong>
                  <span>Find your next great contributor.</span>
                </span>
                <ArrowRight size={16} />
              </Link>
            ) : (
              <p className="creator-popover-item creator-muted">You’re all caught up.</p>
            )}
          </div>
        )}

        {popover === "account" && (
          <div className="creator-popover" id="creator-account-menu">
            <p className="creator-popover-heading">Your workspace</p>
            <Link
              className="creator-popover-item"
              to="/creator/profile"
              onClick={closePopover}
            >
              <CircleUserRound size={18} />Organization profile
            </Link>
            <Link
              className="creator-popover-item"
              to="/creator/settings"
              onClick={closePopover}
            >
              <Settings size={18} />Notification preferences
            </Link>
          </div>
        )}
      </div>
  );
}

export default function CreatorNavbar() {
  const location = useLocation();

  return (
    <header className="creator-topbar">
      <Link className="creator-brand" to="/" aria-label="Grow8 home">
        <Sprout className="creator-brand-mark" size={33} strokeWidth={2.1} />
        <span>Grow8</span>
      </Link>
      <CreatorNavbarActions key={location.key} />
    </header>
  );
}
