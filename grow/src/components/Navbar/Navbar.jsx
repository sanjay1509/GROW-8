
import React from "react";
import { Link } from "react-router-dom";
import "./Navbar.css";

export default function Navbar() {
  return (
    <header className="grow8-navbar">
      <Link to="/" className="grow8-brand">
        <span className="grow8-brand-icon">🌱</span>
        <span>Grow8</span>
      </Link>

      <nav className="grow8-nav-links">
        <Link to="/">Home</Link>
        <Link to="/opportunities">Opportunities</Link>
        <Link to="/about">About</Link>
        <Link to="/contact">Contact</Link>
      </nav>

      <div className="grow8-nav-actions">
        <Link to="/login" className="grow8-nav-button grow8-login">
          Login
        </Link>

        <Link to="/signup" className="grow8-nav-button grow8-signup">
          Sign Up
        </Link>
      </div>
    </header>
  );
}
