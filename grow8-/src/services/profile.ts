// Contributor profile and skills: GET/PATCH /contributors/me/profile,
// PUT /contributors/me/skills and the skill list (GET /skills). See ADR 0017 and 0019.

import { apiRequest } from "./api";

export interface Skill {
  code: string;
  name: string;
}

export interface ProfileSkill extends Skill {
  /** On the contributor's profile (used for matching new opportunities). */
  listed: boolean;
  /** Proved by work a creator approved. */
  verified: boolean;
  verified_at: string | null;
}

export interface ContributorProfile {
  user_id: number;
  full_name: string;
  email: string;
  headline: string | null;
  bio: string | null;
  institution: string | null;
  city: string | null;
  skills: ProfileSkill[];
  has_resume: boolean;
  /** null until the profile has been saved once. */
  updated_at: string | null;
}

export type ProfileChanges = Partial<
  Record<"full_name" | "headline" | "bio" | "institution" | "city", string | null>
>;

export const MAX_LISTED_SKILLS = 25;

export function getSkills(): Promise<Skill[]> {
  return apiRequest<Skill[]>("/skills");
}

export function getMyProfile(): Promise<ContributorProfile> {
  return apiRequest<ContributorProfile>("/contributors/me/profile");
}

/** Send only the fields that changed; null clears an optional field. */
export function updateMyProfile(changes: ProfileChanges): Promise<ContributorProfile> {
  return apiRequest<ContributorProfile>("/contributors/me/profile", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

/** Replaces the listed skills. Earned (verified) skills are never removed. */
export function setMySkills(skillCodes: string[]): Promise<ContributorProfile> {
  return apiRequest<ContributorProfile>("/contributors/me/skills", {
    method: "PUT",
    body: JSON.stringify({ skill_codes: skillCodes }),
  });
}
