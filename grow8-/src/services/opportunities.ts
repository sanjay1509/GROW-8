
import { API_BASE_URL, apiRequest } from "./api";

// ==================================================
// API TYPES
// ==================================================

export interface ApiOpportunity {
  opportunity_id: number;
  title: string;
  description: string;
  status: "draft" | "open" | "closed" | "cancelled";

  category?: {
    code: string;
    name: string;
  };

  location?: string | null;
  work_mode?: string;
  expected_hours?: number | null;
  application_deadline?: string | null;
  created_at?: string | null;
  published_at?: string | null;
  compensation_type?: string;
  compensation_amount?: number | null;
  organization?: {
    organization_id: number;
    name: string;
    organization_type?: string;
    city?: string | null;
  } | null;
  skills?: { code: string; name: string }[];
}

// ==================================================
// FRONTEND OPPORTUNITY TYPE
// ==================================================

export interface Opportunity {
  id: number;
  opportunity_id?: number;
  title: string;
  description: string;
  status?: "draft" | "open" | "closed" | "cancelled";
  category: string;
  location: string;
  workMode: string;
  expectedHours: number | null;
  deadline: string | null;
  createdAt?: string | null;
  publishedAt?: string | null;
  compensationType?: string;
  compensationAmount?: number | null;
  /** The organization's name, as cards and details show it. */
  organization?: string;
  /** Names of the skills the opportunity needs. */
  skills?: string[];
}

// ==================================================
// API RESPONSE TYPE
// ==================================================

interface OpportunityListResponse {
  items: ApiOpportunity[];
  total?: number;
  limit?: number;
  offset?: number;
}

// ==================================================
// MAP API RESPONSE TO FRONTEND FORMAT
// ==================================================

function mapOpportunity(item: ApiOpportunity): Opportunity {
  return {
    id: item.opportunity_id,
    opportunity_id: item.opportunity_id,
    title: item.title,
    description: item.description,
    status: item.status,
    category: item.category?.name || "Other",
    location: item.location || "Not specified",
    workMode: item.work_mode || "Not specified",
    expectedHours: item.expected_hours ?? null,
    deadline: item.application_deadline ?? null,
    createdAt: item.created_at ?? null,
    publishedAt: item.published_at ?? null,
    compensationType: item.compensation_type,
    compensationAmount: item.compensation_amount ?? null,
    organization: item.organization?.name ?? undefined,
    skills: Array.isArray(item.skills) ? item.skills.map((skill) => skill.name) : [],
  };
}

// ==================================================
// FETCH PUBLIC OPPORTUNITIES
// ==================================================

export async function fetchOpportunities(
  options: { signal?: AbortSignal } = {}
): Promise<Opportunity[]> {
  const response = await fetch(
    `${API_BASE_URL}/opportunities?limit=100&offset=0&sort=deadline`,
    { signal: options.signal }
  );

  if (!response.ok) {
    throw new Error(
      `Unable to fetch opportunities (HTTP ${response.status}).`
    );
  }

  const data: unknown = await response.json();

  let opportunities: ApiOpportunity[] = [];

  if (Array.isArray(data)) {
    opportunities = data as ApiOpportunity[];
  } else if (
    data &&
    typeof data === "object" &&
    "items" in data &&
    Array.isArray((data as OpportunityListResponse).items)
  ) {
    opportunities = (data as OpportunityListResponse).items;
  }

  return opportunities.map(mapOpportunity);
}

// ==================================================
// CREATOR: CLOSE OPPORTUNITY
// ==================================================

export async function closeOpportunity(
  opportunityId: number | string
): Promise<ApiOpportunity> {
  return apiRequest<ApiOpportunity>(
    `/opportunities/${opportunityId}/close`,
    {
      method: "POST",
    }
  );
}

// ==================================================
// CREATOR: CANCEL OPPORTUNITY
// ==================================================

export async function cancelOpportunity(
  opportunityId: number | string
): Promise<ApiOpportunity> {
  return apiRequest<ApiOpportunity>(
    `/opportunities/${opportunityId}/cancel`,
    {
      method: "POST",
    }
  );
}
