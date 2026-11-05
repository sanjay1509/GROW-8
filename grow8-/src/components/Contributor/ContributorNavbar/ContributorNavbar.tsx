
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bell,
  CheckCheck,
  ChevronDown,
  CircleUserRound,
  Settings,
  Sprout,
  BriefcaseBusiness,
  LogOut,
  LoaderCircle,
  Check,
} from "lucide-react";

import "./ContributorNavbar.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const NOTIFICATION_REFRESH_MS = 100_000;

type ContributorUser = {
  name: string;
  email: string;
  role: string;
};

type AppNotification = {
  notification_id: number | string;
  notification_type: string;
  title: string;
  message: string;
  opportunity_id: number | string | null;
  read_at: string | null;
  created_at: string;
  is_read: boolean;
};

type NotificationResponse = {
  items?: unknown[];
  notifications?: unknown[];
  results?: unknown[];
  data?: unknown[] | {
    items?: unknown[];
    notifications?: unknown[];
    results?: unknown[];
  };
};

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);

  if (parts.length === 0) return "C";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function getUserDetails(data: unknown): ContributorUser | null {
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

  return {
    name: typeof nameValue === "string" ? nameValue : "",
    email: typeof nestedUser.email === "string" ? nestedUser.email : "",
    role: typeof nestedUser.role === "string" ? nestedUser.role : "",
  };
}

function getNotificationItems(data: unknown): AppNotification[] {
  if (Array.isArray(data)) {
    return data as AppNotification[];
  }

  if (!data || typeof data !== "object") {
    return [];
  }

  const response = data as NotificationResponse;

  if (Array.isArray(response.items)) {
    return response.items as AppNotification[];
  }

  if (Array.isArray(response.notifications)) {
    return response.notifications as AppNotification[];
  }

  if (Array.isArray(response.results)) {
    return response.results as AppNotification[];
  }

  if (Array.isArray(response.data)) {
    return response.data as AppNotification[];
  }

  if (response.data && typeof response.data === "object") {
    const nested = response.data;

    if (Array.isArray(nested.items)) {
      return nested.items as AppNotification[];
    }

    if (Array.isArray(nested.notifications)) {
      return nested.notifications as AppNotification[];
    }

    if (Array.isArray(nested.results)) {
      return nested.results as AppNotification[];
    }
  }

  return [];
}

function getUnreadCount(data: unknown): number {
  if (typeof data === "number") return Math.max(0, data);

  if (!data || typeof data !== "object") return 0;

  const response = data as Record<string, unknown>;
  const nested =
    response.data && typeof response.data === "object"
      ? (response.data as Record<string, unknown>)
      : response;

  const count =
    nested.unread_count ??
    nested.unreadCount ??
    nested.count ??
    nested.total;

  const parsed = typeof count === "number" ? count : Number(count);

  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
}

function formatNotificationTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  const difference = Math.max(0, Date.now() - date.getTime());

  if (difference < 60_000) return "Just now";

  if (difference < 3_600_000) {
    return `${Math.floor(difference / 60_000)}m ago`;
  }

  if (difference < 86_400_000) {
    return `${Math.floor(difference / 3_600_000)}h ago`;
  }

  if (difference < 604_800_000) {
    return `${Math.floor(difference / 86_400_000)}d ago`;
  }

  return date.toLocaleDateString();
}

function ContributorNavbarActions() {
  const [popover, setPopover] = useState<
    "notifications" | "account" | null
  >(null);

  const [contributor, setContributor] = useState<ContributorUser>({
    name: "",
    email: "",
    role: "contributor",
  });

  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const [notificationError, setNotificationError] = useState("");
  const [markingAllRead, setMarkingAllRead] = useState(false);
  const [markingIds, setMarkingIds] = useState<Array<number | string>>([]);

  const actionsRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const getAuthHeaders = useCallback((): HeadersInit | null => {
    const token = localStorage.getItem("access_token");

    if (!token) return null;

    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }, []);

  const loadNotifications = useCallback(
    async (signal?: AbortSignal, showLoading = false) => {
      const headers = getAuthHeaders();

      if (!headers) {
        setNotifications([]);
        setUnreadCount(0);
        setNotificationError("Please sign in to view notifications.");
        setLoadingNotifications(false);
        return;
      }

      if (showLoading) {
        setLoadingNotifications(true);
      }

      try {
        const notificationResponse = await fetch(
          `${API_BASE_URL}/notifications?limit=20&offset=0`,
          {
            method: "GET",
            headers,
            signal,
          }
        );

        if (!notificationResponse.ok) {
          const errorText = await notificationResponse.text();

          throw new Error(
            `Notifications API: HTTP ${notificationResponse.status} - ${
              errorText || notificationResponse.statusText
            }`
          );
        }

        const notificationData: unknown =
          await notificationResponse.json();

        const countResponse = await fetch(
          `${API_BASE_URL}/notifications/unread-count`,
          {
            method: "GET",
            headers,
            signal,
          }
        );

        if (!countResponse.ok) {
          const errorText = await countResponse.text();

          throw new Error(
            `Unread count API: HTTP ${countResponse.status} - ${
              errorText || countResponse.statusText
            }`
          );
        }

        const countData: unknown = await countResponse.json();

        if (signal?.aborted) return;

        setNotifications(getNotificationItems(notificationData));
        setUnreadCount(getUnreadCount(countData));
        setNotificationError("");
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "An unexpected error occurred.";

        console.error("Could not load contributor notifications:", message);
        setNotificationError(message);
      } finally {
        if (!signal?.aborted && showLoading) {
          setLoadingNotifications(false);
        }
      }
    },
    [getAuthHeaders]
  );

  // Load the signed-in contributor's profile.
  useEffect(() => {
    const controller = new AbortController();

    async function loadContributor() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setContributor({
          name: "",
          email: "",
          role: "contributor",
        });
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
          throw new Error(
            `Unable to load contributor profile: HTTP ${response.status}`
          );
        }

        const result: unknown = await response.json();
        const user = getUserDetails(result);

        if (user) {
          setContributor(user);
        }
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;

        console.error("Could not load contributor profile:", error);
      }
    }

    void loadContributor();

    return () => controller.abort();
  }, []);

  // Load notifications on mount and refresh them every 20 seconds.
  useEffect(() => {
    const controller = new AbortController();

    void loadNotifications(controller.signal, true);

    const intervalId = window.setInterval(() => {
      void loadNotifications(undefined, false);
    }, NOTIFICATION_REFRESH_MS);

    return () => {
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, [loadNotifications]);

  // Close popovers on outside click or Escape.
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
                ? "contributor-notifications"
                : "contributor-account-menu"
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

  function togglePopover(kind: "notifications" | "account") {
    setPopover((current) => (current === kind ? null : kind));

    if (kind === "notifications") {
      void loadNotifications(undefined, true);
    }
  }

  function closePopover() {
    setPopover(null);
  }

  async function markAsRead(notification: AppNotification) {
    if (notification.is_read) return;

    const headers = getAuthHeaders();
    if (!headers) return;

    setMarkingIds((current) =>
      current.includes(notification.notification_id)
        ? current
        : [...current, notification.notification_id]
    );

    try {
      const response = await fetch(
        `${API_BASE_URL}/notifications/${notification.notification_id}/read`,
        {
          method: "PATCH",
          headers,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
          `Mark as read failed: HTTP ${response.status} - ${
            errorText || response.statusText
          }`
        );
      }

      setNotifications((current) =>
        current.map((item) =>
          item.notification_id === notification.notification_id
            ? {
                ...item,
                is_read: true,
                read_at: new Date().toISOString(),
              }
            : item
        )
      );

      setUnreadCount((current) => Math.max(0, current - 1));
      setNotificationError("");
    } catch (error) {
      console.error("Could not mark notification as read:", error);

      setNotificationError(
        error instanceof Error
          ? error.message
          : "Could not mark the notification as read."
      );
    } finally {
      setMarkingIds((current) =>
        current.filter((id) => id !== notification.notification_id)
      );
    }
  }

  async function markAllAsRead() {
    const headers = getAuthHeaders();

    if (!headers || unreadCount === 0 || markingAllRead) return;

    setMarkingAllRead(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/notifications/read-all`,
        {
          method: "POST",
          headers,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();

        throw new Error(
          `Mark all as read failed: HTTP ${response.status} - ${
            errorText || response.statusText
          }`
        );
      }

      const now = new Date().toISOString();

      setNotifications((current) =>
        current.map((item) =>
          item.is_read
            ? item
            : { ...item, is_read: true, read_at: now }
        )
      );

      setUnreadCount(0);
      setNotificationError("");
    } catch (error) {
      console.error("Could not mark all notifications as read:", error);

      setNotificationError(
        error instanceof Error
          ? error.message
          : "Could not mark all notifications as read."
      );
    } finally {
      setMarkingAllRead(false);
    }
  }

  function openNotification(notification: AppNotification) {
    void markAsRead(notification);
    setPopover(null);

    if (notification.opportunity_id !== null) {
      // Change this path if your application uses a different detail route.
      navigate(`/contributor/opportunities/${notification.opportunity_id}`);
    } else {
      navigate("/contributor/opportunities");
    }
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_name");
    setPopover(null);
    window.location.assign("/");
  }

  const displayName = contributor.name || "Contributor";
  const initials = getInitials(displayName);

  return (
    <div className="contributor-topbar-actions" ref={actionsRef}>
      {/* Notifications button */}
      <button
        type="button"
        className="contributor-header-button"
        aria-label={
          unreadCount > 0
            ? `Notifications: ${unreadCount} unread`
            : "Notifications"
        }
        aria-expanded={popover === "notifications"}
        aria-controls="contributor-notifications"
        onClick={() => togglePopover("notifications")}
      >
        <Bell size={22} />

        {unreadCount > 0 && (
          <span className="contributor-notification-badge">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Notifications dropdown */}
      {popover === "notifications" && (
        <div
          className="contributor-popover contributor-notifications-popover"
          id="contributor-notifications"
        >
          <div className="contributor-notifications-header">
            <h2 className="contributor-popover-heading">Notifications</h2>

            {unreadCount > 0 && (
              <button
                type="button"
                className="contributor-mark-all-button"
                onClick={() => void markAllAsRead()}
                disabled={markingAllRead}
              >
                {markingAllRead ? (
                  <LoaderCircle
                    size={15}
                    className="contributor-spin"
                  />
                ) : (
                  <CheckCheck size={15} />
                )}
                Mark all read
              </button>
            )}
          </div>

          {loadingNotifications && notifications.length === 0 ? (
            <div className="contributor-notification-status">
              <LoaderCircle
                size={20}
                className="contributor-spin"
              />
              <span>Loading notifications...</span>
            </div>
          ) : notificationError && notifications.length === 0 ? (
            <div className="contributor-notification-status contributor-notification-error">
              <span>{notificationError}</span>

              <button
                type="button"
                onClick={() => void loadNotifications(undefined, true)}
              >
                Retry
              </button>
            </div>
          ) : notifications.length === 0 ? (
            <p className="contributor-popover-item contributor-muted">
              You're all caught up.
            </p>
          ) : (
            <div className="contributor-notification-list">
              {notifications.map((notification) => (
                <div
                  key={notification.notification_id}
                  className={`contributor-notification-row ${
                    notification.is_read ? "is-read" : "is-unread"
                  }`}
                >
                  <button
                    type="button"
                    className="contributor-notification-open"
                    onClick={() => openNotification(notification)}
                  >
                    <span className="contributor-notification-icon">
                      <BriefcaseBusiness size={18} />
                    </span>

                    <span className="contributor-notification-content">
                      <strong>{notification.title}</strong>
                      <span>{notification.message}</span>
                      <small>
                        {formatNotificationTime(notification.created_at)}
                      </small>
                    </span>

                    {!notification.is_read && (
                      <span className="contributor-unread-indicator" />
                    )}
                  </button>

                  {!notification.is_read && (
                    <button
                      type="button"
                      className="contributor-mark-read-button"
                      aria-label={`Mark "${notification.title}" as read`}
                      title="Mark as read"
                      disabled={markingIds.includes(
                        notification.notification_id
                      )}
                      onClick={() => void markAsRead(notification)}
                    >
                      {markingIds.includes(
                        notification.notification_id
                      ) ? (
                        <LoaderCircle
                          size={15}
                          className="contributor-spin"
                        />
                      ) : (
                        <Check size={15} />
                      )}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {notificationError && notifications.length > 0 && (
            <p className="contributor-notification-inline-error">
              {notificationError}
            </p>
          )}

          <button
            type="button"
            className="contributor-view-all-notifications"
            onClick={() => {
              setPopover(null);
              navigate("/contributor/notifications");
            }}
          >
            View all notifications
            <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* Account button */}
      <button
        type="button"
        className="contributor-account"
        aria-expanded={popover === "account"}
        aria-controls="contributor-account-menu"
        onClick={() => togglePopover("account")}
      >
        <span className="contributor-avatar">{initials}</span>

        <span className="contributor-account-label">
          <strong>{displayName}</strong>
          <span>
            Contributor <ChevronDown size={12} />
          </span>
        </span>
      </button>

      {/* Account dropdown */}
      {popover === "account" && (
        <div
          className="contributor-popover contributor-account-popover"
          id="contributor-account-menu"
        >
          <p className="contributor-popover-heading">Your workspace</p>

          <Link
            className="contributor-popover-item"
            to="/contributor/profile"
            onClick={closePopover}
          >
            <CircleUserRound size={18} />
            My Profile
          </Link>

          <Link
            className="contributor-popover-item"
            to="/contributor/settings"
            onClick={closePopover}
          >
            <Settings size={18} />
            Settings
          </Link>

          <div className="contributor-popover-divider" />

          <button
            type="button"
            className="contributor-popover-item contributor-logout-button"
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

export default function ContributorNavbar() {
  const location = useLocation();
  const navigate = useNavigate();

  function switchToCreator() {
    navigate("/creator/dashboard");
  }

  return (
    <header className="contributor-topbar">
      <Link
        className="contributor-brand"
        to="/"
        aria-label="Grow8 home"
      >
        <Sprout
          className="contributor-brand-mark"
          size={33}
          strokeWidth={2.1}
        />
        <span>Grow8</span>
      </Link>

      <div className="contributor-navbar-right">
        <button
          type="button"
          className="contributor-workspace-switch"
          onClick={switchToCreator}
        >
          <BriefcaseBusiness size={18} />
          <span>Switch to Creator</span>
        </button>

        <ContributorNavbarActions key={location.key} />
      </div>
    </header>
  );
}
