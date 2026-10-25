
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

interface ApiSkill {
  name?: string | null;
}

interface ApiCategory {
  name?: string | null;
  code?: string | null;
}

interface ApiOrganization {
  name?: string | null;
  city?: string | null;
}

interface ApiOpportunity {
  opportunity_id: number | string;
  title?: string | null;
  category?: ApiCategory | null;
  expected_hours?: number | string | null;
  work_mode?: string | null;
  organization?: ApiOrganization | null;
  location?: string | null;
  application_deadline?: string | null;
  skills?: (string | ApiSkill)[] | null;
  description?: string | null;
  requirements?: string | null;
  working_conditions?: string | null;
  safety_information?: string | null;
  accessibility_details?: string | null;
  compensation_type?: string | null;
  compensation_amount?: number | string | null;
}

export interface Opportunity {
  id: number | string;
  title: string;
  organization: string;
  location: string;
  mode: string;
  category: string;
  hours: string;
  hoursValue: number;
  deadline: string;
  skills: string[];
  description: string;
  requirements: string;
  workingConditions: string;
  safetyInformation: string;
  accessibilityDetails: string;
  compensationType: string;
  compensationAmount: number | string | null;
  icon: "event" | "social";
  color: "red" | "blue";
}

interface OpportunitiesApiResponse {
  items: ApiOpportunity[];
  total: number;
}

interface FetchOpportunitiesOptions {
  signal?: AbortSignal;
}

const workModeMap: Record<string, string> = {
  remote: "Remote",
  on_site: "On-site",
  onsite: "On-site",
  hybrid: "Hybrid",
};

export function mapApiOpportunity(
  item: ApiOpportunity
): Opportunity {
  const category =
    item.category?.name || item.category?.code || "General";

  const hoursValue = Number(item.expected_hours || 0);

  return {
    id: item.opportunity_id,
    title: item.title || "Untitled opportunity",
    organization: item.organization?.name || "Organization",

    location:
      [item.location, item.organization?.city]
        .filter((value): value is string => Boolean(value))
        .join(", ") || "Location not specified",

    mode:
      workModeMap[String(item.work_mode || "").toLowerCase()] ||
      item.work_mode ||
      "Flexible",

    category,

    hours: hoursValue ? `${hoursValue} hrs` : "Flexible hours",
    hoursValue,

    deadline: item.application_deadline
      ? String(item.application_deadline).slice(0, 10)
      : "",

    skills: (item.skills || [])
      .map((skill) =>
        typeof skill === "string" ? skill : skill.name
      )
      .filter((skill): skill is string => Boolean(skill)),

    description: item.description || "",
    requirements: item.requirements || "",
    workingConditions: item.working_conditions || "",
    safetyInformation: item.safety_information || "",
    accessibilityDetails: item.accessibility_details || "",

    compensationType: item.compensation_type || "",
    compensationAmount: item.compensation_amount ?? null,

    icon: category.toLowerCase().includes("community")
      ? "event"
      : "social",

    color: category.toLowerCase().includes("community")
      ? "red"
      : "blue",
  };
}

export async function fetchOpportunities(
  { signal }: FetchOpportunitiesOptions = {}
): Promise<{ items: Opportunity[]; total: number }> {
  const response = await fetch(
    `${API_BASE_URL}/opportunities?limit=100&offset=0&sort=deadline`,
    { signal }
  );

  if (!response.ok) {
    throw new Error(
      `Could not load opportunities (HTTP ${response.status}).`
    );
  }

  const result: OpportunitiesApiResponse = await response.json();

  if (!Array.isArray(result.items)) {
    throw new Error(
      "Unexpected API response: expected an items array."
    );
  }

  return {
    items: result.items.map(mapApiOpportunity),
    total: result.total,
  };
}
