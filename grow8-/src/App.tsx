
import { Navigate, Route, Routes } from "react-router-dom";

import HomePage from "./pages/HomePage/HomePage";
import AboutPage from "./pages/AboutPage/AboutPage";
import ContactPage from "./pages/AboutPage/ContactPage";
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
import CreatorSubmissions from "./pages/CreatorSubmissions/CreatorSubmissions";

// Admin components
import AdminLayout from "./components/AdminLayout/AdminLayout";
import AdminDashboard from "./pages/Admin/AdminDashboard";
import AdminFeedback from "./pages/Admin/AdminFeedback";
import AdminReports from "./pages/Admin/AdminReports";
import AdminAccount from "./pages/Admin/AdminAccount";


// Contributor components
import ContributorLayout from "./components/Contributor/ContributorLayout/ContributorLayout";
import ContributorDashboard from "./components/Contributor/ContributorDashboard/ContributorDashboard";
import ContributorApplications from "./pages/ContributorApplications/ContributorApplications";
import ContributorProfile from "./pages/ContributorProfile/ContributorProfile";
import ContributorSettings from "./pages/ContributorSettings/ContributorSettings";
import ContributorExperience from "./pages/ContributorActivity/ContributorExperience";
import ContributorFeedback from "./pages/ContributorActivity/ContributorFeedback";
import ContributorReports from "./pages/ContributorActivity/ContributorReports";
import ContributorSkills from "./pages/ContributorActivity/ContributorSkills";

import "./App.css";

export default function App() {
  return (
    <Routes>
      {/* Public pages */}
      <Route path="/" element={<HomePage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/contact" element={<ContactPage />} />
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

          <Route
            path="/contributor/experience"
            element={<ContributorExperience />}
          />

          <Route
            path="/contributor/skills"
            element={<ContributorSkills />}
          />

          <Route
            path="/contributor/feedback"
            element={<ContributorFeedback />}
          />

          <Route
            path="/contributor/reports"
            element={<ContributorReports />}
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
        <Route path="submissions" element={<CreatorSubmissions />} />
        <Route path="settings" element={<CreatorSettings/>} />

        <Route
          path="*"
          element={<Navigate to="/creator/dashboard" replace />}
        />
      </Route>

      
    {/* Admin pages (AdminLayout lets admins only) */}
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<AdminDashboard />} />
        <Route path="feedback" element={<AdminFeedback />} />
        <Route path="reports" element={<AdminReports />} />
        <Route path="profile" element={<AdminAccount section="profile" />} />
        <Route path="settings" element={<AdminAccount section="settings" />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Route>
    </Routes>
  );
}
