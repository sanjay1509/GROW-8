
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  detail?: string;
  message?: string;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    status: number,
    code = "UNKNOWN_ERROR",
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new ApiError(
      "Please sign in to continue.",
      401,
      "AUTH_REQUIRED"
    );
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

export function handleUnauthorized(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_name");

  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);

  // Application endpoints require authentication.
  if (!headers.has("Authorization")) {
    Object.entries(authHeaders()).forEach(([key, value]) => {
      headers.set(key, value);
    });
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const responseText = await response.text();

  let data: unknown = null;

  if (responseText) {
    try {
      data = JSON.parse(responseText);
    } catch {
      data = null;
    }
  }

  if (response.status === 401) {
    handleUnauthorized();
  }

  if (!response.ok) {
    const errorBody = data as ApiErrorBody | null;

    throw new ApiError(
      errorBody?.error?.message ||
        errorBody?.detail ||
        errorBody?.message ||
        `Request failed (HTTP ${response.status}).`,
      response.status,
      errorBody?.error?.code ||
        (response.status === 401
          ? "INVALID_TOKEN"
          : "UNKNOWN_ERROR"),
      errorBody?.error?.details
    );
  }

  return data as T;
}
