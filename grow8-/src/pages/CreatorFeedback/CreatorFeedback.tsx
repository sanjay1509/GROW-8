
import React, { useMemo, useState } from "react";
import "./CreatorFeedback.css";

type FeedbackStatus = "Approved" | "Pending" | "Rejected";

interface Feedback {
  id: number;
  contributor: string;
  initials: string;
  opportunity: string;
  rating: number;
  comment: string;
  date: string;
  status: FeedbackStatus;
}

interface Contributor {
  id: number;
  name: string;
  initials: string;
  opportunity: string;
  completedDate: string;
  verified: boolean;
}

const initialFeedback: Feedback[] = [
  {
    id: 1,
    contributor: "Alex Johnson",
    initials: "AJ",
    opportunity: "Website Data Entry",
    rating: 5,
    comment:
      "The opportunity was well organized. The creator provided clear instructions and was very supportive throughout the work.",
    date: "November 5, 2026",
    status: "Approved",
  },
  {
    id: 2,
    contributor: "Sophia Williams",
    initials: "SW",
    opportunity: "Community Event Support",
    rating: 4,
    comment:
      "Great experience working with the team. Communication was good and all the required information was provided.",
    date: "November 2, 2026",
    status: "Approved",
  },
  {
    id: 3,
    contributor: "Daniel Smith",
    initials: "DS",
    opportunity: "Digital Record Organization",
    rating: 5,
    comment:
      "A positive experience. The project expectations were clear and the work was completed smoothly.",
    date: "October 28, 2026",
    status: "Pending",
  },
];

const eligibleContributors: Contributor[] = [
  {
    id: 101,
    name: "Michael Brown",
    initials: "MB",
    opportunity: "Website Data Entry",
    completedDate: "November 6, 2026",
    verified: true,
  },
  {
    id: 102,
    name: "Emma Davis",
    initials: "ED",
    opportunity: "Community Event Support",
    completedDate: "November 4, 2026",
    verified: true,
  },
  {
    id: 103,
    name: "Ryan Wilson",
    initials: "RW",
    opportunity: "Digital Record Organization",
    completedDate: "November 1, 2026",
    verified: true,
  },
];

const StarRating = ({
  rating,
  interactive = false,
  onChange,
  size = "normal",
}: {
  rating: number;
  interactive?: boolean;
  onChange?: (rating: number) => void;
  size?: "normal" | "large";
}) => (
  <div className={`cf-stars ${size}`}>
    {[1, 2, 3, 4, 5].map((star) => (
      <button
        key={star}
        type="button"
        className={`cf-star ${star <= rating ? "active" : ""}`}
        disabled={!interactive}
        onClick={() => onChange?.(star)}
        aria-label={`Rate ${star} out of 5`}
      >
        ★
      </button>
    ))}
  </div>
);

const CreatorFeedback: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"received" | "give">("received");
  const [feedbacks, setFeedbacks] = useState(initialFeedback);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selectedContributor, setSelectedContributor] = useState("");
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [quality, setQuality] = useState("");
  const [communication, setCommunication] = useState("");
  const [reliability, setReliability] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const averageRating = useMemo(() => {
    if (!feedbacks.length) return "0.0";

    const approved = feedbacks.filter((f) => f.status === "Approved");
    if (!approved.length) return "0.0";

    return (
      approved.reduce((total, feedback) => total + feedback.rating, 0) /
      approved.length
    ).toFixed(1);
  }, [feedbacks]);

  const pendingCount = feedbacks.filter(
    (feedback) => feedback.status === "Pending"
  ).length;

  const filteredFeedback = feedbacks.filter((feedback) => {
    const matchesSearch =
      feedback.contributor.toLowerCase().includes(search.toLowerCase()) ||
      feedback.opportunity.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      statusFilter === "All" || feedback.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedContributor || rating === 0 || !comment.trim()) {
      return;
    }

    const contributor = eligibleContributors.find(
      (item) => item.id === Number(selectedContributor)
    );

    if (!contributor) return;

    const newFeedback: Feedback = {
      id: Date.now(),
      contributor: contributor.name,
      initials: contributor.initials,
      opportunity: contributor.opportunity,
      rating,
      comment: comment.trim(),
      date: new Date().toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      }),
      status: "Pending",
    };

    setFeedbacks((previous) => [newFeedback, ...previous]);
    setSuccessMessage(
      `Your feedback for ${contributor.name} has been submitted for admin review.`
    );

    setSelectedContributor("");
    setRating(0);
    setComment("");
    setQuality("");
    setCommunication("");
    setReliability("");

    setActiveTab("received");
    setStatusFilter("All");
    setSearch("");
  };

  return (
    <div className="creator-feedback-page">
      {/* Page Heading */}
      <div className="cf-page-header">
        <div>
          <div className="cf-breadcrumb">
            Creator Dashboard <span>/</span> Feedback
          </div>

          <h1>Feedback & Reviews</h1>

          <p>
            Share your experience and discover what Contributors think about
            working with you.
          </p>
        </div>

        <button
          className="cf-primary-button"
          onClick={() => {
            setActiveTab("give");
            setSuccessMessage("");
          }}
        >
          <span>＋</span> Give Feedback
        </button>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div className="cf-success-message" role="status">
          <span>✓</span>
          {successMessage}
          <button
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      {/* Statistics */}
      <div className="cf-stats-grid">
        <div className="cf-stat-card">
          <div className="cf-stat-icon purple">✉</div>
          <div>
            <span>Total Feedback</span>
            <h2>{feedbacks.length}</h2>
            <small>All received reviews</small>
          </div>
        </div>

        <div className="cf-stat-card">
          <div className="cf-stat-icon yellow">★</div>
          <div>
            <span>Average Rating</span>
            <h2>{averageRating}<small className="cf-out-of"> / 5</small></h2>
            <small>Approved feedback only</small>
          </div>
        </div>

        <div className="cf-stat-card">
          <div className="cf-stat-icon green">✓</div>
          <div>
            <span>Approved Reviews</span>
            <h2>
              {feedbacks.filter((f) => f.status === "Approved").length}
            </h2>
            <small>Published feedback</small>
          </div>
        </div>

        <div className="cf-stat-card">
          <div className="cf-stat-icon orange">◷</div>
          <div>
            <span>Pending Reviews</span>
            <h2>{pendingCount}</h2>
            <small>Awaiting admin review</small>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="cf-tabs">
        <button
          className={activeTab === "received" ? "active" : ""}
          onClick={() => {
            setActiveTab("received");
            setSuccessMessage("");
          }}
        >
          <span>▤</span> Feedback Received
          <span className="cf-tab-count">{feedbacks.length}</span>
        </button>

        <button
          className={activeTab === "give" ? "active" : ""}
          onClick={() => {
            setActiveTab("give");
            setSuccessMessage("");
          }}
        >
          <span>✎</span> Give Feedback
        </button>
      </div>

      {/* Received Feedback */}
      {activeTab === "received" && (
        <section className="cf-content">
          <div className="cf-section-heading">
            <div>
              <h2>Feedback from Contributors</h2>
              <p>See what Contributors say about their experience with you.</p>
            </div>
          </div>

          <div className="cf-filter-bar">
            <div className="cf-search-box">
              <span>⌕</span>
              <input
                type="text"
                placeholder="Search by contributor or opportunity..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="All">All Status</option>
              <option value="Approved">Approved</option>
              <option value="Pending">Pending</option>
              <option value="Rejected">Rejected</option>
            </select>
          </div>

          <div className="cf-feedback-list">
            {filteredFeedback.length > 0 ? (
              filteredFeedback.map((feedback) => (
                <article className="cf-feedback-card" key={feedback.id}>
                  <div className="cf-feedback-top">
                    <div className="cf-person-info">
                      <div className="cf-avatar">{feedback.initials}</div>
                      <div>
                        <h3>{feedback.contributor}</h3>
                        <span>{feedback.opportunity}</span>
                      </div>
                    </div>

                    <span
                      className={`cf-status ${feedback.status.toLowerCase()}`}
                    >
                      {feedback.status}
                    </span>
                  </div>

                  <div className="cf-rating-row">
                    <StarRating rating={feedback.rating} />
                    <span className="cf-rating-number">
                      {feedback.rating}.0 / 5
                    </span>
                  </div>

                  <p className="cf-comment">{feedback.comment}</p>

                  <div className="cf-feedback-footer">
                    <span>◷ {feedback.date}</span>
                    {feedback.status === "Approved" && (
                      <span className="cf-approved-label">
                        ✓ Published feedback
                      </span>
                    )}
                    {feedback.status === "Pending" && (
                      <span className="cf-pending-label">
                        Awaiting moderation
                      </span>
                    )}
                  </div>
                </article>
              ))
            ) : (
              <div className="cf-empty-state">
                <div>✉</div>
                <h3>No feedback found</h3>
                <p>Try changing your search or status filter.</p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Give Feedback */}
      {activeTab === "give" && (
        <section className="cf-content cf-give-section">
          <div className="cf-section-heading">
            <div>
              <h2>Give Feedback to a Contributor</h2>
              <p>
                Recognize Contributors who successfully completed their work.
              </p>
            </div>
          </div>

          <div className="cf-form-card">
            <div className="cf-form-intro">
              <div className="cf-form-icon">✎</div>
              <div>
                <h3>Contributor Review Form</h3>
                <p>
                  Feedback can only be submitted for verified and completed
                  opportunities.
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="cf-form-group">
                <label htmlFor="cf-contributor">
                  Select Contributor <span>*</span>
                </label>

                <select
                  id="cf-contributor"
                  value={selectedContributor}
                  onChange={(event) =>
                    setSelectedContributor(event.target.value)
                  }
                  required
                >
                  <option value="">Choose a Contributor</option>
                  {eligibleContributors
                    .filter((contributor) => contributor.verified)
                    .map((contributor) => (
                      <option key={contributor.id} value={contributor.id}>
                        {contributor.name} — {contributor.opportunity}
                      </option>
                    ))}
                </select>

                <small>
                  Only Contributors with verified work are eligible.
                </small>
              </div>

              {selectedContributor && (
                <div className="cf-selected-contributor">
                  {(() => {
                    const contributor = eligibleContributors.find(
                      (item) => item.id === Number(selectedContributor)
                    );

                    if (!contributor) return null;

                    return (
                      <>
                        <div className="cf-avatar">{contributor.initials}</div>
                        <div>
                          <strong>{contributor.name}</strong>
                          <span>{contributor.opportunity}</span>
                          <small>
                            ✓ Work verified · Completed{" "}
                            {contributor.completedDate}
                          </small>
                        </div>
                        <span className="cf-status approved">Eligible</span>
                      </>
                    );
                  })()}
                </div>
              )}

              <div className="cf-form-divider" />

              <div className="cf-form-group">
                <label>
                  Overall Rating <span>*</span>
                </label>
                <div className="cf-rating-selector">
                  <StarRating
                    rating={rating}
                    interactive
                    onChange={setRating}
                    size="large"
                  />
                  <span>
                    {rating === 0
                      ? "Select a rating"
                      : [
                          "",
                          "Poor",
                          "Fair",
                          "Good",
                          "Very Good",
                          "Excellent",
                        ][rating]}
                  </span>
                </div>
              </div>

              <div className="cf-form-divider" />

              <h3 className="cf-criteria-title">Performance Assessment</h3>
              <p className="cf-criteria-description">
                Rate the Contributor across the following areas.
              </p>

              {[
                {
                  label: "Quality of Work",
                  value: quality,
                  setter: setQuality,
                  options: ["Needs Improvement", "Good", "Excellent"],
                },
                {
                  label: "Communication",
                  value: communication,
                  setter: setCommunication,
                  options: ["Needs Improvement", "Good", "Excellent"],
                },
                {
                  label: "Reliability & Timeliness",
                  value: reliability,
                  setter: setReliability,
                  options: ["Needs Improvement", "Good", "Excellent"],
                },
              ].map((criterion) => (
                <div className="cf-criterion-row" key={criterion.label}>
                  <label>{criterion.label}</label>
                  <div className="cf-criterion-options">
                    {criterion.options.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={
                          criterion.value === option ? "selected" : ""
                        }
                        onClick={() => criterion.setter(option)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              ))}

              <div className="cf-form-divider" />

              <div className="cf-form-group">
                <label htmlFor="cf-comment">
                  Written Feedback <span>*</span>
                </label>
                <textarea
                  id="cf-comment"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder="Describe the Contributor's work quality, professionalism, communication and overall performance..."
                  rows={5}
                  maxLength={1000}
                  required
                />
                <div className="cf-character-count">
                  {comment.length}/1000 characters
                </div>
              </div>

              <div className="cf-privacy-note">
                <span>ⓘ</span>
                <p>
                  Your feedback will be submitted to the Admin for review.
                  Only approved feedback will be published and used in public
                  ratings.
                </p>
              </div>

              <div className="cf-form-actions">
                <button
                  type="button"
                  className="cf-secondary-button"
                  onClick={() => {
                    setSelectedContributor("");
                    setRating(0);
                    setComment("");
                    setQuality("");
                    setCommunication("");
                    setReliability("");
                  }}
                >
                  Clear Form
                </button>

                <button
                  type="submit"
                  className="cf-primary-button"
                  disabled={
                    !selectedContributor || rating === 0 || !comment.trim()
                  }
                >
                  Submit Feedback <span>→</span>
                </button>
              </div>
            </form>
          </div>
        </section>
      )}
    </div>
  );
};

export default CreatorFeedback;
