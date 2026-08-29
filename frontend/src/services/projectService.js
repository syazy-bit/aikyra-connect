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
 * Fetch a project's verified community funding summary (public).
 * Funding totals are always server-computed from COMPLETED contributions in
 * integer minor units — the client never calculates the canonical amount.
 * @param {string} id project id
 */
export async function getProjectFunding(id) {
  if (!id) throw new Error("Project ID is required");
  return apiRequest(`/api/projects/${encodeURIComponent(id)}/funding`);
}

/**
 * Advance a project's lifecycle (prototype -> pilot -> implemented).
 * Only the project team's active lead may do this; the server enforces it.
 * @param {string} projectId
 * @param {"prototype" | "pilot" | "implemented"} status
 */
export async function updateProjectLifecycle(projectId, status) {
  if (!projectId) throw new Error("Project ID is required");
  return apiRequest(`/api/projects/${encodeURIComponent(projectId)}/lifecycle`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
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

/**
 * Create an impact metric on an approved project (team lead only).
 * @param {string} projectId
 * @param {{name: string, value: string, unit?: string, description?: string}} payload
 */
export async function createImpactMetric(projectId, payload) {
  return apiRequest(`/api/projects/${encodeURIComponent(projectId)}/impact`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Update an impact metric (team lead only).
 */
export async function updateImpactMetric(projectId, metricId, payload) {
  return apiRequest(
    `/api/projects/${encodeURIComponent(projectId)}/impact/${encodeURIComponent(metricId)}`,
    { method: "PATCH", body: JSON.stringify(payload) }
  );
}

/**
 * Delete an impact metric (team lead only).
 */
export async function deleteImpactMetric(projectId, metricId) {
  return apiRequest(
    `/api/projects/${encodeURIComponent(projectId)}/impact/${encodeURIComponent(metricId)}`,
    { method: "DELETE" }
  );
}

/**
 * Create the outcome report for an implemented project (team lead only).
 * A report is a project-scoped singleton; the server requires the project to
 * be at the 'implemented' stage (409 otherwise).
 * @param {string} projectId
 * @param {{summary: string, results?: string, lessons_learned?: string, next_steps?: string}} payload
 */
export async function createOutcomeReport(projectId, payload) {
  return apiRequest(`/api/projects/${encodeURIComponent(projectId)}/report`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Update a project's outcome report (team lead only).
 */
export async function updateOutcomeReport(projectId, payload) {
  return apiRequest(`/api/projects/${encodeURIComponent(projectId)}/report`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a project's outcome report (team lead only).
 */
export async function deleteOutcomeReport(projectId) {
  return apiRequest(`/api/projects/${encodeURIComponent(projectId)}/report`, {
    method: "DELETE",
  });
}
