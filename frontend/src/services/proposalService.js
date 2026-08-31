/**
 * Proposal Service — communication with the FastAPI Proposal Engine (CP3).
 * Read surfaces only for now (workspace summaries, proposal detail).
 * Create / edit / submit / withdraw arrive in later slices.
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
 * List proposals visible to the authenticated user (active team member,
 * or institution_admin/representative of the team's institution).
 * @param {Object} [params]
 * @param {string} [params.teamId]  Narrow to a single team
 * @param {string} [params.status]  ProposalStatus value ("draft"|"submitted"|...)
 * @param {number} [params.skip]
 * @param {number} [params.limit]
 */
export async function listProposals(params = {}) {
  const { teamId, status, skip = 0, limit = 20 } = params;
  return apiRequest(
    `/api/proposals${buildQuery({ team_id: teamId, status, skip, limit })}`
  );
}

/**
 * Fetch a single proposal's full detail (summary, approach, resources,
 * timeline, review fields).
 */
export async function getProposal(id) {
  if (!id) throw new Error("Proposal ID is required");
  return apiRequest(`/api/proposals/${encodeURIComponent(id)}`);
}

/**
 * Create a draft proposal for a team and challenge. Any ACTIVE team member
 * may create; the challenge must match the team's challenge (409 otherwise).
 * Proposals always start as a draft.
 * @param {{team_id: string, challenge_id: string, title: string, summary: string,
 *          approach?: string, resources_needed?: string, timeline?: string}} payload
 */
export async function createProposal(payload) {
  return apiRequest("/api/proposals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Edit a draft proposal (any ACTIVE team member). Only drafts are editable.
 * @param {string} id
 * @param {{title?: string, summary?: string, approach?: string|null,
 *          resources_needed?: string|null, timeline?: string|null}} fields
 *        Partial patch; title/summary must be non-blank when supplied.
 */
export async function updateProposal(id, fields) {
  return apiRequest(`/api/proposals/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

/**
 * Submit a draft proposal (draft -> submitted). Team lead only;
 * submitted_at is set server-side.
 */
export async function submitProposal(id) {
  return apiRequest(`/api/proposals/${encodeURIComponent(id)}/submit`, {
    method: "POST",
  });
}

/**
 * Withdraw a draft or submitted proposal (-> withdrawn). Team lead only.
 * Withdrawal is terminal in CP3.
 */
export async function withdrawProposal(id) {
  return apiRequest(`/api/proposals/${encodeURIComponent(id)}/withdraw`, {
    method: "POST",
  });
}

/**
 * Advance the proposal review workflow (CP4). Institution admin or
 * representative of the proposal's team institution only.
 * @param {string} id
 * @param {{action: "start_review"|"accept"|"reject", review_note?: string}} payload
 *        - start_review: submitted -> under_review
 *        - accept:       under_review -> accepted
 *        - reject:       under_review -> rejected (review_note is captured)
 */
export async function reviewProposal(id, payload) {
  return apiRequest(`/api/proposals/${encodeURIComponent(id)}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}