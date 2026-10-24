
const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  "http://localhost:8000/api/v1";

export function mapApiOpportunity(item) {
  const category =
    item.category?.name || item.category?.code || "General";

  const hoursValue = Number(item.expected_hours || 0);

  const workModeMap = {
    remote: "Remote",
    on_site: "On-site",
    onsite: "On-site",
    hybrid: "Hybrid",
  };

  return {
    id: item.opportunity_id,
    title: item.title || "Untitled opportunity",
    organization: item.organization?.name || "Organization",

    location:
      [item.location, item.organization?.city]
        .filter(Boolean)
        .join(", ") || "Location not specified",

    mode:
      workModeMap[String(item.work_mode || "").toLowerCase()] ||
      item.work_mode ||
      "Flexible",

    category,
    hours: hoursValue
      ? `${hoursValue} hrs`
      : "Flexible hours",
    hoursValue,

    deadline: item.application_deadline
      ? String(item.application_deadline).slice(0, 10)
      : "",

    skills: (item.skills || []).map((skill) =>
      typeof skill === "string" ? skill : skill.name
    ).filter(Boolean),

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

export async function fetchOpportunities({ signal } = {}) {
  const response = await fetch(
    `${API_BASE_URL}/opportunities?limit=100&offset=0&sort=deadline`,
    { signal }
  );

  if (!response.ok) {
    throw new Error(
      `Could not load opportunities (HTTP ${response.status}).`
    );
  }

  const result = await response.json();

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
