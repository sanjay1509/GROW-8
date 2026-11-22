
import { Navigate, Route, Routes } from "react-router-dom";

import HomePage from "./pages/HomePage/HomePage";
import BrowseOpportunities from "./pages/BrowseOpportunities/BrowseOpportunitites";
import SignUpLogin from "./pages/Auth/SignUpLogin";

// Creator components
import CreatorLayout from "./components/CreatorLayout/CreatorLayout";
import CreatorDashboard from "./pages/CreatorDashboard/CreatorDashboard";
import CreatorOpportunity from "./pages/CreatorOpportunities/CreatorOpportunity";
import MyOpportunities from "./pages/CreatorOpportunities/MyOpportunities";
import CreatorProfile from "./pages/CreatorProfile/CreatorProfile";
import CreatorFeedback from "./pages/CreatorFeedback/CreatorFeedback";
import CreatorSettings from "./pages/CreatorSettings/CreatorSettings";
import CreatorApplications from "./pages/CreatorApplications/CreatorApplications";

// Contributor components
import ContributorLayout from "./components/Contributor/ContributorLayout/ContributorLayout";
import ContributorDashboard from "./components/Contributor/ContributorDashboard/ContributorDashboard";
import ContributorApplications from "./pages/ContributorApplications/ContributorApplications";
import ContributorProfile from "./pages/ContributorProfile/ContributorProfile";
import ContributorSettings from "./pages/ContributorSettings/ContributorSettings";

import "./App.css";

export default function App() {
  return (
    <Routes>
      {/* Public pages */}
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<SignUpLogin />} />
      <Route path="/opportunities" element={<BrowseOpportunities />} />

      {/* Contributor pages */}
        <Route element={<ContributorLayout />}>
          <Route
            path="/contributor-dashboard"
            element={<ContributorDashboard />}
          />

          <Route
            path="/contributor/applications"
            element={<ContributorApplications />}
          />

          <Route
            path="/contributor/profile"
            element={<ContributorProfile />}
          />

          <Route
            path="/contributor/settings"
            element={<ContributorSettings />}
          />
        </Route>

      {/* Creator pages */}
      <Route path="/creator" element={<CreatorLayout />}>
        <Route
          index
          element={<Navigate to="/creator/dashboard" replace />}
        />

        <Route path="dashboard" element={<CreatorDashboard />} />
        <Route path="profile" element={<CreatorProfile />} />
        <Route path="feedback" element={<CreatorFeedback />} />
        <Route
          path="opportunities/create"
          element={<CreatorOpportunity />}
        />

        <Route
          path="opportunities"
          element={<MyOpportunities />}
        />

        <Route path="applications" element={<CreatorApplications />} />

        {/* Creator pages not implemented yet */}
        <Route path="submissions" element={null} />
        <Route path="settings" element={<CreatorSettings/>} />

        <Route
          path="*"
          element={<Navigate to="/creator/dashboard" replace />}
        />
      </Route>
    </Routes>
  );
}
