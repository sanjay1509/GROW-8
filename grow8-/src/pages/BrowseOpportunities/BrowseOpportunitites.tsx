
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  MapPin,
  Clock,
  CalendarDays,
  BriefcaseBusiness,
  Building2,
  X,
  SlidersHorizontal,
  ArrowUpDown,
  Filter,
} from "lucide-react";

import Navbar from "../../components/Navbar/Navbar";
import BackToTop from "../../components/BackToTop/BackToTop";

import {
  fetchOpportunities,
  type Opportunity,
} from "../../services/opportunities";

import { applyToOpportunity } from "../../services/applications";
import { ApiError, API_BASE_URL } from "../../services/api";

import "./BrowseOpportunities.css";

// ==================================================
// TYPES
// ==================================================

type BrowseOpportunity = Opportunity & {
  organization?: string;
  skills?: string[];
  color?: string;
  icon?: string;
};

type UserRole = "contributor" | "creator" | "admin" | "";

// ==================================================
// HELPER FUNCTIONS
// ==================================================

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "Not specified";

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) return "Not specified";

  return date.toLocaleDateString("en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
};

const getDaysRemaining = (dateString?: string | null) => {
  if (!dateString) return null;

  const deadline = new Date(dateString);
  const today = new Date();

  today.setHours(0, 0, 0, 0);

  if (Number.isNaN(deadline.getTime())) return null;

  deadline.setHours(0, 0, 0, 0);

  return Math.ceil(
    (deadline.getTime() - today.getTime()) /
      (1000 * 60 * 60 * 24)
  );
};

const getIcon = (opportunity: BrowseOpportunity) => {
  if (opportunity.icon === "event") return Building2;
  return BriefcaseBusiness;
};

const getHoursLabel = (hours?: number | null) => {
  if (hours == null) return "Flexible hours";
  return `${hours} expected hours`;
};

// ==================================================
// BROWSE OPPORTUNITIES COMPONENT
// ==================================================

export default function BrowseOpportunities() {
  const navigate = useNavigate();

  const [opportunities, setOpportunities] = useState<
    BrowseOpportunity[]
  >([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Authentication
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState<UserRole>("");
  const [authLoading, setAuthLoading] = useState(true);

  // Application state
  const [applyingId, setApplyingId] = useState<number | null>(null);
  const [motivation, setMotivation] = useState("");
  const [applicationMessage, setApplicationMessage] = useState("");
  const [applicationError, setApplicationError] = useState("");
  const [duplicateApplicationId, setDuplicateApplicationId] =
    useState<number | null>(null);

  const [appliedIds, setAppliedIds] = useState<Set<number>>(
    new Set()
  );

  // Search and filters
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedModes, setSelectedModes] = useState<string[]>([]);
  const [selectedHours, setSelectedHours] = useState<string[]>([]);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState("deadline");
  const [showFilters, setShowFilters] = useState(true);

  // Details modal
  const [selectedOpportunity, setSelectedOpportunity] =
    useState<BrowseOpportunity | null>(null);

  // ==================================================
  // CHECK AUTHENTICATION
  // ==================================================

  useEffect(() => {
    const controller = new AbortController();

    async function checkAuthentication() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setIsAuthenticated(false);
        setUserRole("");
        setAuthLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          setIsAuthenticated(false);
          setUserRole("");
          return;
        }

        const data = await response.json();

        const nestedUser =
          data?.user && typeof data.user === "object"
            ? data.user
            : data?.data && typeof data.data === "object"
              ? data.data
              : data;

        const role = String(
          nestedUser?.role || ""
        ).toLowerCase();

        setIsAuthenticated(true);
        setUserRole(
          role === "contributor" ||
            role === "creator" ||
            role === "admin"
            ? role
            : ""
        );
      } catch (err) {
        if (
          !controller.signal.aborted &&
          err instanceof Error &&
          err.name !== "AbortError"
        ) {
          setIsAuthenticated(false);
          setUserRole("");
        }
      } finally {
        if (!controller.signal.aborted) {
          setAuthLoading(false);
        }
      }
    }

    void checkAuthentication();

    return () => controller.abort();
  }, []);

  // ==================================================
  // LOAD OPPORTUNITIES FROM FASTAPI BACKEND
  // ==================================================

  useEffect(() => {
    const controller = new AbortController();

    async function loadOpportunities() {
      setLoading(true);
      setError("");

      try {
        const result = await fetchOpportunities({
          signal: controller.signal,
        });

        if (!controller.signal.aborted) {
          setOpportunities(Array.isArray(result) ? result : []);
        }
      } catch (err) {
        const error = err as Error;

        if (
          error.name !== "AbortError" &&
          !controller.signal.aborted
        ) {
          setError(
            error.message ||
              "Something went wrong while loading opportunities."
          );
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

  // ==================================================
  // APPLY TO OPPORTUNITY
  // ==================================================

  async function handleApply(opportunity: BrowseOpportunity) {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    if (userRole !== "contributor") {
      return;
    }

    const opportunityId =
      opportunity.opportunity_id ?? opportunity.id;

    setApplyingId(opportunityId);
    setApplicationError("");
    setApplicationMessage("");
    setDuplicateApplicationId(null);

    try {
      await applyToOpportunity(
        opportunityId,
        motivation.trim() || undefined
      );

      setAppliedIds((previous) => {
        const updated = new Set(previous);
        updated.add(opportunityId);
        return updated;
      });

      setApplicationMessage(
        "Your application has been submitted successfully!"
      );

      setMotivation("");
    } catch (err) {
      if (err instanceof ApiError) {
        const messages: Record<string, string> = {
          OPPORTUNITY_NOT_OPEN:
            "This opportunity is no longer accepting applications.",

          APPLICATION_DEADLINE_PASSED:
            "The application deadline has passed.",

          APPLICANT_LIMIT_REACHED:
            "All available places for this opportunity have been taken.",

          APPLICATION_DUPLICATE:
            "You have already applied for this opportunity.",

          CONTRIBUTOR_PROFILE_REQUIRED:
            "Please complete your contributor profile before applying.",

          AUTH_REQUIRED:
            "Please sign in to apply.",

          INVALID_TOKEN:
            "Your session has expired. Please sign in again.",

          VALIDATION_ERROR:
            "Please check your application details and try again.",
        };

        setApplicationError(
          messages[err.code] ||
            err.message ||
            "Unable to submit your application."
        );

        if (err.code === "APPLICATION_DUPLICATE") {
          const applicationId = Number(
            err.details?.application_id
          );

          if (
            Number.isFinite(applicationId) &&
            applicationId > 0
          ) {
            setDuplicateApplicationId(applicationId);
          }
        }

        if (
          err.code === "AUTH_REQUIRED" ||
          err.code === "INVALID_TOKEN"
        ) {
          navigate("/login");
        }
      } else {
        setApplicationError(
          err instanceof Error
            ? err.message
            : "Something went wrong. Please try again."
        );
      }
    } finally {
      setApplyingId(null);
    }
  }

  // ==================================================
  // DYNAMIC FILTER OPTIONS
  // ==================================================

  const categories = useMemo(
    () => [
      ...new Set(
        opportunities
          .map((item) => item.category)
          .filter(Boolean)
      ),
    ],
    [opportunities]
  );

  const modes = useMemo(
    () => [
      ...new Set(
        opportunities
          .map((item) => item.workMode)
          .filter(Boolean)
      ),
    ],
    [opportunities]
  );

  const skills = useMemo(
    () => [
      ...new Set(
        opportunities.flatMap((item) =>
          Array.isArray(item.skills) ? item.skills : []
        )
      ),
    ],
    [opportunities]
  );

  // ==================================================
  // CHECKBOX HELPER
  // ==================================================

  const toggleSelection = (
    value: string,
    setSelected: React.Dispatch<React.SetStateAction<string[]>>
  ) => {
    setSelected((previous) =>
      previous.includes(value)
        ? previous.filter((item) => item !== value)
        : [...previous, value]
    );
  };

  // ==================================================
  // SEARCH, FILTER AND SORT
  // ==================================================

  const filteredOpportunities = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    const results = opportunities.filter((item) => {
      const itemSkills = Array.isArray(item.skills)
        ? item.skills
        : [];

      const searchableText = [
        item.title,
        item.organization,
        item.location,
        item.workMode,
        item.category,
        item.description,
        ...itemSkills,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query || searchableText.includes(query);

      const matchesCategory =
        selectedCategories.length === 0 ||
        selectedCategories.includes(item.category);

      const matchesMode =
        selectedModes.length === 0 ||
        selectedModes.includes(item.workMode);

      const hoursValue = Number(item.expectedHours ?? 0);

      const matchesHours =
        selectedHours.length === 0 ||
        selectedHours.some((range) => {
          if (range === "Under 5") return hoursValue < 5;

          if (range === "5-10") {
            return hoursValue >= 5 && hoursValue <= 10;
          }

          if (range === "10+") return hoursValue > 10;

          return true;
        });

      const matchesSkills =
        selectedSkills.length === 0 ||
        selectedSkills.some((skill) =>
          itemSkills.includes(skill)
        );

      return (
        matchesSearch &&
        matchesCategory &&
        matchesMode &&
        matchesHours &&
        matchesSkills
      );
    });

    return [...results].sort((a, b) => {
      if (sortBy === "title") {
        return (a.title || "").localeCompare(b.title || "");
      }

      const dateA = a.deadline
        ? new Date(a.deadline).getTime()
        : Infinity;

      const dateB = b.deadline
        ? new Date(b.deadline).getTime()
        : Infinity;

      if (sortBy === "latest") return dateB - dateA;

      return dateA - dateB;
    });
  }, [
    opportunities,
    searchTerm,
    selectedCategories,
    selectedModes,
    selectedHours,
    selectedSkills,
    sortBy,
  ]);

  // ==================================================
  // CLEAR FILTERS
  // ==================================================

  const clearFilters = () => {
    setSearchTerm("");
    setSelectedCategories([]);
    setSelectedModes([]);
    setSelectedHours([]);
    setSelectedSkills([]);
    setSortBy("deadline");
  };

  const hasActiveFilters =
    searchTerm.trim() !== "" ||
    selectedCategories.length > 0 ||
    selectedModes.length > 0 ||
    selectedHours.length > 0 ||
    selectedSkills.length > 0;

  // ==================================================
  // CLOSE MODAL
  // ==================================================

  function closeDetailsModal() {
    setSelectedOpportunity(null);
    setApplicationError("");
    setApplicationMessage("");
    setDuplicateApplicationId(null);
    setMotivation("");
  }

  // ==================================================
  // PAGE UI
  // ==================================================

  return (
    <main className="browse-page">
      <Navbar />

      {/* Heading banner */}
      <section className="browse-heading">
        <div>
          <p className="browse-eyebrow">
            DISCOVER YOUR NEXT OPPORTUNITY
          </p>

          <h1>Browse Opportunities</h1>

          <p>
            Find meaningful opportunities, develop your skills,
            and make a difference in your community.
          </p>
        </div>
      </section>

      {/* Layout */}
      <div
        className={`browse-layout ${
          showFilters ? "" : "browse-layout--no-filters"
        }`}
      >
        {/* Filter sidebar */}
        {showFilters && (
          <aside className="browse-filters">
            <div className="browse-filter-heading">
              <div className="browse-filter-title">
                <Filter size={17} />
                <h2>Filters</h2>
              </div>

              <button
                type="button"
                className="browse-clear-button"
                onClick={clearFilters}
              >
                Clear all
              </button>
            </div>

            <fieldset className="browse-filter-group">
              <legend>Category</legend>

              {categories.map((category) => (
                <label className="browse-checkbox" key={category}>
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category)}
                    onChange={() =>
                      toggleSelection(category, setSelectedCategories)
                    }
                  />
                  {category}
                </label>
              ))}
            </fieldset>

            <fieldset className="browse-filter-group">
              <legend>Work mode</legend>

              {modes.map((mode) => (
                <label className="browse-checkbox" key={mode}>
                  <input
                    type="checkbox"
                    checked={selectedModes.includes(mode)}
                    onChange={() =>
                      toggleSelection(mode, setSelectedModes)
                    }
                  />
                  {mode}
                </label>
              ))}
            </fieldset>

            <fieldset className="browse-filter-group">
              <legend>Time commitment</legend>

              {["Under 5", "5-10", "10+"].map((range) => (
                <label className="browse-checkbox" key={range}>
                  <input
                    type="checkbox"
                    checked={selectedHours.includes(range)}
                    onChange={() =>
                      toggleSelection(range, setSelectedHours)
                    }
                  />
                  {range === "Under 5"
                    ? "Under 5 hours"
                    : range === "5-10"
                      ? "5–10 hours"
                      : "More than 10 hours"}
                </label>
              ))}
            </fieldset>

            <fieldset className="browse-filter-group">
              <legend>Skills</legend>

              {skills.length > 0 ? (
                skills.map((skill) => (
                  <label className="browse-checkbox" key={skill}>
                    <input
                      type="checkbox"
                      checked={selectedSkills.includes(skill)}
                      onChange={() =>
                        toggleSelection(skill, setSelectedSkills)
                      }
                    />
                    {skill}
                  </label>
                ))
              ) : (
                <p>No skills available</p>
              )}
            </fieldset>

            <button
              type="button"
              className="browse-reset-button"
              onClick={clearFilters}
            >
              Reset filters
            </button>
          </aside>
        )}

        {/* Results */}
        <section className="browse-results">
          <div className="browse-search-row">
            <div className="browse-search">
              <Search size={18} />

              <input
                type="search"
                placeholder="Search opportunities, organizations, skills..."
                value={searchTerm}
                onChange={(event) =>
                  setSearchTerm(event.target.value)
                }
                aria-label="Search opportunities"
              />

              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm("")}
                  aria-label="Clear search"
                >
                  <X size={16} />
                </button>
              )}
            </div>

            <button
              type="button"
              className="browse-toggle-filters"
              onClick={() =>
                setShowFilters((previous) => !previous)
              }
              aria-expanded={showFilters}
            >
              <SlidersHorizontal size={16} />
              {showFilters ? "Hide filters" : "Show filters"}
            </button>

            <div className="browse-sort">
              <ArrowUpDown size={15} />

              <span className="browse-sort-label">Sort:</span>

              <select
                aria-label="Sort opportunities"
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
              >
                <option value="deadline">Upcoming deadline</option>
                <option value="latest">Latest deadline</option>
                <option value="title">Title A–Z</option>
              </select>
            </div>
          </div>

          <div className="browse-results-count">
            <span>
              Showing{" "}
              <strong>{filteredOpportunities.length}</strong>{" "}
              opportunities
            </span>

            {hasActiveFilters && (
              <button
                type="button"
                className="browse-inline-clear"
                onClick={clearFilters}
              >
                Clear applied filters
              </button>
            )}
          </div>

          {loading && (
            <div className="browse-empty-state">
              <p>Loading opportunities...</p>
            </div>
          )}

          {!loading && error && (
            <div className="browse-empty-state">
              <h3>Unable to load opportunities</h3>
              <p>{error}</p>

              <button
                type="button"
                onClick={() => window.location.reload()}
              >
                Try again
              </button>
            </div>
          )}

          {!loading &&
            !error &&
            filteredOpportunities.length === 0 && (
              <div className="browse-empty-state">
                <div className="browse-empty-icon">
                  <Search size={25} />
                </div>

                <h3>No opportunities found</h3>

                <p>
                  Try changing your search or filters to find
                  opportunities that match your interests.
                </p>

                <button type="button" onClick={clearFilters}>
                  Clear filters
                </button>
              </div>
            )}

          {/* Opportunity cards */}
          {!loading && !error && filteredOpportunities.length > 0 && (
            <div className="browse-opportunity-list">
              {filteredOpportunities.map((opportunity) => {
                const OpportunityIcon = getIcon(opportunity);
                const daysRemaining = getDaysRemaining(
                  opportunity.deadline
                );

                return (
                  <article
                    className="browse-opportunity-card"
                    key={opportunity.id}
                  >
                    <div
                      className={`browse-opportunity-icon ${
                        opportunity.color || "blue"
                      }`}
                    >
                      <OpportunityIcon size={22} />
                    </div>

                    <div className="browse-opportunity-content">
                      <h3>{opportunity.title}</h3>

                      <p className="browse-organization">
                        {opportunity.organization ||
                          "Organization not specified"}
                      </p>

                      <p className="browse-description">
                        {opportunity.description}
                      </p>

                      <div className="browse-meta">
                        <span>
                          <MapPin size={13} />
                          {opportunity.location ||
                            "Location not specified"}
                        </span>

                        <span>
                          <Building2 size={13} />
                          {opportunity.workMode || "Flexible"}
                        </span>

                        <span>
                          <Clock size={13} />
                          {getHoursLabel(opportunity.expectedHours)}
                        </span>

                        <span>
                          <CalendarDays size={13} />
                          Deadline: {formatDate(opportunity.deadline)}
                        </span>
                      </div>

                      <div className="browse-tags">
                        <span className="browse-tag category-tag">
                          {opportunity.category || "General"}
                        </span>

                        {(Array.isArray(opportunity.skills)
                          ? opportunity.skills
                          : []
                        ).map((skill) => (
                          <span className="browse-tag" key={skill}>
                            {skill}
                          </span>
                        ))}

                        {daysRemaining !== null && (
                          <span className="browse-tag">
                            {daysRemaining < 0
                              ? "Deadline passed"
                              : daysRemaining === 0
                                ? "Deadline today"
                                : `${daysRemaining} days left`}
                          </span>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      className="browse-details-button"
                      onClick={() => {
                        setSelectedOpportunity(opportunity);
                        setApplicationError("");
                        setApplicationMessage("");
                        setDuplicateApplicationId(null);
                        setMotivation("");
                      }}
                    >
                      View Details
                    </button>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* Opportunity details modal */}
      {selectedOpportunity && (
        <div
          className="browse-modal-backdrop"
          onClick={closeDetailsModal}
        >
          <section
            className="browse-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="browse-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="browse-modal-close"
              onClick={closeDetailsModal}
              aria-label="Close details"
            >
              <X size={20} />
            </button>

            <p className="browse-modal-eyebrow">
              {selectedOpportunity.category || "Opportunity"}
            </p>

            <h2 id="browse-modal-title">
              {selectedOpportunity.title}
            </h2>

            <p className="browse-modal-organization">
              {selectedOpportunity.organization ||
                "Organization not specified"}
            </p>

            <p className="browse-modal-description">
              {selectedOpportunity.description ||
                "Contact the organization for more information about this opportunity."}
            </p>

            <div className="browse-modal-info">
              <p>
                <MapPin size={17} />
                <span>
                  <strong>Location</strong>
                  {selectedOpportunity.location || "Not specified"}
                </span>
              </p>

              <p>
                <Building2 size={17} />
                <span>
                  <strong>Work mode</strong>
                  {selectedOpportunity.workMode || "Not specified"}
                </span>
              </p>

              <p>
                <Clock size={17} />
                <span>
                  <strong>Time commitment</strong>
                  {getHoursLabel(selectedOpportunity.expectedHours)}
                </span>
              </p>

              <p>
                <CalendarDays size={17} />
                <span>
                  <strong>Application deadline</strong>
                  {formatDate(selectedOpportunity.deadline)}
                </span>
              </p>
            </div>

            <h3 className="browse-modal-subheading">
              Skills required
            </h3>

            <div className="browse-tags">
              {(Array.isArray(selectedOpportunity.skills)
                ? selectedOpportunity.skills
                : []
              ).map((skill) => (
                <span className="browse-tag" key={skill}>
                  {skill}
                </span>
              ))}

              {(!selectedOpportunity.skills ||
                selectedOpportunity.skills.length === 0) && (
                <span>No specific skills listed.</span>
              )}
            </div>

            {/* Application section */}
            {!authLoading &&
              (userRole === "contributor" || !isAuthenticated) && (
                <div className="browse-application-section">
                  <h3>Apply for this opportunity</h3>

                  {!isAuthenticated ? (
                    <button
                      type="button"
                      className="browse-apply-button"
                      onClick={() => navigate("/login")}
                    >
                      Sign In to Apply
                    </button>
                  ) : appliedIds.has(
                      selectedOpportunity.opportunity_id ??
                        selectedOpportunity.id
                    ) ? (
                    <>
                      <p
                        className="browse-application-success"
                        role="status"
                      >
                        {applicationMessage ||
                          "You have successfully applied for this opportunity."}
                      </p>

                      <button
                        type="button"
                        className="browse-apply-button"
                        disabled
                      >
                        Applied
                      </button>
                    </>
                  ) : (
                    <>
                      <label htmlFor="application-motivation">
                        Motivation (Optional)
                      </label>

                      <textarea
                        id="application-motivation"
                        className="browse-motivation-input"
                        value={motivation}
                        onChange={(event) =>
                          setMotivation(
                            event.target.value.slice(0, 5000)
                          )
                        }
                        maxLength={5000}
                        placeholder="Tell the organization why you are interested in this opportunity..."
                        rows={5}
                      />

                      <div className="browse-character-count">
                        {motivation.length}/5000 characters
                      </div>

                      {applicationError && (
                        <div
                          className="browse-application-error"
                          role="alert"
                        >
                          {applicationError}

                          {duplicateApplicationId && (
                            <p>
                              <button
                                type="button"
                                onClick={() =>
                                  navigate(
                                    `/contributor/applications?application_id=${duplicateApplicationId}`
                                  )
                                }
                              >
                                View your existing application
                              </button>
                            </p>
                          )}
                        </div>
                      )}

                      {applicationMessage && (
                        <p
                          className="browse-application-success"
                          role="status"
                        >
                          {applicationMessage}
                        </p>
                      )}

                      <button
                        type="button"
                        className="browse-apply-button"
                        disabled={
                          applyingId !== null ||
                          !selectedOpportunity.id
                        }
                        onClick={() =>
                          void handleApply(selectedOpportunity)
                        }
                      >
                        {applyingId ===
                        (selectedOpportunity.opportunity_id ??
                          selectedOpportunity.id)
                          ? "Submitting..."
                          : "Apply Now"}
                      </button>
                    </>
                  )}
                </div>
              )}

            <button
              type="button"
              className="browse-modal-done"
              onClick={closeDetailsModal}
            >
              Close Details
            </button>
          </section>
        </div>
      )}

      <BackToTop />
    </main>
  );
}
