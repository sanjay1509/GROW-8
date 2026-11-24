
import React from "react";
import { MapPin, Monitor, Clock3 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import "./OpportunityCard.css";

/** What the home page's featured cards show (built by FeaturedOpportunities). */
export interface CardOpportunity {
  id: number | string;
  title: string;
  organization: string;
  location: string;
  mode: string;
  category: string;
  hours: string;
  icon: LucideIcon;
  color?: string;
}

export default function OpportunityCard({ opportunity }: { opportunity: CardOpportunity }) {
  const {
    title,
    organization,
    location,
    mode,
    category,
    hours,
    icon: Icon,
    color = "blue",
  } = opportunity;

  return (
    <article className="grow8-opportunity-card">
      <div className={`grow8-opportunity-icon ${color}`}>
        <Icon size={23} strokeWidth={2.3} />
      </div>

      <div className="grow8-opportunity-content">
        <h3>{title}</h3>

        <p className="grow8-organization">
          {organization}
        </p>

        <div className="grow8-opportunity-meta">
          <span>
            <MapPin size={17} />
            {location}
          </span>

          <span>
            {mode === "Remote" ? (
              <Monitor size={17} />
            ) : (
              <Clock3 size={17} />
            )}
            {mode}
          </span>
        </div>

        <div className="grow8-opportunity-tags">
          <span
            className={`grow8-tag grow8-category ${
              category === "Community" ? "community" : ""
            }`}
          >
            {category}
          </span>

          <span className="grow8-tag grow8-hours">
            <MapPin size={13} />
            {hours}
          </span>
        </div>
      </div>
    </article>
  );
}
