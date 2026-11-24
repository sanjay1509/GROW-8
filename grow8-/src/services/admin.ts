// Admin review queues: feedback (ADR 0015) and opportunity reports with takedown
// (ADR 0016). Admin-only; anyone else gets 403 ROLE_FORBIDDEN.

import { apiRequest } from "./api";
import type { Feedback, FeedbackStatus } from "./feedback";
import type { OpportunityReport, ReportStatus } from "./reports";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminReport extends OpportunityReport {
  reporter: { user_id: number; full_name: string };
  creator: { user_id: number; full_name: string };
  open_reports_on_opportunity: number;
}

export const ADMIN_MESSAGES: Record<string, string> = {
  FEEDBACK_ALREADY_REVIEWED: "Another admin already reviewed this feedback. The list has been refreshed.",
  REPORT_ALREADY_REVIEWED: "Another admin already reviewed this report. The list has been refreshed.",
  REJECTION_REASON_REQUIRED: "Give a reason for rejecting this feedback.",
  TAKEDOWN_REASON_REQUIRED: "Give a reason for taking the opportunity down. The organization will see it.",
  WORK_ALREADY_SUBMITTED:
    "Work was already submitted for this opportunity, so it can't be taken down. You can only dismiss the report.",
  OPPORTUNITY_CANCELLED: "This opportunity is already cancelled.",
  ROLE_FORBIDDEN: "Only admins can do this.",
};

function query(params: Record<string, string | number | boolean | string[] | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, item));
    } else {
      search.set(key, String(value));
    }
  });
  return search.toString();
}

// --------------------------------------------------
// Feedback review
// --------------------------------------------------

export function getFeedbackQueue(
  options: { status?: FeedbackStatus[]; discrepancy?: boolean; limit?: number; offset?: number } = {}
): Promise<Page<Feedback>> {
  return apiRequest<Page<Feedback>>(
    `/admin/feedback?${query({
      status: options.status,
      discrepancy: options.discrepancy,
      limit: options.limit ?? 20,
      offset: options.offset ?? 0,
    })}`
  );
}

export function reviewFeedback(
  feedbackId: number,
  decision: "approved" | "rejected",
  reason?: string
): Promise<Feedback> {
  const trimmed = reason?.trim();
  return apiRequest<Feedback>(`/admin/feedback/${feedbackId}/review`, {
    method: "POST",
    body: JSON.stringify(trimmed ? { decision, reason: trimmed } : { decision }),
  });
}

// --------------------------------------------------
// Reports and takedown
// --------------------------------------------------

export function getReportQueue(
  options: { status?: ReportStatus[]; opportunity_id?: number; limit?: number; offset?: number } = {}
): Promise<Page<AdminReport>> {
  return apiRequest<Page<AdminReport>>(
    `/admin/reports?${query({
      status: options.status,
      opportunity_id: options.opportunity_id,
      limit: options.limit ?? 50,
      offset: options.offset ?? 0,
    })}`
  );
}

/** "upheld" takes the opportunity down (cancels it) and upholds every pending report on it. */
export function reviewReport(
  reportId: number,
  decision: "upheld" | "dismissed",
  reason?: string
): Promise<AdminReport> {
  const trimmed = reason?.trim();
  return apiRequest<AdminReport>(`/admin/reports/${reportId}/review`, {
    method: "POST",
    body: JSON.stringify(trimmed ? { decision, reason: trimmed } : { decision }),
  });
}
