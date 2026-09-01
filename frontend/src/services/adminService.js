import { apiRequest } from "./api.js";

export async function getAdminOverview() {
  return apiRequest("/api/admin/overview");
}

export async function listAdminChallenges(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set("status", params.status);
  if (params.dna_validation_status) searchParams.set("dna_validation_status", params.dna_validation_status);
  if (params.skip) searchParams.set("skip", String(params.skip));
  if (params.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  return apiRequest(`/api/admin/challenges${query ? `?${query}` : ""}`);
}

export async function getAdminChallenge(challengeId) {
  return apiRequest(`/api/admin/challenges/${challengeId}`);
}

export async function transitionChallengeStatus(challengeId, request) {
  return apiRequest(`/api/admin/challenges/${challengeId}/status`, {
    method: "PATCH",
    body: JSON.stringify(request),
  });
}

export async function validateChallengeDna(challengeId, request) {
  return apiRequest(`/api/admin/challenges/${challengeId}/dna/validate`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getChallengeAudit(challengeId) {
  return apiRequest(`/api/admin/challenges/${challengeId}/audit`);
}

export async function listAdminInstitutions(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.verification_status) searchParams.set("verification_status", params.verification_status);
  if (params.institution_type) searchParams.set("institution_type", params.institution_type);
  if (params.skip) searchParams.set("skip", String(params.skip));
  if (params.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  return apiRequest(`/api/admin/institutions${query ? `?${query}` : ""}`);
}

export async function getAdminInstitution(institutionId) {
  return apiRequest(`/api/admin/institutions/${institutionId}`);
}

export async function updateInstitutionVerification(institutionId, action, note = null) {
  const payload = { action };
  if (note && note.trim()) {
    payload.note = note.trim();
  }
  return apiRequest(`/api/institutions/${institutionId}/verification`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}