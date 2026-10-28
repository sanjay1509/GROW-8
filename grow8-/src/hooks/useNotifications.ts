
import { useCallback, useEffect, useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export type AppNotification = {
  notification_id: number;
  notification_type: string;
  title: string;
  message: string;
  opportunity_id: number | null;
  read_at: string | null;
  is_read: boolean;
  created_at: string;
};

type NotificationResponse = {
  items: AppNotification[];
  total: number;
  limit: number;
  offset: number;
};

export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const loadNotifications = useCallback(async () => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setNotifications([]);
      setUnreadCount(0);
      setLoading(false);
      return;
    }

    try {
      const headers = {
        Authorization: `Bearer ${token}`,
      };

      const [listResponse, countResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/notifications?limit=20&offset=0`, {
          headers,
        }),
        fetch(`${API_BASE_URL}/notifications/unread-count`, {
          headers,
        }),
      ]);

      if (!listResponse.ok || !countResponse.ok) {
        throw new Error("Unable to load notifications.");
      }

      const listData = (await listResponse.json()) as NotificationResponse;
      const countData = (await countResponse.json()) as {
        unread_count: number;
      };

      setNotifications(listData.items ?? []);
      setUnreadCount(countData.unread_count ?? 0);
    } catch (error) {
      console.error("Could not load notifications:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const markAsRead = useCallback(
    async (notificationId: number) => {
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
      }
    },
    [loadNotifications]
  );

  const markAllAsRead = useCallback(async () => {
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
    }
  }, [loadNotifications]);

  useEffect(() => {
    void loadNotifications();

    const interval = window.setInterval(() => {
      void loadNotifications();
    }, 20000);

    return () => window.clearInterval(interval);
  }, [loadNotifications]);

  return {
    notifications,
    unreadCount,
    loading,
    refreshNotifications: loadNotifications,
    markAsRead,
    markAllAsRead,
  };
}
