
import { Routes, Route } from 'react-router-dom';

import HomePage from './pages/HomePage/HomePage';
import BrowseOpportunities from './pages/BrowseOpportunities/BrowseOpportunitites';

import './App.css';

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
        element={null}
      />

      <Route
        path="/creator-dashboard"
        element={null}
      />
    </Routes>
  );
}
