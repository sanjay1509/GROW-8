// Work submissions and verification (ADR 0012, ADR 0013).
// Contributor: submit work for an accepted application. Creator: review queue,
// download attachments, approve with verified hours or reject with a comment.

import {
  API_BASE_URL,
  ApiError,
  apiRequest,
  authHeaders,
  handleUnauthorized,
} from "./api";
import type { ApiErrorBody } from "./api";

export type WorkStatus =
  | "not_submitted"
  | "awaiting_verification"
  | "completed"
  | "work_rejected";

export type SubmissionStatus = "awaiting" | "approved" | "rejected";

export interface Attachment {
  attachment_id: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
}

export interface Verification {
  decision: "approved" | "rejected";
  verified_hours: string | null;
  comment: string | null;
  verified_at: string;
}

export interface Submission {
  submission_id: number;
  application_id: number;
  status: SubmissionStatus;
  description: string;
  /** Decimal as a string, e.g. "6.50". */
  hours_claimed: string;
  submitted_at: string;
  opportunity: { opportunity_id: number; title: string; status: string };
  applicant: { user_id: number; full_name: string };
  attachments: Attachment[];
  verification: Verification | null;
}

export interface SubmissionList {
  items: Submission[];
  total: number;
  limit: number;
  offset: number;
}

export const MAX_ATTACHMENTS = 5;
export const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024;
export const ATTACHMENT_ACCEPT = ".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.csv,.txt";

export const WORK_MESSAGES: Record<string, string> = {
  WORK_ALREADY_SUBMITTED: "Work has already been submitted for this application.",
  OPPORTUNITY_CANCELLED: "This opportunity was cancelled, so work can't be submitted or verified.",
  APPLICATION_NOT_ACCEPTED: "Work can only be submitted for an accepted application.",
  ATTACHMENT_TOO_LARGE: "Each file must be 5 MB or smaller.",
  TOO_MANY_FILES: "You can attach up to 5 files.",
  EMPTY_FILE: "One of the files is empty.",
  UNSUPPORTED_FILE_TYPE: "Files must be PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT.",
  SUBMISSION_ALREADY_VERIFIED: "This work has already been reviewed. Refresh to see the decision.",
  VERIFIED_HOURS_EXCEED_CLAIMED: "Verified hours can't be more than the hours claimed.",
  REJECTION_COMMENT_REQUIRED: "Please explain why the work is rejected.",
  SUBMISSION_NOT_FOUND: "This submission is no longer available.",
  ATTACHMENT_NOT_FOUND: "This file is no longer available.",
};

/** "6.50" → "6.5", "5.00" → "5". */
export function formatHours(value: string | number | null | undefined): string {
  const number = Number(value);
  return Number.isFinite(number) ? String(Number(number.toFixed(2))) : "—";
}

/** A positive number with at most 2 decimals and at most 9999.99. */
export function isValidHours(value: string): boolean {
  if (!/^\d{1,4}(\.\d{1,2})?$/.test(value.trim())) {
    return false;
  }
  return Number(value) > 0;
}

// --------------------------------------------------
// Contributor
// --------------------------------------------------

/**
 * Submit work, with progress (0-100) through XMLHttpRequest, because fetch can't
 * report upload progress. Don't set Content-Type: the browser adds the boundary.
 */
export function submitWork(
  applicationId: number,
  description: string,
  hoursClaimed: string,
  files: File[],
  onProgress?: (percent: number) => void
): Promise<Submission> {
  return new Promise((resolve, reject) => {
    let headers: Record<string, string>;
    try {
      headers = authHeaders();
    } catch (error) {
      reject(error);
      return;
    }

    const form = new FormData();
    form.append("description", description.trim());
    form.append("hours_claimed", hoursClaimed.trim());
    files.forEach((file) => form.append("files", file));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/applications/${applicationId}/submission`);
    Object.entries(headers).forEach(([key, value]) => xhr.setRequestHeader(key, value));
    xhr.setRequestHeader("Accept", "application/json");

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300 && data) {
        resolve(data as Submission);
        return;
      }
      if (xhr.status === 401) {
        handleUnauthorized();
      }
      const body = data as ApiErrorBody | null;
      reject(
        new ApiError(
          body?.error?.message || `Upload failed (HTTP ${xhr.status}).`,
          xhr.status,
          body?.error?.code || "UNKNOWN_ERROR",
          body?.error?.details
        )
      );
    };
    xhr.onerror = () => reject(new TypeError("Network error"));
    xhr.send(form);
  });
}

/** The work submitted for an application (applicant or owning creator). */
export function getApplicationSubmission(applicationId: number): Promise<Submission> {
  return apiRequest<Submission>(`/applications/${applicationId}/submission`);
}

// --------------------------------------------------
// Creator
// --------------------------------------------------

export interface ReceivedSubmissionOptions {
  status?: SubmissionStatus | SubmissionStatus[];
  opportunity_id?: number;
  limit?: number;
  offset?: number;
}

/** The creator's review queue, oldest first. */
export function getReceivedSubmissions(
  options: ReceivedSubmissionOptions = {}
): Promise<SubmissionList> {
  const params = new URLSearchParams();
  const statuses = options.status
    ? Array.isArray(options.status)
      ? options.status
      : [options.status]
    : [];
  statuses.forEach((status) => params.append("status", status));
  if (options.opportunity_id !== undefined) {
    params.set("opportunity_id", String(options.opportunity_id));
  }
  params.set("limit", String(options.limit ?? 20));
  params.set("offset", String(options.offset ?? 0));
  return apiRequest<SubmissionList>(`/submissions/received?${params.toString()}`);
}

export function getSubmission(submissionId: number): Promise<Submission> {
  return apiRequest<Submission>(`/submissions/${submissionId}`);
}

export type VerificationBody =
  | { decision: "approved"; verified_hours: string; comment?: string }
  | { decision: "rejected"; comment: string };

export function verifySubmission(
  submissionId: number,
  body: VerificationBody
): Promise<Submission> {
  return apiRequest<Submission>(`/submissions/${submissionId}/verification`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// --------------------------------------------------
// Both: download an attachment
// --------------------------------------------------

export async function downloadAttachment(
  submissionId: number,
  attachment: Attachment
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/submissions/${submissionId}/attachments/${attachment.attachment_id}`,
    { headers: authHeaders() }
  );
  if (response.status === 401) {
    handleUnauthorized();
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      body?.error?.message || `Could not download the file (HTTP ${response.status}).`,
      response.status,
      body?.error?.code || "UNKNOWN_ERROR"
    );
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = attachment.file_name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
