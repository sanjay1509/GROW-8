import { Navigate, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage/HomePage";
import BrowseOpportunities from "./pages/BrowseOpportunities/BrowseOpportunitites";
import CreatorLayout from "./components/CreatorLayout/CreatorLayout";
import CreatorDashboard from "./pages/CreatorDashboard/CreatorDashboard";
import "./App.css";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/opportunities" element={<BrowseOpportunities />} />
      <Route path="/contributor-dashboard" element={null} />

      <Route path="/creator" element={<CreatorLayout />}>
        <Route index element={<Navigate to="/creator/dashboard" replace />} />
        <Route path="dashboard" element={<CreatorDashboard />} />
        <Route path="opportunities" element={null} />
        <Route path="applications" element={null} />
        <Route path="submissions" element={null} />
        <Route path="feedback" element={null} />
        <Route path="profile" element={null} />
        <Route path="settings" element={null} />
        <Route path="*" element={<Navigate to="/creator/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
