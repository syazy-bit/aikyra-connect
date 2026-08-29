/**
 * Project Service — communication with the FastAPI Industry/NGO support
 * surface (approved projects, organizations, support offers).
 */

import { apiRequest } from "./api.js";

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    search.set(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

/**
 * List approved projects (public). Projects exist only for accepted
 * proposals, so this is the "approved solutions" board.
 * @param {{status?: string, skip?: number, limit?: number}} [params]
 */
export async function listProjects(params = {}) {
  const { status, skip = 0, limit = 20 } = params;
  return apiRequest(`/api/projects${buildQuery({ status, skip, limit })}`);
}

/**
 * Fetch a single approved project including its support offers (public).
 */
export async function getProject(id) {
  if (!id) throw new Error("Project ID is required");
  return apiRequest(`/api/projects/${encodeURIComponent(id)}`);
}

/**
 * Fetch the authenticated user's managed organization (or null).
 */
export async function getMyOrganization() {
  return apiRequest("/api/organizations/me");
}

/**
 * Register an organization. The authenticated user becomes its manager.
 * @param {{name: string, description?: string, website?: string}} payload
 */
export async function createOrganization(payload) {
  return apiRequest("/api/organizations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Offer support to an approved project. Server derives the offering
 * organization from the caller's managed organization.
 * @param {string} projectId
 * @param {{support_type: string, message?: string}} payload
 */
export async function createOffer(projectId, payload) {
  return apiRequest(`/api/projects/${encodeURIComponent(projectId)}/offers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
