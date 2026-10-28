import { Outlet } from "react-router-dom";
import CreatorNavbar from "../CreatorNavbar/CreatorNavbar";
import CreatorSidebar from "../CreatorSidebar/CreatorSidebar";
import { CreatorWorkspaceContext } from "../../context/CreatorWorkspaceContext";
import { initialApplications, initialOpportunities } from "../../data/creatorDashboardData";
import "./CreatorLayout.css";

export default function CreatorLayout() {
  // TODO API: Fetch this creator's opportunities from GET /opportunities/mine.
  // TODO API: Fetch applications when the creator applications endpoint is available.
  return (
    <CreatorWorkspaceContext.Provider value={{
      opportunities: initialOpportunities,
      applications: initialApplications,
    }}>
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
