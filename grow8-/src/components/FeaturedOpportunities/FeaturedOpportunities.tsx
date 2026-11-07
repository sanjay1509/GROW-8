
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  HeartHandshake,
  Building2,
  BriefcaseBusiness,
} from "lucide-react";

import OpportunityCard from "../OpportunityCard/OpportunityCard";
import "./FeaturedOpportunities.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

// Randomly select up to three unique opportunities.
function getRandomOpportunities(opportunities, count = 3) {
  const shuffled = [...opportunities];

  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }

  return shuffled.slice(0, count);
}

// Convert the backend response into the format used by OpportunityCard.
function normalizeOpportunity(opportunity) {
  const category =
    typeof opportunity.category === "object"
      ? opportunity.category?.name || opportunity.category?.code
      : opportunity.category;

  const organization =
    typeof opportunity.organization === "object"
      ? opportunity.organization?.name ||
        opportunity.organization?.organization_name
      : opportunity.organization;

  const mode = opportunity.work_mode || opportunity.mode || "Not specified";

  const hours =
    opportunity.expected_hours != null
      ? `${opportunity.expected_hours} hrs`
      : opportunity.hours || "Flexible";

  const categoryText = String(category || "Opportunity").toLowerCase();

  let icon = BriefcaseBusiness;
  let color = "blue";

  if (
    categoryText.includes("community") ||
    categoryText.includes("volunteer") ||
    categoryText.includes("social")
  ) {
    icon = HeartHandshake;
    color = "orange";
  } else if (
    categoryText.includes("business") ||
    categoryText.includes("organization") ||
    categoryText.includes("event")
  ) {
    icon = Building2;
    color = "blue";
  }

  return {
    ...opportunity,
    id: opportunity.opportunity_id ?? opportunity.id,
    title: opportunity.title || "Untitled Opportunity",
    organization:
      organization ||
      opportunity.organization_name ||
      opportunity.organization?.name ||
      "Organization",
    location: opportunity.location || "Location not specified",
    mode: String(mode)
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase()),
    category: category || "General",
    hours,
    icon,
    color,
  };
}

export default function FeaturedOpportunities() {
  const [featuredItems, setFeaturedItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadOpportunities() {
      try {
        setLoading(true);
        setError("");

        // Fetch real opportunities from the FastAPI backend.
        const response = await fetch(
          `${API_BASE_URL}/opportunities?limit=100`,
          {
            method: "GET",
            headers: {
              Accept: "application/json",
            },
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          throw new Error(
            `Failed to load opportunities (HTTP ${response.status}).`
          );
        }

        const data = await response.json();

        // FastAPI returns a paginated response with an "items" array.
        const opportunities = Array.isArray(data)
          ? data
          : Array.isArray(data?.items)
            ? data.items
            : [];

        // Exclude records without a usable ID or title.
        const validOpportunities = opportunities
          .filter(
            (item) =>
              item &&
              (item.opportunity_id != null || item.id != null) &&
              typeof item.title === "string" &&
              item.title.trim() !== ""
          )
          .map(normalizeOpportunity);

        // Randomize the results whenever this component loads.
        setFeaturedItems(getRandomOpportunities(validOpportunities, 3));
      } catch (err) {
        if (err.name !== "AbortError") {
          console.error("Error loading featured opportunities:", err);
          setError("Unable to load opportunities right now.");
          setFeaturedItems([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadOpportunities();

    return () => controller.abort();
  }, []);

  return (
    <section className="grow8-featured" id="opportunities">
      <div className="grow8-featured-heading">
        <h2>Featured Opportunities</h2>

        <Link to="/opportunities">
          View All <ArrowRight size={16} />
        </Link>
      </div>

      {loading ? (
        <p>Loading opportunities...</p>
      ) : error ? (
        <p role="alert">{error}</p>
      ) : featuredItems.length > 0 ? (
        <div className="grow8-featured-grid">
          {featuredItems.map((opportunity) => (
            <OpportunityCard
              key={opportunity.id}
              opportunity={opportunity}
            />
          ))}
        </div>
      ) : (
        <p>No opportunities are available right now.</p>
      )}
    </section>
  );
}
