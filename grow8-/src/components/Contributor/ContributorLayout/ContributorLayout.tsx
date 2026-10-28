
import { Outlet } from "react-router-dom";
import ContributorNavbar from "../ContributorNavbar/ContributorNavbar";
import ContributorSidebar from "../ContributorSidebar/ContributorSidebar";
import "./ContributorLayout.css";

export default function ContributorLayout() {
  return (
    <div className="contributor-app">
      <ContributorNavbar />

      <div className="contributor-app-body">
        <ContributorSidebar />

        <main className="contributor-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
