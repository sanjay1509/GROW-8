// The creator's own name (PATCH /auth/me) and organization (GET/PATCH
// /creators/me/organization). See ADR 0017 and ADR 0018.

import { ApiError, apiRequest } from "./api";
import type { Me } from "./account";

export type OrganizationType = "small_business" | "nonprofit" | "event_organizer" | "other";

export interface Organization {
  organization_id: number;
  name: string;
  organization_type: OrganizationType;
  description: string | null;
  website: string | null;
  city: string | null;
  updated_at: string;
}

export type OrganizationChanges = Partial<{
  name: string;
  organization_type: OrganizationType;
  description: string | null;
  website: string | null;
  city: string | null;
}>;

export const ORGANIZATION_TYPES: { value: OrganizationType; label: string }[] = [
  { value: "small_business", label: "Small business" },
  { value: "nonprofit", label: "Nonprofit" },
  { value: "event_organizer", label: "Event organizer" },
  { value: "other", label: "Other" },
];

export function organizationTypeLabel(value: string | null | undefined): string {
  return ORGANIZATION_TYPES.find((item) => item.value === value)?.label ?? "—";
}

export const ORGANIZATION_MESSAGES: Record<string, string> = {
  ORGANIZATION_REQUIRED: "Add your organization's name and type to create it.",
  ROLE_FORBIDDEN: "Only creator accounts have an organization.",
};

/** Change your own name. Email can't be changed, so only full_name is sent. */
export function updateMyName(fullName: string): Promise<Me> {
  return apiRequest<Me>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify({ full_name: fullName.trim() }),
  });
}

/** After a name change: remember it and let the navbars show it straight away. */
export function rememberUserName(fullName: string): void {
  localStorage.setItem("user_name", fullName);
  window.dispatchEvent(new Event("grow8:user-name-changed"));
}

/** The creator's organization, or null when they haven't created one yet. */
export async function getMyOrganization(): Promise<Organization | null> {
  try {
    return await apiRequest<Organization>("/creators/me/organization");
  } catch (error) {
    if (error instanceof ApiError && error.code === "ORGANIZATION_NOT_FOUND") {
      return null;
    }
    throw error;
  }
}

/** Only the fields sent change. The first save must include name and type. */
export function updateMyOrganization(changes: OrganizationChanges): Promise<Organization> {
  return apiRequest<Organization>("/creators/me/organization", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}
