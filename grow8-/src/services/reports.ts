// Contributors report a misleading or unsafe opportunity and follow the outcome (ADR 0016).
// The creator never learns who reported.

import { apiRequest } from "./api";

export type ReportReason =
  | "misleading_terms"
  | "unsafe_conditions"
  | "discriminatory"
  | "scam_or_spam"
  | "other";

export type ReportStatus = "pending" | "upheld" | "dismissed";

export interface OpportunityReport {
  report_id: number;
  opportunity: { opportunity_id: number; title: string; status: string };
  reason: ReportReason;
  details: string | null;
  created_at: string;
  status: ReportStatus;
  review: { decision: "upheld" | "dismissed"; reason: string | null; reviewed_at: string } | null;
}

export interface ReportList {
  items: OpportunityReport[];
  total: number;
  limit: number;
  offset: number;
}

export const REPORT_REASONS: { value: ReportReason; label: string; hint: string }[] = [
  {
    value: "misleading_terms",
    label: "Misleading terms",
    hint: "Pay, hours or duties don't match what's described.",
  },
  {
    value: "unsafe_conditions",
    label: "Unsafe conditions",
    hint: "The work or place could put people at risk.",
  },
  {
    value: "discriminatory",
    label: "Discriminatory",
    hint: "It excludes people unfairly, for example by age, gender or origin.",
  },
  {
    value: "scam_or_spam",
    label: "Scam or spam",
    hint: "It isn't a real opportunity, or asks for money or personal data.",
  },
  { value: "other", label: "Something else", hint: "Tell us in the details." },
];

export function reasonLabel(reason: ReportReason): string {
  return REPORT_REASONS.find((item) => item.value === reason)?.label ?? reason;
}

export const REPORT_MESSAGES: Record<string, string> = {
  OPPORTUNITY_ALREADY_REPORTED: "You've already reported this opportunity.",
  OPPORTUNITY_CANCELLED: "This opportunity has already been cancelled.",
  OPPORTUNITY_NOT_FOUND: "This opportunity is no longer available.",
  ROLE_FORBIDDEN: "Only contributors can report opportunities.",
};

export function reportOpportunity(
  opportunityId: number,
  reason: ReportReason,
  details?: string
): Promise<OpportunityReport> {
  const trimmed = details?.trim();
  return apiRequest<OpportunityReport>(`/opportunities/${opportunityId}/reports`, {
    method: "POST",
    body: JSON.stringify(trimmed ? { reason, details: trimmed } : { reason }),
  });
}

export function getMyReports(limit = 50, offset = 0): Promise<ReportList> {
  return apiRequest<ReportList>(`/reports/mine?limit=${limit}&offset=${offset}`);
}
