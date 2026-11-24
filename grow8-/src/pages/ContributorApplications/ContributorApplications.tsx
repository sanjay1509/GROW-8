
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Download,
  Eye,
  RefreshCw,
  RotateCcw,
  X,
} from "lucide-react";

import {
  getMyApplications,
  downloadApplicationResume,
  withdrawApplication,
  type ApplicationStatus,
} from "../../services/applications";

import { ApiError } from "../../services/api";
import type { WorkStatus } from "../../services/submissions";
import WorkSection from "./WorkSection";
import "./ContributorApplications.css";

type ApplicationRow = {
  application_id: number;
  status: ApplicationStatus;
  submitted_at?: string | null;
  decided_at?: string | null;
  motivation?: string | null;
  application_details?: Record<string, string>;
  applicant?: { has_resume?: boolean };
  opportunity?: {
    opportunity_id?: number;
    title?: string;
    status?: string;
    organization?: {
      name?: string;
    } | null;
    creator?: {
      organization_name?: string;
      name?: string;
    } | null;
  };
  organization?: {
    name?: string;
  } | null;
  submission_id?: number | null;
  work_status?: WorkStatus;
};

type TabValue =
  | "all"
  | "pending"
  | "accepted"
  | "rejected"
  | "withdrawn";

const PAGE_SIZE = 5;

const tabs: { label: string; value: TabValue }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "Accepted", value: "accepted" },
  { label: "Rejected", value: "rejected" },
  { label: "Withdrawn", value: "withdrawn" },
];

function formatDate(value?: string | null): string {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleDateString("en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ").replace(/\b\w/g, (character) =>
    character.toUpperCase()
  );
}

function opportunityNotice(status?: string): string | null {
  if (status === "cancelled") return "Opportunity cancelled";
  if (status === "closed") return "Applications closed";
  return null;
}

function getOrganization(application: ApplicationRow): string {
  return (
    application.organization?.name ||
    application.opportunity?.organization?.name ||
    application.opportunity?.creator?.organization_name ||
    application.opportunity?.creator?.name ||
    "Organization not available"
  );
}

export default function ContributorApplications() {
  const [searchParams] = useSearchParams();

  const opportunityId = searchParams.get("opportunity_id") || undefined;

  const [activeTab, setActiveTab] = useState<TabValue>("all");
  const [applications, setApplications] = useState<ApplicationRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [withdrawingId, setWithdrawingId] = useState<number | null>(null);
  const [viewingApplication, setViewingApplication] = useState<ApplicationRow | null>(null);
  const [downloadingResumeId, setDownloadingResumeId] = useState<number | null>(null);

  const loadApplications = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const options: {
        limit: number;
        offset: number;
        status?: ApplicationStatus[];
        opportunity_id?: number;
      } = {
        limit: PAGE_SIZE,
        offset,
      };

      if (activeTab !== "all") {
        options.status = [activeTab];
      }

      if (opportunityId && Number.isFinite(Number(opportunityId))) {
        options.opportunity_id = Number(opportunityId);
      }

      const response = await getMyApplications(options);

      setApplications(response.items as unknown as ApplicationRow[]);
      setTotal(response.total ?? response.items.length);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load your applications."
      );
    } finally {
      setLoading(false);
    }
  }, [activeTab, offset, opportunityId]);

  useEffect(() => {
    void loadApplications();
  }, [loadApplications]);

  function changeTab(tab: TabValue) {
    setActiveTab(tab);
    setOffset(0);
  }

  async function handleWithdraw(application: ApplicationRow) {
    const confirmed = window.confirm(
      `Are you sure you want to withdraw your application for "${application.opportunity?.title || "this opportunity"}"?`
    );

    if (!confirmed) return;

    setWithdrawingId(application.application_id);
    setError("");

    try {
      const updated = await withdrawApplication(
        application.application_id
      );

      // Use the response returned by the backend.
      setApplications((current) =>
        current.map((item) =>
          item.application_id === application.application_id
            ? (updated as unknown as ApplicationRow)
            : item
        )
      );

      // Refresh the current page so server-side totals and filters stay accurate.
      await loadApplications();
    } catch (err) {
      if (err instanceof ApiError) {
        const messages: Record<string, string> = {
          APPLICATION_NOT_ACTIVE:
            "This application can no longer be withdrawn.",
          APPLICATION_NOT_PENDING:
            "This application has already been updated. Please refresh the page.",
          OPPORTUNITY_CANCELLED:
            "This opportunity has been cancelled. Refresh to see the latest status.",
          WORK_ALREADY_SUBMITTED:
            "This application cannot be withdrawn because work has already been submitted.",
          INVALID_TOKEN:
            "Your session has expired. Please sign in again.",
          AUTH_REQUIRED:
            "Please sign in to withdraw an application.",
        };

        setError(
          messages[err.code] ||
            err.message ||
            "Unable to withdraw this application."
        );
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to withdraw this application."
        );
      }
    } finally {
      setWithdrawingId(null);
    }
  }

  async function handleDownloadResume(application: ApplicationRow) {
    setDownloadingResumeId(application.application_id);
    setError("");
    try {
      await downloadApplicationResume(application.application_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download this resume.");
    } finally {
      setDownloadingResumeId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <section className="contributor-applications-page">
      <header className="ca-header">
        <div>
          <span className="ca-eyebrow">CONTRIBUTOR WORKSPACE</span>
          <h1>My Applications</h1>
          <p>Track your applications and stay updated on their progress.</p>
        </div>

        <Link to="/opportunities" className="ca-browse-button">
          <BriefcaseBusiness size={18} />
          Browse Opportunities
        </Link>
      </header>

      {opportunityId && (
        <div className="ca-filter-notice">
          Showing applications for opportunity #{opportunityId}
          <Link to="/contributor/applications">Clear filter</Link>
        </div>
      )}

      <div className="ca-tabs" role="tablist" aria-label="Application status">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.value}
            className={`ca-tab ${activeTab === tab.value ? "active" : ""}`}
            onClick={() => changeTab(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="ca-list-heading">
        <div>
          <h2>
            {activeTab === "all"
              ? "All Applications"
              : `${statusLabel(activeTab)} Applications`}
          </h2>
          <p>
            {total} {total === 1 ? "application" : "applications"} found
          </p>
        </div>

        <button
          type="button"
          className="ca-refresh-button"
          onClick={() => void loadApplications()}
          disabled={loading || withdrawingId !== null}
        >
          <RefreshCw size={16} className={loading ? "ca-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="ca-error" role="alert">
          <strong>Something went wrong</strong>
          <p>{error}</p>
          <button type="button" onClick={() => void loadApplications()}>
            Try again
          </button>
        </div>
      )}

      {loading ? (
        <div className="ca-state">
          <RefreshCw size={26} className="ca-spin" />
          <p>Loading your applications...</p>
        </div>
      ) : applications.length === 0 ? (
        <div className="ca-empty">
          <span className="ca-empty-icon">
            <ClipboardList size={30} />
          </span>

          <h2>No applications found</h2>
          <p>
            {activeTab === "all"
              ? "You haven't applied to any opportunities yet. Explore available opportunities to get started."
              : `You don't have any ${activeTab} applications right now.`}
          </p>

          <Link to="/opportunities" className="ca-browse-button">
            Browse Opportunities
            <ArrowRight size={17} />
          </Link>
        </div>
      ) : (
        <>
          <div className="ca-application-list">
            {applications.map((application) => {
              const opportunityStatus =
                application.opportunity?.status?.toLowerCase();

              const notice = opportunityNotice(opportunityStatus);
              const displayStatus = opportunityStatus === "cancelled" ? "closed" : application.status;

              const canWithdraw =
                application.status === "pending" ||
                application.status === "accepted";

              return (
                <article
                  className="ca-application-card"
                  key={application.application_id}
                >
                  <div className="ca-card-main">
                    <div className="ca-card-icon">
                      <BriefcaseBusiness size={22} />
                    </div>

                    <div className="ca-card-content">
                      <div className="ca-card-title-row">
                        <div>
                          <h3>
                            {application.opportunity?.title ||
                              "Opportunity"}
                          </h3>
                          <p className="ca-organization">
                            {getOrganization(application)}
                          </p>
                        </div>

                        <span
                          className={`ca-status ca-status-${displayStatus}`}
                        >
                          {statusLabel(displayStatus)}
                        </span>
                      </div>

                      {notice && (
                        <span
                          className={`ca-opportunity-notice ca-notice-${opportunityStatus}`}
                        >
                          {notice}
                        </span>
                      )}

                      <div className="ca-dates">
                        <span>
                          <CalendarDays size={15} />
                          Applied: {formatDate(application.submitted_at)}
                        </span>

                        {application.decided_at && (
                          <span>
                            <CalendarDays size={15} />
                            Decided: {formatDate(application.decided_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="ca-card-actions">
                    <button
                      type="button"
                      className="ca-details-button"
                      onClick={() => setViewingApplication(application)}
                    >
                      <Eye size={15} /> View details
                    </button>
                    {canWithdraw && !notice && !application.submission_id && (
                      <button
                        type="button"
                        className="ca-withdraw-button"
                        onClick={() => void handleWithdraw(application)}
                        disabled={withdrawingId !== null}
                      >
                        <RotateCcw size={15} />
                        {withdrawingId === application.application_id
                          ? "Withdrawing..."
                          : "Withdraw"}
                      </button>
                    )}
                  </div>

                  {application.status === "accepted" && (
                    <WorkSection
                      applicationId={application.application_id}
                      opportunityTitle={application.opportunity?.title || "Opportunity"}
                      opportunityStatus={opportunityStatus}
                      workStatus={application.work_status ?? "not_submitted"}
                      onChanged={() => void loadApplications()}
                    />
                  )}
                </article>
              );
            })}
          </div>

          <div className="ca-pagination">
            <span>
              Page {currentPage} of {totalPages}
            </span>

            <div>
              <button
                type="button"
                onClick={() =>
                  setOffset((current) =>
                    Math.max(0, current - PAGE_SIZE)
                  )
                }
                disabled={offset === 0 || loading}
                aria-label="Previous page"
              >
                <ChevronLeft size={18} />
                Previous
              </button>

              <button
                type="button"
                onClick={() => setOffset((current) => current + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total || loading}
                aria-label="Next page"
              >
                Next
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </>
      )}

      {viewingApplication && (
        <div className="ca-modal-backdrop" role="presentation" onClick={() => setViewingApplication(null)}>
          <section
            className="ca-details-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ca-details-title"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="ca-details-modal-header">
              <div>
                <span className="ca-eyebrow">APPLICATION DETAILS</span>
                <h2 id="ca-details-title">{viewingApplication.opportunity?.title || "Opportunity"}</h2>
              </div>
              <button type="button" className="ca-details-close" aria-label="Close details" onClick={() => setViewingApplication(null)}>
                <X size={20} />
              </button>
            </header>

            <dl className="ca-details-list">
              {Object.entries(viewingApplication.application_details || {}).map(([label, value]) => (
                <div key={label}>
                  <dt>{label.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase())}</dt>
                  <dd>{value || "—"}</dd>
                </div>
              ))}
              <div>
                <dt>Motivation</dt>
                <dd>{viewingApplication.motivation || "Not provided"}</dd>
              </div>
            </dl>

            <div className="ca-details-resume">
              <div>
                <strong>Resume</strong>
                <p>{viewingApplication.applicant?.has_resume ? "Resume attached to this application." : "No resume was attached to this application."}</p>
              </div>
              {viewingApplication.applicant?.has_resume && (
                <button
                  type="button"
                  className="ca-details-button"
                  onClick={() => void handleDownloadResume(viewingApplication)}
                  disabled={downloadingResumeId === viewingApplication.application_id}
                >
                  <Download size={15} />
                  {downloadingResumeId === viewingApplication.application_id ? "Downloading..." : "Download resume"}
                </button>
              )}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
