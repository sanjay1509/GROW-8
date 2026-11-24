import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { getMe } from "../../services/account";
import type { Me } from "../../services/account";

type Props = {
  role: Me["role"];
  children: ReactNode;
};

const HOME: Record<Me["role"], string> = {
  admin: "/admin",
  creator: "/creator/dashboard",
  contributor: "/contributor-dashboard",
};

/**
 * Shows its children only to a signed-in user with this role. Signed-out users go to
 * the sign-in page; users with another role go to their own area. The API still checks
 * the role on every request: this only keeps people out of screens they can't use.
 */
export default function RequireRole({ role, children }: Props) {
  const [me, setMe] = useState<Me | null>(null);
  const [failed, setFailed] = useState(false);
  const hasToken = Boolean(localStorage.getItem("access_token"));

  useEffect(() => {
    if (!hasToken) return;
    let active = true;
    getMe()
      .then((result) => {
        if (active) setMe(result);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [hasToken]);

  if (!hasToken || failed) {
    return <Navigate to="/login" replace />;
  }
  if (!me) {
    return <p style={{ padding: 24, color: "#6b778c" }}>Loading...</p>;
  }
  if (me.role !== role) {
    return <Navigate to={HOME[me.role]} replace />;
  }
  return <>{children}</>;
}
