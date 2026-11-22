// Contributor resume (ADR 0008): one optional PDF, at most 10 MB.
// PUT/GET/DELETE /contributors/me/resume and GET /contributors/me/resume/file.

import {
  API_BASE_URL,
  ApiError,
  apiRequest,
  authHeaders,
  handleUnauthorized,
} from "./api";
import type { ApiErrorBody } from "./api";

export interface Resume {
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
}

export const RESUME_MAX_BYTES = 10 * 1024 * 1024;

// What we tell the contributor for each error code (branch on the code, not the message).
const RESUME_MESSAGES: Record<string, string> = {
  RESUME_TOO_LARGE: "That file is larger than 10 MB.",
  UNSUPPORTED_FILE_TYPE: "Only PDF files can be uploaded.",
  EMPTY_FILE: "That file is empty.",
  LENGTH_REQUIRED: "The upload could not be read. Please try again.",
  CONTRIBUTOR_PROFILE_REQUIRED: "Your contributor profile is missing. Please contact support.",
  RESUME_NOT_FOUND: "You haven't uploaded a resume yet.",
  AUTH_REQUIRED: "Please sign in to continue.",
  INVALID_TOKEN: "Your session has expired. Please sign in again.",
  ROLE_FORBIDDEN: "Only contributor accounts have a resume.",
};

export function resumeErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return RESUME_MESSAGES[error.code] || error.message || fallback;
  }
  if (error instanceof TypeError) {
    return "Can't reach the server. Check that the backend is running.";
  }
  return error instanceof Error && error.message ? error.message : fallback;
}

/** The contributor's resume metadata, or null when they haven't uploaded one. */
export async function getMyResume(): Promise<Resume | null> {
  try {
    return await apiRequest<Resume>("/contributors/me/resume");
  } catch (error) {
    if (error instanceof ApiError && error.code === "RESUME_NOT_FOUND") {
      return null;
    }
    throw error;
  }
}

/**
 * Upload (or replace) the resume. Uses XMLHttpRequest because fetch can't report
 * upload progress; onProgress receives 0-100.
 */
export function uploadResume(
  file: File,
  onProgress?: (percent: number) => void
): Promise<Resume> {
  return new Promise((resolve, reject) => {
    let headers: Record<string, string>;
    try {
      headers = authHeaders();
    } catch (error) {
      reject(error);
      return;
    }

    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("PUT", `${API_BASE_URL}/contributors/me/resume`);
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
        resolve(data as Resume);
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

export async function deleteResume(): Promise<void> {
  await apiRequest<null>("/contributors/me/resume", { method: "DELETE" });
}

/** Download the contributor's own resume and hand it to the browser. */
export async function downloadMyResume(fileName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/contributors/me/resume/file`, {
    headers: authHeaders(),
  });

  if (response.status === 401) {
    handleUnauthorized();
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      body?.error?.message || `Could not download resume (HTTP ${response.status}).`,
      response.status,
      body?.error?.code || "UNKNOWN_ERROR"
    );
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
