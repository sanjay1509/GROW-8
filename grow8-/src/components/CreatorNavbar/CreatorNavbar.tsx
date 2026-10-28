
import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bell,
  ChevronDown,
  CircleUserRound,
  Settings,
  Sprout,
  UsersRound,
  LogOut,
  CheckCheck,
  BriefcaseBusiness,
} from "lucide-react";
import { useCreatorWorkspace } from "../../context/CreatorWorkspaceContext";
import "./CreatorNavbar.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type CreatorUser = {
  name: string;
  email: string;
  role: string;
};

type AppNotification = {
  notification_id: number;
  notification_type: string;
  title: string;
  message: string;
  opportunity_id: number | null;
  read_at: string | null;
  is_read: boolean;
  created_at: string;
};

type NotificationListResponse = {
  items: AppNotification[];
  total: number;
  limit: number;
  offset: number;
};

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);

  if (parts.length === 0) return "C";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function getUserDetails(data: unknown): CreatorUser | null {
  if (!data || typeof data !== "object") return null;

  const response = data as Record<string, unknown>;

  const nestedUser =
    response.user && typeof response.user === "object"
      ? (response.user as Record<string, unknown>)
      : response.data && typeof response.data === "object"
        ? (response.data as Record<string, unknown>)
        : response;

  const nameValue =
    nestedUser.full_name ??
    nestedUser.name ??
    nestedUser.display_name ??
    nestedUser.username;

  const emailValue = nestedUser.email;
  const roleValue = nestedUser.role;

  return {
    name: typeof nameValue === "string" ? nameValue : "",
    email: typeof emailValue === "string" ? emailValue : "",
    role: typeof roleValue === "string" ? roleValue : "",
  };
}

function formatNotificationDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function CreatorNavbarActions() {
  const { applications } = useCreatorWorkspace();
  const navigate = useNavigate();

  const [popover, setPopover] = useState<
    "notifications" | "account" | null
  >(null);

  const [creator, setCreator] = useState<CreatorUser>({
    name: "",
    email: "",
    role: "creator",
  });

  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(true);
  const [notificationError, setNotificationError] = useState("");

  const actionsRef = useRef<HTMLDivElement>(null);

  const pendingCount = applications.filter(
    (application) => application.status === "Under Review"
  ).length;

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_name");
    setPopover(null);
    window.location.assign("/");
  }

  async function loadNotifications(signal?: AbortSignal) {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setNotifications([]);
      setUnreadCount(0);
      setNotificationsLoading(false);
      return;
    }

    try {
      const headers = {
        Authorization: `Bearer ${token}`,
      };

      const [listResponse, countResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/notifications?limit=20&offset=0`, {
          headers,
          signal,
        }),
        fetch(`${API_BASE_URL}/notifications/unread-count`, {
          headers,
          signal,
        }),
      ]);

      if (!listResponse.ok || !countResponse.ok) {
        throw new Error("Unable to load notifications.");
      }

      const listData =
        (await listResponse.json()) as NotificationListResponse;
      const countData = (await countResponse.json()) as {
        unread_count: number;
      };

      setNotifications(listData.items ?? []);
      setUnreadCount(countData.unread_count ?? 0);
      setNotificationError("");
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;

      console.error("Could not load creator notifications:", error);
      setNotificationError("Unable to load notifications. Please try again.");
    } finally {
      if (!signal?.aborted) {
        setNotificationsLoading(false);
      }
    }
  }

  async function markAsRead(notificationId: number) {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/notifications/${notificationId}/read`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Unable to mark notification as read.");
      }

      await loadNotifications();
    } catch (error) {
      console.error("Could not mark notification as read:", error);
      setNotificationError("Could not update this notification.");
    }
  }

  async function markAllAsRead() {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/notifications/read-all`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Unable to mark notifications as read.");
      }

      await loadNotifications();
    } catch (error) {
      console.error("Could not mark notifications as read:", error);
      setNotificationError("Could not mark all notifications as read.");
    }
  }

  useEffect(() => {
    const controller = new AbortController();

    async function loadCreator() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setCreator({ name: "", email: "", role: "creator" });
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Unable to load the signed-in user.");
        }

        const result: unknown = await response.json();
        const user = getUserDetails(result);

        if (user) {
          setCreator(user);
        }
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;

        console.error("Could not load creator profile:", error);
      }
    }

    void loadCreator();
    void loadNotifications(controller.signal);

    const interval = window.setInterval(() => {
      void loadNotifications(controller.signal);
    }, 20000);

    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!popover) return;

    function dismiss(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !actionsRef.current?.contains(event.target)
      ) {
        setPopover(null);
      }
    }

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPopover(null);

        actionsRef.current
          ?.querySelector<HTMLButtonElement>(
            `[aria-controls="${
              popover === "notifications"
                ? "creator-notifications"
                : "creator-account-menu"
            }"]`
          )
          ?.focus();
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
    setPopover((current) => (current === kind ? null : kind));

    if (kind === "notifications") {
      void loadNotifications();
    }
  }

  function openNotification(notification: AppNotification) {
    if (!notification.is_read) {
      void markAsRead(notification.notification_id);
    }

    closePopover();

    if (notification.opportunity_id) {
      navigate(`/creator/opportunities`);
    }
  }

  const displayName = creator.name || "Creator";
  const initials = getInitials(displayName);

  return (
    <div className="creator-topbar-actions" ref={actionsRef}>
      <button
        type="button"
        className="creator-header-button"
        aria-label={`Notifications: ${unreadCount} unread`}
        aria-expanded={popover === "notifications"}
        aria-controls="creator-notifications"
        onClick={() => togglePopover("notifications")}
      >
        <Bell size={22} />

        {unreadCount > 0 && (
          <span className="creator-notification-dot">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <button
        type="button"
        className="creator-account"
        aria-expanded={popover === "account"}
        aria-controls="creator-account-menu"
        onClick={() => togglePopover("account")}
      >
        <span className="creator-avatar">{initials}</span>

        <span className="creator-account-label">
          <strong>{displayName}</strong>
          <span>
            Creator <ChevronDown size={12} />
          </span>
        </span>
      </button>

      {popover === "notifications" && (
        <div className="creator-popover" id="creator-notifications">
          <div className="notification-popover-header">
            <h2 className="creator-popover-heading">Notifications</h2>

            {unreadCount > 0 && (
              <button
                type="button"
                className="notification-mark-all"
                onClick={() => void markAllAsRead()}
              >
                <CheckCheck size={14} />
                Mark all read
              </button>
            )}
          </div>

          {notificationError && (
            <p className="creator-popover-item" role="alert">
              {notificationError}
            </p>
          )}

          {notificationsLoading && notifications.length === 0 ? (
            <p className="creator-popover-item creator-muted">
              Loading notifications...
            </p>
          ) : notifications.length === 0 ? (
            <p className="creator-popover-item creator-muted">
              You’re all caught up.
            </p>
          ) : (
            <div className="notification-list">
              {notifications.map((notification) => (
                <button
                  key={notification.notification_id}
                  type="button"
                  className={`notification-item ${
                    notification.is_read ? "" : "notification-unread"
                  }`}
                  onClick={() => openNotification(notification)}
                >
                  <span className="notification-item-icon">
                    <BriefcaseBusiness size={17} />
                  </span>

                  <span className="notification-item-content">
                    <strong>{notification.title}</strong>
                    <span>{notification.message}</span>
                    <small>
                      {formatNotificationDate(notification.created_at)}
                    </small>
                  </span>

                  {!notification.is_read && (
                    <span className="notification-unread-indicator" />
                  )}
                </button>
              ))}
            </div>
          )}

          {pendingCount > 0 && (
            <Link
              className="creator-popover-item creator-application-notice"
              to="/creator/applications"
              onClick={closePopover}
            >
              <UsersRound size={19} />
              <span>
                <strong>{pendingCount} applications under review</strong>
                <span>Review your applicants.</span>
              </span>
              <ArrowRight size={16} />
            </Link>
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
            <CircleUserRound size={18} />
            Organization profile
          </Link>

          <Link
            className="creator-popover-item"
            to="/creator/settings"
            onClick={closePopover}
          >
            <Settings size={18} />
            Notification preferences
          </Link>

          <div className="creator-popover-divider" />

          <button
            type="button"
            className="creator-popover-item creator-logout-button"
            onClick={handleLogout}
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      )}
    </div>
  );
}

export default function CreatorNavbar() {
  const location = useLocation();
  const navigate = useNavigate();

  function switchToContributor() {
    navigate("/contributor-dashboard");
  }

  return (
    <header className="creator-topbar">
      <Link className="creator-brand" to="/" aria-label="Grow8 home">
        <Sprout
          className="creator-brand-mark"
          size={33}
          strokeWidth={2.1}
        />
        <span>Grow8</span>
      </Link>

      <div className="creator-navbar-right">
        <button
          type="button"
          className="creator-workspace-switch"
          onClick={switchToContributor}
        >
          <UsersRound size={18} />
          <span>Switch to Contributor</span>
        </button>

        <CreatorNavbarActions key={location.key} />
      </div>
    </header>
  );
}
