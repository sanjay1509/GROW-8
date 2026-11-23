// Feedback between the contributor and the creator, and public ratings (ADR 0015).
// Only feedback an admin approves is shown to the person rated and counts toward ratings.

import { API_BASE_URL, apiRequest } from "./api";

export type FeedbackStatus = "pending" | "approved" | "rejected";

export interface Feedback {
  feedback_id: number;
  application_id: number;
  opportunity: { opportunity_id: number; title: string };
  author: { user_id: number; full_name: string };
  subject: { user_id: number; full_name: string };
  rating: number;
  comment: string | null;
  reports_discrepancy: boolean;
  created_at: string;
  status: FeedbackStatus;
  review: { decision: "approved" | "rejected"; reason: string | null; reviewed_at: string } | null;
}

export interface ApplicationFeedback {
  /** Yours, in any status. */
  given: Feedback | null;
  /** Theirs about you, only once an admin approved it. */
  received: Feedback | null;
}

export interface UserRating {
  user_id: number;
  /** Two-decimal string, or null with no approved feedback. */
  average_rating: string | null;
  approved_feedback_count: number;
}

export interface FeedbackBody {
  rating: number;
  comment?: string;
  reports_discrepancy?: boolean;
}

export const FEEDBACK_MESSAGES: Record<string, string> = {
  WORK_NOT_VERIFIED: "Feedback opens once the work has been verified.",
  FEEDBACK_ALREADY_SUBMITTED: "You've already left feedback for this application.",
  APPLICATION_NOT_FOUND: "This application is no longer available.",
};

export function getApplicationFeedback(applicationId: number): Promise<ApplicationFeedback> {
  return apiRequest<ApplicationFeedback>(`/applications/${applicationId}/feedback`);
}

export function leaveFeedback(applicationId: number, body: FeedbackBody): Promise<Feedback> {
  return apiRequest<Feedback>(`/applications/${applicationId}/feedback`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

const ratingCache = new Map<number, Promise<UserRating>>();

/**
 * Public rating of a user. No token needed, so plain fetch: a failure here should never
 * sign anyone out. Cached for the page's lifetime because lists ask for the same people.
 */
export function getUserRating(userId: number): Promise<UserRating> {
  const cached = ratingCache.get(userId);
  if (cached) {
    return cached;
  }
  const request = fetch(`${API_BASE_URL}/users/${userId}/rating`).then(async (response) => {
    if (!response.ok) {
      throw new Error(`Rating unavailable (HTTP ${response.status}).`);
    }
    return (await response.json()) as UserRating;
  });
  request.catch(() => ratingCache.delete(userId));
  ratingCache.set(userId, request);
  return request;
}
