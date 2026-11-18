// Signed-in user's account: GET /auth/me and POST /auth/change-password.

import { API_BASE_URL, ApiError, apiRequest, authHeaders, handleUnauthorized } from "./api";
import type { ApiErrorBody } from "./api";

export interface Me {
  user_id: number;
  email: string;
  full_name: string;
  role: "contributor" | "creator" | "admin";
}

export function getMe(): Promise<Me> {
  return apiRequest<Me>("/auth/me");
}

const PASSWORD_MESSAGES: Record<string, string> = {
  INVALID_CURRENT_PASSWORD: "Your current password is incorrect.",
  PASSWORD_UNCHANGED: "Your new password must be different from the current one.",
  VALIDATION_ERROR: "The new password must be 8 to 72 characters.",
};

export function passwordErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return PASSWORD_MESSAGES[error.code] || error.message;
  }
  if (error instanceof TypeError) {
    return "Can't reach the server. Check that the backend is running.";
  }
  return "Your password could not be changed.";
}

/**
 * Change the password. Not sent through apiRequest on purpose: a wrong current password
 * is a 401 (INVALID_CURRENT_PASSWORD), and apiRequest signs the user out on every 401.
 * Here only an expired or invalid token does that.
 */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });

  if (response.ok) {
    return;
  }

  const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
  const code = body?.error?.code || (response.status === 422 ? "VALIDATION_ERROR" : "UNKNOWN_ERROR");
  if (response.status === 401 && code !== "INVALID_CURRENT_PASSWORD") {
    handleUnauthorized();
  }
  throw new ApiError(
    body?.error?.message || `Request failed (HTTP ${response.status}).`,
    response.status,
    code,
    body?.error?.details
  );
}

/** bcrypt only uses the first 72 bytes, so the API refuses longer passwords. */
export function passwordByteLength(value: string): number {
  return new TextEncoder().encode(value).length;
}
