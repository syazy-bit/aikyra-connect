/**
 * Base API client for Aikyra frontend.
 * Communicates with the FastAPI backend.
 * Uses VITE_API_BASE_URL if explicitly defined, otherwise relative paths (Vite proxy / same-origin).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const TOKEN_KEY = "aikyra_token";

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

let onUnauthenticated = null;

export function setUnauthenticatedHandler(handler) {
  onUnauthenticated = handler;
}

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

/**
 * Build a full API URL using the configured base URL (VITE_API_BASE_URL,
 * or "" for the Vite same-origin proxy). Consumers that build raw URLs —
 * e.g. <img src> for public endpoints — must use this so they keep working
 * when the API is served from a different origin.
 */
export function apiUrl(endpoint) {
  return `${BASE_URL}${endpoint}`;
}

/**
 * Perform an HTTP request and parse the response JSON.
 * Normalizes error messages and details.
 * Automatically includes Authorization header when token exists.
 */
export async function apiRequest(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const token = getToken();

  const headers = {
    ...options.headers,
  };

  // FormData: let the browser set the multipart boundary; the JSON header
  // would corrupt the body (and confuse the server's multipart parser).
  const isFormData = options.body instanceof FormData;
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    // Network failure / server unreachable
    throw new ApiError(
      "Unable to connect to the Aikyra server. Please check your internet connection or verify the backend is running.",
      0,
      { originalError: err.message }
    );
  }

  // Handle empty responses (like 204 No Content)
  if (response.status === 204) {
    return null;
  }

  let data = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    // Handle 401: clear token and notify app
    if (response.status === 401) {
      clearToken();
      if (onUnauthenticated) {
        onUnauthenticated();
      }
    }

    // Format human-friendly error messages from backend responses
    let errorMessage = "An unexpected error occurred. Please try again.";

    if (data && typeof data === "object") {
      if (typeof data.detail === "string") {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        // FastAPI 422 validation errors: array of { loc, msg, type }
        const fieldErrors = data.detail.map((d) => {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "Field";
          return `${field}: ${d.msg}`;
        });
        errorMessage = fieldErrors.join("; ");
      }
    } else if (response.status === 404) {
      errorMessage = "The requested resource was not found.";
    } else if (response.status === 500) {
      errorMessage = "Server error occurred. The team has been notified.";
    }

    throw new ApiError(errorMessage, response.status, data);
  }

  return data;
}