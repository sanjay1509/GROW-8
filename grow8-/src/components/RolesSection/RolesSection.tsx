
import React from "react";
import { useNavigate } from "react-router-dom";
import {
  BriefcaseBusiness,
  Building2,
} from "lucide-react";

import RoleCard from "../RoleCard/RoleCard";
import SlideIn from "../SlideIn/SlideIn";
import "./RolesSection.css";

export default function RolesSection() {
  const navigate = useNavigate();

  return (
    <section
      className="grow8-roles-section"
      id="about"
      aria-label="Grow8 roles"
    >
      {/* Contributor card */}
      <SlideIn direction="right" threshold={0.1} delay={150}>
        <button
          type="button"
          className="grow8-role-button"
          onClick={() => navigate("/contributor-dashboard")}
          aria-label="Open Contributor Dashboard"
        >
          <RoleCard
            icon={BriefcaseBusiness}
            title="For Contributors"
            description={
              <>
                Find opportunities, gain skills,
                <br />
                and get verified experience.
              </>
            }
            color="blue"
          />
        </button>
      </SlideIn>

      {/* Creator card */}
      <SlideIn direction="left" threshold={0.1} delay={150}>
        <button
          type="button"
          className="grow8-role-button"
          onClick={() => navigate("/creator/dashboard")}
          aria-label="Open Creator Dashboard"
        >
          <RoleCard
            icon={Building2}
            title="For Creators"
            description={
              <>
                Post opportunities and get
                <br />
                support for your organisation.
              </>
            }
            color="green"
          />
        </button>
      </SlideIn>
    </section>
  );
}
