import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { Outlet } from "react-router-dom";
import CreatorNavbar from "../CreatorNavbar/CreatorNavbar";
import CreatorSidebar from "../CreatorSidebar/CreatorSidebar";
import { CreatorWorkspaceContext } from "../../context/CreatorWorkspaceContext";
import {
  fetchAllReceivedApplications,
  fetchMyOpportunities,
  friendlyError,
  toDashboardApplication,
  toDashboardOpportunity,
} from "../../services/creatorWorkspace";
import type { CreatorOpportunity as ApiOpportunity } from "../../services/creatorWorkspace";
import type { Application as ApiApplication } from "../../services/applications";
import { getReceivedSubmissions } from "../../services/submissions";
import type { Submission } from "../../services/submissions";
import "./CreatorLayout.css";

export default function CreatorLayout() {
  const location = useLocation();
  const [apiOpportunities, setApiOpportunities] = useState<ApiOpportunity[]>([]);
  const [apiApplications, setApiApplications] = useState<ApiApplication[]>([]);
  const [approvedSubmissions, setApprovedSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // GET /opportunities/mine and GET /applications/received, shared by every creator page.
  const load = useCallback(async (isActive: () => boolean = () => true) => {
    setLoading(true);
    setError("");
    try {
      const [opportunities, applications, approved] = await Promise.all([
        fetchMyOpportunities(),
        fetchAllReceivedApplications(),
        getReceivedSubmissions({ status: ["awaiting", "approved", "rejected"], limit: 100 }),
      ]);
      if (isActive()) {
        setApiOpportunities(opportunities);
        setApiApplications(applications);
        setApprovedSubmissions(approved.items);
      }
    } catch (err) {
      if (isActive()) {
        setError(friendlyError(err, "Your workspace could not be loaded."));
      }
    } finally {
      if (isActive()) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let active = true;
    void load(() => active);
    return () => {
      active = false;
    };
  }, [load]);

  useEffect(() => {
    if (location.pathname === "/creator/dashboard") void load();
  }, [location.pathname, load]);

  // An organization rename shows on every opportunity, so reload after one.
  useEffect(() => {
    function handleOrganizationChange() {
      void load();
    }
    window.addEventListener("grow8:organization-changed", handleOrganizationChange);
    return () => window.removeEventListener("grow8:organization-changed", handleOrganizationChange);
  }, [load]);

  const workspace = useMemo(
    () => ({
      opportunities: apiOpportunities.map((item) => toDashboardOpportunity(item, apiApplications)),
      applications: apiApplications.map(toDashboardApplication),
      apiOpportunities,
      apiApplications,
      approvedSubmissions,
      creatorName:
        apiOpportunities[0]?.organization?.name ||
        localStorage.getItem("user_name") ||
        "Creator",
      loading,
      error,
      refresh: () => load(),
    }),
    [apiOpportunities, apiApplications, approvedSubmissions, loading, error, load]
  );

  return (
    <CreatorWorkspaceContext.Provider value={workspace}>
      <div className="creator-workspace">
        <a className="creator-skip-link" href="#creator-content">Skip to dashboard content</a>
        <CreatorNavbar />
        <div className="creator-shell">
          <CreatorSidebar />
          <main className="creator-main" id="creator-content">
            <Outlet />
          </main>
        </div>
      </div>
    </CreatorWorkspaceContext.Provider>
  );
}
