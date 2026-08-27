/**
 * Institution Service — communication with the FastAPI Institution Engine.
 * Capability data is human-entered (Phase 4A); no AI-derived fields exist.
 */

import { apiRequest } from "./api.js";

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    if (Array.isArray(value)) {
      if (value.length) search.set(key, value.join(","));
    } else {
      search.set(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

/**
 * List institutions.
 * Backend returns an envelope: { items, total, skip, limit }.
 * @param {Object} [params]
 * @param {string}  [params.q]        Free-text search
 * @param {string[]} [params.types]   institution_type values (multi-select)
 * @param {string[]} [params.domains] Taxonomy domain slugs (multi-select)
 * @param {"newest"|"oldest"|"relevance"} [params.sort]
 * @param {number}  [params.skip]
 * @param {number}  [params.limit]
 */
export async function listInstitutions(params = {}) {
  const { q, types, domains, sort, skip = 0, limit = 20 } = params;
  return apiRequest(
    `/api/institutions${buildQuery({ q, types, domains, sort, skip, limit })}`
  );
}

/**
 * Fetch a single institution profile (includes capability data).
 */
export async function getInstitution(id) {
  if (!id) throw new Error("Institution ID is required");
  return apiRequest(`/api/institutions/${encodeURIComponent(id)}`);
}

/**
 * Register a new institution. Starts active + unverified; verification is
 * performed by reviewers in a later phase.
 */
export async function registerInstitution(payload) {
  return apiRequest("/api/institutions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Update an institution profile / capabilities (partial, replace-whole for
 * the capabilities object).
 */
export async function updateInstitution(id, payload) {
  return apiRequest(`/api/institutions/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch the authenticated user's membership status for an institution.
 * Returns { is_member, role, membership_status } or { is_member: false }.
 */
export async function getInstitutionMembership(id) {
  if (!id) throw new Error("Institution ID is required");
  return apiRequest(`/api/institutions/${encodeURIComponent(id)}/membership`);
}
