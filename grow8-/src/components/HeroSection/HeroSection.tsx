
import React from "react";
import { Link } from "react-router-dom";
import SlideIn from "../SlideIn/SlideIn";
import "./HeroSection.css";
import heroTeam from "../../assets/hero-team.png";

export default function HeroSection() {
  return (
    <section className="grow8-hero">
      {/* Text slides in from the left */}
      <SlideIn direction="right" threshold={0.1}>
        <div className="grow8-hero-copy">
          <h1>
            Earn Experience.
            <br />
            Build Skills.
            <br />
            Support Communities.
          </h1>

          <p>
            Grow8 connects students and early-career workers with
            <br className="grow8-desktop-break" />
            short-term opportunities from local businesses, nonprofits,
            <br className="grow8-desktop-break" />
            and event organizers.
          </p>

          <div className="grow8-hero-actions">
            <Link to="/signup" className="grow8-hero-primary">
              Get Started
            </Link>

            <Link
              to="/opportunities"
              className="grow8-hero-secondary"
            >
              Explore Opportunities
            </Link>
          </div>
        </div>
      </SlideIn>

      {/* Image and decorations slide in from the right */}
      <SlideIn direction="left" threshold={0.1} delay={150}>
        <div className="grow8-hero-visual">
          <span className="grow8-decor grow8-decor-blue" />

          <img
            src={heroTeam}
            alt="Students collaborating around a laptop"
          />

          <span className="grow8-decor grow8-decor-yellow" />
          <span className="grow8-hero-dot grow8-hero-dot-blue" />
          <span className="grow8-hero-dot grow8-hero-dot-yellow" />
        </div>
      </SlideIn>
    </section>
  );
}
