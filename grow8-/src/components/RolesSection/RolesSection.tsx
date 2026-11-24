
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BriefcaseBusiness,
  Building2,
  X,
} from "lucide-react";

import RoleCard from "../RoleCard/RoleCard";
import SlideIn from "../SlideIn/SlideIn";
import "./RolesSection.css";

type SelectedRole = "contributor" | "creator";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export default function RolesSection() {
  const navigate = useNavigate();
  const [selectedRole, setSelectedRole] = useState<SelectedRole | null>(null);
  const [checkingRole, setCheckingRole] = useState(false);

  async function chooseRole(targetRole: SelectedRole) {
    const token = localStorage.getItem("access_token");
    if (token) {
      setCheckingRole(true);
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          const user = data?.user ?? data?.data ?? data;
          const currentRole = String(user?.role ?? "").toLowerCase();
          if (currentRole === targetRole) {
            navigate(targetRole === "creator" ? "/creator/dashboard" : "/contributor-dashboard");
            return;
          }
        }
      } catch {
        // A failed role check falls through to the role-specific sign-in prompt.
      } finally {
        setCheckingRole(false);
      }
    }
    setSelectedRole(targetRole);
  }

  useEffect(() => {
    if (!selectedRole) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedRole(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedRole]);

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
          onClick={() => void chooseRole("contributor")}
          disabled={checkingRole}
          aria-label="Contributor sign in options"
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
          onClick={() => void chooseRole("creator")}
          disabled={checkingRole}
          aria-label="Creator sign in options"
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

      {selectedRole && (
        <div className="grow8-role-modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setSelectedRole(null);
        }}>
          <section className="grow8-role-modal" role="dialog" aria-modal="true" aria-labelledby="grow8-role-modal-title">
            <button type="button" className="grow8-role-modal-close" onClick={() => setSelectedRole(null)} aria-label="Close sign in prompt">
              <X size={18} />
            </button>
            <span className={`grow8-role-modal-icon ${selectedRole}`}>
              {selectedRole === "creator" ? <Building2 size={23} /> : <BriefcaseBusiness size={23} />}
            </span>
            <h2 id="grow8-role-modal-title">Continue as a {selectedRole === "creator" ? "Creator" : "Contributor"}</h2>
            <p>Sign in to open your {selectedRole === "creator" ? "creator" : "contributor"} workspace.</p>
            <button
              type="button"
              className="grow8-role-modal-login"
              onClick={() => navigate(`/login?role=${selectedRole}&mode=login`)}
            >
              Log in as a {selectedRole === "creator" ? "Creator" : "Contributor"}
            </button>
          </section>
        </div>
      )}
    </section>
  );
}
