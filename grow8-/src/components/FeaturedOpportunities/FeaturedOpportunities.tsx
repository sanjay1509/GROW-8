
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

// Temporary sample data until the backend is connected
const sampleOpportunities = [
  {
    id: 1,
    title: "Social Media Support",
    organization: "Green Future NGO",
    location: "Calgary, AB",
    mode: "Remote",
    category: "Digital Support",
    hours: "5-10 hrs",
    icon: HeartHandshake,
    color: "blue",
  },
  {
    id: 2,
    title: "Event Volunteer Support",
    organization: "City Arts Festival",
    location: "Calgary, AB",
    mode: "On-site",
    category: "Community",
    hours: "8-12 hrs",
    icon: Building2,
    color: "orange",
  },
  {
    id: 3,
    title: "Data Entry and Organization",
    organization: "Local Business Inc.",
    location: "Calgary, AB",
    mode: "Remote",
    category: "Digital Support",
    hours: "5-10 hrs",
    icon: BriefcaseBusiness,
    color: "blue",
  },
];

// Select up to three random opportunities
function getRandomOpportunities(opportunities, count = 3) {
  const shuffled = [...opportunities];

  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }

  return shuffled.slice(0, count);
}

export default function FeaturedOpportunities({
  items,
  fetchFromBackend = false,
}) {
  const [featuredItems, setFeaturedItems] = useState(() =>
    getRandomOpportunities(items ?? sampleOpportunities)
  );

  const [loading, setLoading] = useState(fetchFromBackend);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!fetchFromBackend) {
      setFeaturedItems(getRandomOpportunities(items ?? sampleOpportunities));
      setLoading(false);
      return;
    }

    const controller = new AbortController();

    async function loadOpportunities() {
      try {
        setLoading(true);
        setError("");

        // Replace this URL with your actual backend endpoint.
        const response = await fetch(
          "/api/opportunities/featured",
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("Failed to load opportunities.");
        }

        const data = await response.json();

        setFeaturedItems(
          getRandomOpportunities(Array.isArray(data) ? data : [], 3)
        );
      } catch (err) {
        if (err.name !== "AbortError") {
          setError("Unable to load opportunities right now.");
          setFeaturedItems([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadOpportunities();

    return () => controller.abort();
  }, [items, fetchFromBackend]);

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
