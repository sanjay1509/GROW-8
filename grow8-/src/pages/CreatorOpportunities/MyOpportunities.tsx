
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Plus,
  BriefcaseBusiness,
  MapPin,
  Clock,
  CalendarDays,
  RefreshCw,
  Eye,
} from "lucide-react";
import "./MyOpportunities.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type Opportunity = {
  opportunity_id: number;
  title: string;
  description: string;
  status: string;
  category?: { code: string; name: string };
  location?: string | null;
  work_mode?: string;
  expected_hours?: number | null;
  application_deadline?: string | null;
  compensation_type?: string;
  compensation_amount?: number | null;
};

function formatDate(value?: string | null) {
  if (!value) return "No deadline";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "No deadline"
    : date.toLocaleDateString("en-CA", {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      });
}

function statusLabel(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (c) =>
    c.toUpperCase()
  );
}

export default function MyOpportunities() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");

  async function loadOpportunities() {
    setLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        throw new Error(
          "Please sign in as a creator before viewing your opportunities."
        );
      }

      const response = await fetch(
        `${API_BASE_URL}/opportunities/mine`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const data: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          `Unable to load opportunities (HTTP ${response.status}).`
        );
      }

      const rows = Array.isArray(data)
        ? data
        : data &&
            typeof data === "object" &&
            "items" in data &&
            Array.isArray(data.items)
          ? data.items
          : [];

      setItems(rows as Opportunity[]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while loading opportunities."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOpportunities();
  }, []);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const matchesSearch =
        `${item.title} ${item.description} ${item.category?.name ?? ""}`
          .toLowerCase()
          .includes(search.toLowerCase());

      const matchesStatus =
        status === "all" ||
        item.status.toLowerCase() === status.toLowerCase();

      return matchesSearch && matchesStatus;
    });
  }, [items, search, status]);

  return (
    <section className="my-opportunities-page">
      <header className="mo-header">
        <div>
          <span className="mo-eyebrow">CREATOR WORKSPACE</span>
          <h1>My Opportunities</h1>
          <p>Manage the opportunities your organization has created.</p>
        </div>

        <Link
          className="mo-create-button"
          to="/creator/opportunities/create"
        >
          <Plus size={18} /> Create Opportunity
        </Link>
      </header>

      <div className="mo-toolbar">
        <label className="mo-search">
          <Search size={18} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search opportunities..."
            aria-label="Search opportunities"
          />
        </label>

        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          aria-label="Filter by status"
          className="mo-status-filter"
        >
          <option value="all">All statuses</option>
          <option value="open">Open</option>
          <option value="draft">Draft</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="closed">Closed</option>
        </select>

        <button
          className="mo-refresh-button"
          onClick={() => void loadOpportunities()}
          disabled={loading}
          type="button"
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {!loading && !error && (
        <div className="mo-result-count">
          Showing {filtered.length} of {items.length} opportunities
        </div>
      )}

      {loading && (
        <div className="mo-state">
          <RefreshCw size={24} className="mo-spin" />
          <p>Loading your opportunities...</p>
        </div>
      )}

      {!loading && error && (
        <div className="mo-error" role="alert">
          <strong>Unable to load opportunities</strong>
          <p>{error}</p>
          <button type="button" onClick={() => void loadOpportunities()}>
            Try again
          </button>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="mo-empty">
          <span className="mo-empty-icon">
            <BriefcaseBusiness size={30} />
          </span>
          <h2>{items.length ? "No matching opportunities" : "No opportunities yet"}</h2>
          <p>
            {items.length
              ? "Try another search term or status filter."
              : "Create your first opportunity to start connecting with contributors."}
          </p>
          {items.length === 0 && (
            <Link
              className="mo-create-button"
              to="/creator/opportunities/create"
            >
              <Plus size={18} /> Create your first opportunity
            </Link>
          )}
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="mo-grid">
          {filtered.map((item) => (
            <article className="mo-card" key={item.opportunity_id}>
              <div className="mo-card-top">
                <span className="mo-card-icon">
                  <BriefcaseBusiness size={22} />
                </span>
                <span
                  className={`mo-badge mo-status-${item.status.toLowerCase().replaceAll("_", "-")}`}
                >
                  {statusLabel(item.status)}
                </span>
              </div>

              <span className="mo-category">
                {item.category?.name ?? "Opportunity"}
              </span>

              <h2>{item.title}</h2>
              <p className="mo-description">{item.description}</p>

              <div className="mo-metadata">
                <span>
                  <MapPin size={16} />
                  {item.location || item.work_mode?.replaceAll("_", " ") || "Location not specified"}
                </span>
                <span>
                  <Clock size={16} />
                  {item.expected_hours != null
                    ? `${item.expected_hours} expected hours`
                    : "Hours not specified"}
                </span>
                <span>
                  <CalendarDays size={16} />
                  Deadline: {formatDate(item.application_deadline)}
                </span>
              </div>

              <div className="mo-card-footer">
                <span className="mo-compensation">
                  {item.compensation_type === "stipend" &&
                  item.compensation_amount != null
                    ? `$${item.compensation_amount} stipend`
                    : item.compensation_type === "paid" &&
                        item.compensation_amount != null
                      ? `$${item.compensation_amount} paid`
                      : item.compensation_type === "unpaid"
                        ? "Volunteer / Unpaid"
                        : item.compensation_type
                          ? statusLabel(item.compensation_type)
                          : "Compensation not specified"}
                </span>

                <Link
                  to={`/creator/opportunities/${item.opportunity_id}`}
                  className="mo-view-link"
                >
                  <Eye size={16} /> View
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
