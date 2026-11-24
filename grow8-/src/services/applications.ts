
import {
  API_BASE_URL,
  apiRequest,
  authHeaders,
  handleUnauthorized,
} from "./api";
import type { WorkStatus } from "./submissions";

// --------------------------------------------------
// Types
// --------------------------------------------------

export type ApplicationStatus =
  | "pending"
  | "accepted"
  | "rejected"
  | "withdrawn";

export type OpportunityStatus =
  | "draft"
  | "open"
  | "closed"
  | "cancelled";

export interface ApplicationSkill {
  code: string;
  name: string;
}

export interface ApplicationOrganization {
  organization_id: number;
  name: string;
  organization_type?: string;
  city?: string | null;
}

export interface ApplicationOpportunity {
  opportunity_id: number;
  title: string;
  status: OpportunityStatus;
  application_deadline: string;
  organization: ApplicationOrganization;
}

export interface ApplicationApplicant {
  user_id: number;
  full_name: string;
  headline?: string | null;
  institution?: string | null;
  city?: string | null;
  skills: ApplicationSkill[];
  has_resume: boolean;
}

export interface Application {
  application_id: number;
  status: ApplicationStatus;
  motivation?: string | null;
  application_details?: Record<string, string>;
  submitted_at: string;
  decided_at: string | null;
  opportunity: ApplicationOpportunity;
  applicant: ApplicationApplicant;
  /** The submitted work's id, or null until the applicant submits work. */
  submission_id: number | null;
  /** not_submitted, awaiting_verification, completed or work_rejected (derived). */
  work_status: WorkStatus;
}

export interface ApplicationListResponse {
  items: Application[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApplicationListOptions {
  status?: ApplicationStatus | ApplicationStatus[];
  opportunity_id?: number;
  limit?: number;
  offset?: number;
}

// --------------------------------------------------
// Query helper
// --------------------------------------------------

function buildApplicationQuery(
  options: ApplicationListOptions = {}
): string {
  const params = new URLSearchParams();

  if (options.status) {
    const statuses = Array.isArray(options.status)
      ? options.status
      : [options.status];

    statuses.forEach((status) => {
      params.append("status", status);
    });
  }

  if (options.opportunity_id !== undefined) {
    params.set(
      "opportunity_id",
      String(options.opportunity_id)
    );
  }

  params.set("limit", String(options.limit ?? 20));
  params.set("offset", String(options.offset ?? 0));

  return `?${params.toString()}`;
}

// --------------------------------------------------
// Contributor: Apply
// --------------------------------------------------

export async function applyToOpportunity(
  opportunityId: number | string,
  motivation?: string,
  applicationDetails: Record<string, string> = {},
  resume?: File | null
): Promise<Application> {
  const body = new FormData();
  if (motivation?.trim()) body.append("motivation", motivation.trim());
  body.append("application_details", JSON.stringify(applicationDetails));
  if (resume) body.append("resume", resume);

  return apiRequest<Application>(
    `/opportunities/${opportunityId}/applications`,
    {
      method: "POST",
      body,
    }
  );
}

// --------------------------------------------------
// Contributor: My applications
// --------------------------------------------------

export async function getMyApplications(
  options: ApplicationListOptions = {}
): Promise<ApplicationListResponse> {
  return apiRequest<ApplicationListResponse>(
    `/applications/mine${buildApplicationQuery(options)}`
  );
}

// --------------------------------------------------
// Creator: Applications received
// --------------------------------------------------

export async function getReceivedApplications(
  options: ApplicationListOptions = {}
): Promise<ApplicationListResponse> {
  return apiRequest<ApplicationListResponse>(
    `/applications/received${buildApplicationQuery(options)}`
  );
}

// --------------------------------------------------
// Creator: Applications for one opportunity
// --------------------------------------------------

export async function getOpportunityApplications(
  opportunityId: number | string,
  options: Omit<ApplicationListOptions, "opportunity_id"> = {}
): Promise<ApplicationListResponse> {
  return apiRequest<ApplicationListResponse>(
    `/opportunities/${opportunityId}/applications${buildApplicationQuery(options)}`
  );
}

// --------------------------------------------------
// Both: Get one application
// --------------------------------------------------

export async function getApplication(
  applicationId: number | string
): Promise<Application> {
  return apiRequest<Application>(
    `/applications/${applicationId}`
  );
}

// --------------------------------------------------
// Creator: Accept or reject
// --------------------------------------------------

export type ApplicationDecision = "accepted" | "rejected";

export async function decideApplication(
  applicationId: number | string,
  decision: ApplicationDecision
): Promise<Application> {
  return apiRequest<Application>(
    `/applications/${applicationId}/decision`,
    {
      method: "POST",
      body: JSON.stringify({ decision }),
    }
  );
}

// --------------------------------------------------
// Contributor: Withdraw
// --------------------------------------------------

export async function withdrawApplication(
  applicationId: number | string
): Promise<Application> {
  return apiRequest<Application>(
    `/applications/${applicationId}/withdraw`,
    {
      method: "POST",
    }
  );
}

// --------------------------------------------------
// Creator: Download applicant resume
// --------------------------------------------------

export async function downloadApplicationResume(
  applicationId: number | string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/applications/${applicationId}/resume`,
    {
      method: "GET",
      headers: authHeaders(),
    }
  );

  if (response.status === 401) {
    handleUnauthorized();
  }

  if (!response.ok) {
    throw new Error(
      `Could not download resume (HTTP ${response.status}).`
    );
  }

  const blob = await response.blob();

  const disposition = response.headers.get(
    "Content-Disposition"
  );

  let filename = `application-${applicationId}-resume.pdf`;

  if (disposition) {
    const encodedMatch = disposition.match(
      /filename\*=UTF-8''([^;]+)/i
    );

    const regularMatch = disposition.match(
      /filename="?([^";]+)"?/i
    );

    if (encodedMatch?.[1]) {
      filename = decodeURIComponent(encodedMatch[1]);
    } else if (regularMatch?.[1]) {
      filename = regularMatch[1];
    }
  }

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}
