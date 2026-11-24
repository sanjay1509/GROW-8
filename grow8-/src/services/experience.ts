// The contributor's verified record: GET /contributors/me/experience.
// Totals come from the database view v_contributor_verified_hours, so this page agrees
// with badges and the leaderboard.

import { apiRequest } from "./api";

export interface CompletedWork {
  application_id: number;
  submission_id: number;
  opportunity: { opportunity_id: number; title: string };
  organization: { organization_id: number; name: string };
  description: string;
  /** Decimal as a string, e.g. "5.00". */
  verified_hours: string;
  comment: string | null;
  verified_at: string;
}

export interface Experience {
  verified_hours: string;
  completed_opportunities: number;
  organizations: number;
  verified_skills: { code: string; name: string; verified_at: string | null }[];
  completed_work: CompletedWork[];
}

export function getMyExperience(): Promise<Experience> {
  return apiRequest<Experience>("/contributors/me/experience");
}
