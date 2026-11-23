// Turns API errors into messages for forms.
// A 422 VALIDATION_ERROR carries details as [{loc: ["body", "field"], message}], so each
// message can be shown next to its field.

import { ApiError } from "./api";

export type FieldErrors = Record<string, string>;

interface ValidationDetail {
  loc?: (string | number)[];
  message?: string;
  msg?: string;
}

/** Field name → message, from a VALIDATION_ERROR. Empty for any other error. */
export function fieldErrorsFrom(error: unknown): FieldErrors {
  if (!(error instanceof ApiError) || error.code !== "VALIDATION_ERROR") {
    return {};
  }
  const details = error.details as unknown;
  if (!Array.isArray(details)) {
    return {};
  }

  const result: FieldErrors = {};
  for (const item of details as ValidationDetail[]) {
    const loc = item.loc ?? [];
    const field = String(loc[loc.length - 1] ?? "");
    const message = item.message || item.msg;
    if (field && message && !result[field]) {
      result[field] = cleanMessage(message);
    }
  }
  return result;
}

/** Pydantic wording, made a little friendlier. */
function cleanMessage(message: string): string {
  return message
    .replace(/^Value error, /, "")
    .replace("String should have at least 1 character", "This can't be empty")
    .replace(/String should have at most (\d+) characters/, "Keep this under $1 characters");
}

/**
 * One plain-language message for any error. `messages` maps API error codes to the
 * wording this screen wants; otherwise the API's own message is used.
 */
export function errorMessage(
  error: unknown,
  fallback: string,
  messages: Record<string, string> = {}
): string {
  if (error instanceof ApiError) {
    if (messages[error.code]) {
      return messages[error.code];
    }
    if (error.code === "VALIDATION_ERROR") {
      return "Please check the highlighted fields.";
    }
    return error.message || fallback;
  }
  if (error instanceof TypeError) {
    return "Can't reach the server. Check that the backend is running.";
  }
  return error instanceof Error && error.message ? error.message : fallback;
}

/** The fields whose value changed, for PATCH bodies. Empty strings become null (cleared). */
export function changedFields<T extends Record<string, string>>(
  original: T,
  current: T
): Partial<Record<keyof T, string | null>> {
  const changes: Partial<Record<keyof T, string | null>> = {};
  (Object.keys(current) as (keyof T)[]).forEach((key) => {
    const before = (original[key] ?? "").trim();
    const after = (current[key] ?? "").trim();
    if (before !== after) {
      changes[key] = after === "" ? null : after;
    }
  });
  return changes;
}
