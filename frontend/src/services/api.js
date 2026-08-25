/**
 * Base API client for Aikyra frontend.
 * Communicates with the FastAPI backend.
 * Uses VITE_API_BASE_URL if explicitly defined, otherwise relative paths (Vite proxy / same-origin).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/**
 * Perform an HTTP request and parse the response JSON.
 * Normalizes error messages and details.
 */
export async function apiRequest(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

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
