// Creator workspace data: the creator's opportunities and the applications they received,
// closing/cancelling opportunities, and mapping API data to the dashboard components' shapes.
// Application calls come from ./applications; this adds what the creator pages need on top.

import { ApiError, apiRequest } from "./api";
import { getReceivedApplications } from "./applications";
import type {
  Application,
  ApplicationStatus,
  OpportunityStatus as ApiOpportunityStatus,
} from "./applications";
import type {
  ApplicantStatus,
  Application as DashboardApplication,
  Opportunity as DashboardOpportunity,
  OpportunityStatus,
} from "../data/creatorDashboardData";

export interface CreatorOpportunity {
  opportunity_id: number;
  title: string;
  description: string;
  status: ApiOpportunityStatus;
  category?: { code: string; name: string } | null;
  location?: string | null;
  work_mode?: string | null;
  expected_hours?: number | string | null;
  application_deadline?: string | null;
  compensation_type?: string | null;
  compensation_amount?: number | string | null;
  organization?: { organization_id: number; name: string; city?: string | null } | null;
}

interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------- errors

const CREATOR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: "Please sign in to continue.",
  INVALID_TOKEN: "Your session has expired. Please sign in again.",
  ROLE_FORBIDDEN: "Only creator accounts can do this.",
  NOT_OPPORTUNITY_OWNER: "This opportunity belongs to another organization.",
  OPPORTUNITY_NOT_FOUND: "This opportunity could not be found.",
  OPPORTUNITY_NOT_OPEN: "Only an open opportunity can be closed.",
  OPPORTUNITY_NOT_PUBLISHED: "A draft can't be cancelled. Delete it instead.",
  OPPORTUNITY_CANCELLED: "This opportunity was cancelled, so its applications can't be decided.",
  WORK_ALREADY_SUBMITTED: "Work has already been submitted for this opportunity, so it can't be cancelled.",
  APPLICATION_NOT_FOUND: "This application could not be found.",
  APPLICATION_NOT_PENDING: "This application has already been decided or withdrawn.",
  RESUME_NOT_FOUND: "This applicant has no resume, or it is no longer available.",
};

export function friendlyError(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof ApiError) {
    return CREATOR_MESSAGES[error.code] || error.message || fallback;
  }
  if (error instanceof TypeError) {
    return "Can't reach the server. Check that the backend is running.";
  }
  return error instanceof Error && error.message ? error.message : fallback;
}

// ---------------------------------------------------------------- requests

/** Every item from a paginated endpoint, 100 at a time. */
async function collectAll<T>(fetchPage: (offset: number) => Promise<Page<T>>): Promise<T[]> {
  const all: T[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await fetchPage(offset);
    all.push(...page.items);
    if (all.length >= page.total || page.items.length === 0) {
      return all;
    }
  }
}

export function fetchMyOpportunities(): Promise<CreatorOpportunity[]> {
  return collectAll((offset) =>
    apiRequest<Page<CreatorOpportunity>>(`/opportunities/mine?limit=100&offset=${offset}`)
  );
}

/** Applications to every opportunity the creator owns, newest first. */
export function fetchAllReceivedApplications(): Promise<Application[]> {
  return collectAll((offset) => getReceivedApplications({ limit: 100, offset }));
}

// ADR 0011. Close: open -> closed (no new applications). Cancel: open or closed -> cancelled.
export function closeOpportunity(opportunityId: number): Promise<CreatorOpportunity> {
  return apiRequest<CreatorOpportunity>(`/opportunities/${opportunityId}/close`, { method: "POST" });
}

export function cancelOpportunity(opportunityId: number): Promise<CreatorOpportunity> {
  return apiRequest<CreatorOpportunity>(`/opportunities/${opportunityId}/cancel`, { method: "POST" });
}

// ---------------------------------------------------------------- dashboard mapping

const OPPORTUNITY_STATUS: Record<ApiOpportunityStatus, OpportunityStatus> = {
  draft: "Draft",
  open: "Open",
  closed: "Completed",
  cancelled: "Cancelled",
};

const APPLICANT_STATUS: Record<ApplicationStatus, ApplicantStatus> = {
  pending: "Under Review",
  accepted: "Selected",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

// Same wording as My Opportunities.
function compensation(item: CreatorOpportunity): string {
  if (item.compensation_type === "stipend" && item.compensation_amount != null) {
    return `$${item.compensation_amount} stipend`;
  }
  if (item.compensation_type === "paid" && item.compensation_amount != null) {
    return `$${item.compensation_amount} paid`;
  }
  if (item.compensation_type === "unpaid") {
    return "Volunteer / Unpaid";
  }
  return item.compensation_type ? item.compensation_type.replaceAll("_", " ") : "Not specified";
}

export function toDashboardOpportunity(
  item: CreatorOpportunity,
  applications: Application[]
): DashboardOpportunity {
  return {
    id: item.opportunity_id,
    title: item.title,
    description: item.description,
    applications: applications.filter((a) => a.opportunity.opportunity_id === item.opportunity_id).length,
    status: OPPORTUNITY_STATUS[item.status],
    category: item.category?.code === "community" ? "community" : "digital",
    location: item.location || item.work_mode?.replaceAll("_", " ") || "Not specified",
    deadline: item.application_deadline ? item.application_deadline.slice(0, 10) : "",
    expectedHours: Number(item.expected_hours ?? 0),
    compensation: compensation(item),
  };
}

export function toDashboardApplication(item: Application): DashboardApplication {
  return {
    id: item.application_id,
    name: item.applicant.full_name,
    initials: initials(item.applicant.full_name),
    email: "", // contact details are not shared with creators
    opportunityId: item.opportunity.opportunity_id,
    appliedDate: formatDate(item.submitted_at),
    status: APPLICANT_STATUS[item.status],
    bio: item.applicant.headline ?? "",
    skills: item.applicant.skills.map((skill) => skill.name),
  };
}
