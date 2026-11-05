
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
  X,
  Trash2,
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
  created_at?: string | null;
  published_at?: string | null;
  compensation_type?: string;
  compensation_amount?: number | null;
};

function formatDate(value?: string | null) {
  if (!value) return "Not available";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Not available"
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

function getCompensation(item: Opportunity) {
  if (
    item.compensation_type === "stipend" &&
    item.compensation_amount != null
  ) {
    return `$${item.compensation_amount} stipend`;
  }

  if (
    item.compensation_type === "paid" &&
    item.compensation_amount != null
  ) {
    return `$${item.compensation_amount} paid`;
  }

  if (item.compensation_type === "unpaid") {
    return "Volunteer / Unpaid";
  }

  return item.compensation_type
    ? statusLabel(item.compensation_type)
    : "Compensation not specified";
}

export default function MyOpportunities() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");

  const [selectedOpportunity, setSelectedOpportunity] =
    useState<Opportunity | null>(null);

  const [deletingId, setDeletingId] = useState<number | null>(null);

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
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          `Unable to load opportunities (HTTP ${response.status}).`
        );
      }

      const rows =
        Array.isArray(data)
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

  // Close the details popup with Escape.
  useEffect(() => {
    if (!selectedOpportunity) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSelectedOpportunity(null);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [selectedOpportunity]);

  async function deleteOpportunity(item: Opportunity) {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${item.title}"? This action cannot be undone.`
    );

    if (!confirmed) return;

    const token = localStorage.getItem("access_token");

    if (!token) {
      window.alert("Please sign in to delete an opportunity.");
      return;
    }

    setDeletingId(item.opportunity_id);

    try {
      const response = await fetch(
        `${API_BASE_URL}/opportunities/${item.opportunity_id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => null);

        throw new Error(
          data?.detail ||
            `Unable to delete opportunity (HTTP ${response.status}).`
        );
      }

      // Update the list after the server confirms deletion.
      setItems((currentItems) =>
        currentItems.filter(
          (opportunity) =>
            opportunity.opportunity_id !== item.opportunity_id
        )
      );

      // Close the popup if it shows the deleted opportunity.
      setSelectedOpportunity((current) =>
        current?.opportunity_id === item.opportunity_id
          ? null
          : current
      );
    } catch (err) {
      window.alert(
        err instanceof Error
          ? err.message
          : "Something went wrong while deleting the opportunity."
      );
    } finally {
      setDeletingId(null);
    }
  }

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
          <p>
            Manage the opportunities your organization has created.
          </p>
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
          disabled={loading || deletingId !== null}
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

          <button
            type="button"
            onClick={() => void loadOpportunities()}
          >
            Try again
          </button>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="mo-empty">
          <span className="mo-empty-icon">
            <BriefcaseBusiness size={30} />
          </span>

          <h2>
            {items.length
              ? "No matching opportunities"
              : "No opportunities yet"}
          </h2>

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
            <article
              className="mo-card"
              key={item.opportunity_id}
            >
              <div className="mo-card-top">
                <span className="mo-card-icon">
                  <BriefcaseBusiness size={22} />
                </span>

                <span
                  className={`mo-badge mo-status-${item.status
                    .toLowerCase()
                    .replaceAll("_", "-")}`}
                >
                  {statusLabel(item.status)}
                </span>
              </div>

              <span className="mo-category">
                {item.category?.name ?? "Opportunity"}
              </span>

              <h2>{item.title}</h2>

              <p className="mo-description">
                {item.description}
              </p>

              <div className="mo-metadata">
                <span>
                  <MapPin size={16} />
                  {item.location ||
                    item.work_mode?.replaceAll("_", " ") ||
                    "Location not specified"}
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
                  {getCompensation(item)}
                </span>

                <div className="mo-card-actions">
                  <button
                    type="button"
                    className="mo-view-link"
                    onClick={() => setSelectedOpportunity(item)}
                    aria-label={`View details for ${item.title}`}
                  >
                    <Eye size={16} /> View
                  </button>

                  <button
                    type="button"
                    className="mo-delete-button"
                    onClick={() => void deleteOpportunity(item)}
                    disabled={deletingId !== null}
                    aria-label={`Delete ${item.title}`}
                  >
                    <Trash2 size={16} />
                    {deletingId === item.opportunity_id
                      ? "Deleting..."
                      : "Delete"}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Opportunity details popup */}
      {selectedOpportunity && (
        <div
          className="mo-modal-overlay"
          onClick={() => setSelectedOpportunity(null)}
        >
          <section
            className="mo-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mo-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="mo-modal-header">
              <div>
                <span className="mo-eyebrow">
                  CREATOR WORKSPACE
                </span>

                <h2 id="mo-modal-title">
                  {selectedOpportunity.title}
                </h2>

                <p>Opportunity details</p>
              </div>

              <button
                type="button"
                className="mo-modal-close"
                onClick={() => setSelectedOpportunity(null)}
                aria-label="Close opportunity details"
              >
                <X size={22} />
              </button>
            </header>

            <div className="mo-modal-body">
              <div className="mo-modal-status">
                <span className="mo-category">
                  {selectedOpportunity.category?.name ??
                    "Opportunity"}
                </span>

                <span
                  className={`mo-badge mo-status-${selectedOpportunity.status
                    .toLowerCase()
                    .replaceAll("_", "-")}`}
                >
                  {statusLabel(selectedOpportunity.status)}
                </span>
              </div>

              <div className="mo-modal-section">
                <h3>Description</h3>
                <p>
                  {selectedOpportunity.description ||
                    "No description provided."}
                </p>
              </div>

              <div className="mo-modal-info-grid">
                <div className="mo-modal-info">
                  <MapPin size={18} />
                  <div>
                    <span>Location</span>
                    <strong>
                      {selectedOpportunity.location ||
                        selectedOpportunity.work_mode?.replaceAll(
                          "_",
                          " "
                        ) ||
                        "Not specified"}
                    </strong>
                  </div>
                </div>

                <div className="mo-modal-info">
                  <Clock size={18} />
                  <div>
                    <span>Expected hours</span>
                    <strong>
                      {selectedOpportunity.expected_hours != null
                        ? `${selectedOpportunity.expected_hours} hours`
                        : "Not specified"}
                    </strong>
                  </div>
                </div>

                <div className="mo-modal-info">
                  <CalendarDays size={18} />
                  <div>
                    <span>Published Date</span>
                    <strong>
                      {formatDate(
                        selectedOpportunity.published_at ??
                          selectedOpportunity.created_at
                      )}
                    </strong>
                  </div>
                </div>

                <div className="mo-modal-info">
                  <CalendarDays size={18} />
                  <div>
                    <span>Application deadline</span>
                    <strong>
                      {formatDate(
                        selectedOpportunity.application_deadline
                      )}
                    </strong>
                  </div>
                </div>

                <div className="mo-modal-info">
                  <BriefcaseBusiness size={18} />
                  <div>
                    <span>Compensation</span>
                    <strong>
                      {getCompensation(selectedOpportunity)}
                    </strong>
                  </div>
                </div>
              </div>
            </div>

            <footer className="mo-modal-footer">
              <button
                type="button"
                className="mo-modal-close-button"
                onClick={() => setSelectedOpportunity(null)}
              >
                Close
              </button>
            </footer>
          </section>
        </div>
      )}
    </section>
  );
}
