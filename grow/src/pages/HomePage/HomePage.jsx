
import React from "react";

import Navbar from "../../components/Navbar/Navbar";
import HeroSection from "../../components/HeroSection/HeroSection";
import RolesSection from "../../components/RolesSection/RolesSection";
import FeaturedOpportunities from "../../components/FeaturedOpportunities/FeaturedOpportunities";
import AboutUs from "../../components/AboutUs/AboutUs";
import SlideIn from "../../components/SlideIn/SlideIn";
import BackToTop from "../../components/BackToTop/BackToTop";

import "./HomePage.css";

export default function HomePage() {
  return (
    <main className="grow8-page">
      <Navbar />

      <div className="grow8-page-content">
        <SlideIn direction="up" threshold={0} delay={100}>
          <HeroSection />
        </SlideIn>

        <RolesSection />

        <SlideIn direction="up" delay={100}>
          <FeaturedOpportunities />
        </SlideIn>

        <SlideIn direction="right">
          <AboutUs />
        </SlideIn>
      </div>

      <BackToTop />
    </main>
  );
}
