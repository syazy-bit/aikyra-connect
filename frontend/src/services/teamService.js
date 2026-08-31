/**
 * Team Service — communication with the FastAPI Team Engine (CP1–CP2).
 * Read surfaces only for now (workspace, team detail). Mutation actions
 * (create team, invite, accept/decline, leave, transfer) arrive in later slices.
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
 * List teams visible to the authenticated user.
 * Backend envelope: { items, total, skip, limit }. Visibility is resolved
 * server-side (active institution membership, or membership in the team).
 * @param {Object} [params]
 * @param {string} [params.status] TeamStatus value ("forming"|"active"|...)
 * @param {number} [params.skip]
 * @param {number} [params.limit]
 */
export async function listTeams(params = {}) {
  const { status, skip = 0, limit = 20 } = params;
  return apiRequest(`/api/teams${buildQuery({ status, skip, limit })}`);
}

/**
 * Fetch a single team (active member, or institution_admin/representative of the
 * team's institution).
 */
export async function getTeam(id) {
  if (!id) throw new Error("Team ID is required");
  return apiRequest(`/api/teams/${encodeURIComponent(id)}`);
}

/**
 * Fetch a team's memberships (active team membership required).
 */
export async function getTeamMembers(id) {
  if (!id) throw new Error("Team ID is required");
  return apiRequest(`/api/teams/${encodeURIComponent(id)}/members`);
}

/**
 * Fetch the authenticated user's pending team invitations.
 * No team membership required — this is the discoverable entry point.
 * Returns { items: TeamMembershipResponse[], total }.
 */
export async function getMyInvitations() {
  return apiRequest("/api/teams/invitations/me");
}

/**
 * Create a team for a challenge. The authenticated user becomes the lead;
 * they need an ACTIVE institution membership at the chosen institution.
 * @param {{institution_id: string, challenge_id: string, name: string, description?: string}} payload
 */
export async function createTeam(payload) {
  return apiRequest("/api/teams", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Invite a user to a team. Lead-only. The invitee must already hold an
 * ACTIVE faculty/student membership at the team's institution (resolved
 * server-side). Identity is by user_id — no person search exists yet.
 * Returns a TeamMembershipResponse (status "invited").
 */
export async function inviteMember(teamId, userId) {
  return apiRequest(`/api/teams/${encodeURIComponent(teamId)}/invitations`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

/**
 * Accept a pending team invitation (the invited user only).
 * The membership becomes active server-side; joined_at is set by the server.
 */
export async function acceptInvitation(teamId, membershipId) {
  return apiRequest(
    `/api/teams/${encodeURIComponent(teamId)}/invitations/${encodeURIComponent(membershipId)}/accept`,
    { method: "POST" }
  );
}

/**
 * Decline a pending team invitation (the invited user only).
 * Removes the invitation row server-side.
 */
export async function declineInvitation(teamId, membershipId) {
  return apiRequest(
    `/api/teams/${encodeURIComponent(teamId)}/invitations/${encodeURIComponent(membershipId)}/decline`,
    { method: "POST" }
  );
}