
import React from "react";
import { Routes, Route } from "react-router-dom";

import HomePage from "./pages/HomePage/HomePage.jsx";
import BrowseOpportunities from "./pages/BrowseOpportunities/BrowseOpportunitites.jsx";
// import ContributorDashboard from "./pages/ContributorDashboard";
// import CreatorDashboard from "./pages/CreatorDashboard";

import "./App.css";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/opportunities"
        element={<BrowseOpportunities />}
      />

      <Route
        path="/contributor-dashboard"
        // element={<ContributorDashboard />}
      />

      <Route
        path="/creator-dashboard"
        // element={<CreatorDashboard />}
      />
    </Routes>
  );
}
