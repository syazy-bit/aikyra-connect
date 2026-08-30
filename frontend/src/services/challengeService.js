/**
 * Challenge Service — handles all communication with the FastAPI Challenge Engine.
 */

import { apiRequest, apiUrl } from "./api.js";

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" ) return;
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
 * Discovery search over community challenges.
 * Backend returns an envelope: { items, total, skip, limit }.
 * @param {Object} [params]
 * @param {string}  [params.q]          Free-text search
 * @param {string[]} [params.domains]   Taxonomy domain slugs (multi-select)
 * @param {string[]} [params.urgencies] Urgency levels (multi-select)
 * @param {string}  [params.location]   Location substring filter
 * @param {"newest"|"oldest"|"urgency"|"relevance"} [params.sort]
 * @param {number}  [params.skip]
 * @param {number}  [params.limit]
 * @returns {Promise<{items: Array, total: number, skip: number, limit: number}>}
 */
export async function listChallenges(params = {}) {
  const { q, domains, urgencies, location, hasDna, sort, skip = 0, limit = 20 } = params;
  return apiRequest(
    `/api/challenges${buildQuery({ q, domains, urgencies, location, has_dna: hasDna, sort, skip, limit })}`
  );
}

/**
 * Fetch a single challenge by UUID (includes its Problem DNA summary,
 * or dna: null when analysis has not run).
 */
export async function getChallenge(id) {
  if (!id) throw new Error("Challenge ID is required");
  return apiRequest(`/api/challenges/${encodeURIComponent(id)}`);
}

/**
 * Fetch the full Problem DNA for a challenge (signals, provenance, keywords…).
 */
export async function getDna(id) {
  if (!id) throw new Error("Challenge ID is required");
  return apiRequest(`/api/challenges/${encodeURIComponent(id)}/dna`);
}

/**
 * Fetch deterministic related challenges derived from reliable Problem DNA.
 * @returns {Promise<{items: Array}>} Empty when no reliable relationships exist.
 */
export async function getRelatedChallenges(id, limit = 4) {
  return apiRequest(`/api/challenges/${encodeURIComponent(id)}/related?limit=${limit}`);
}

/**
 * Deterministic institution recommendations for a challenge's Problem DNA
 * (Phase 4B rule-based baseline — explainable, never persisted).
 * Rejects with ApiError(409) when the DNA is not reliable enough to match on.
 */
export async function getChallengeMatches(id, limit = 6) {
  return apiRequest(
    `/api/challenges/${encodeURIComponent(id)}/matches?limit=${limit}`
  );
}

/**
 * Fetch the controlled taxonomy (domains, subdomains, urgency levels).
 * The taxonomy API is the single source of truth for discovery filters.
 */
export async function getTaxonomy() {
  return apiRequest("/api/taxonomy");
}

/**
 * Submit a new community challenge.
 */
export async function createChallenge(payload) {
  return apiRequest("/api/challenges", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Upload the optional public photo evidence for a challenge (public — no
 * sign-in needed, matching the public challenge it attaches to). Only the
 * image bytes are sent; the stored filename is generated server-side.
 * @param {string} id
 * @param {File} file
 */
export async function uploadChallengeImage(id, file) {
  const form = new FormData();
  form.append("file", file);
  return apiRequest(`/api/challenges/${encodeURIComponent(id)}/image`, {
    method: "POST",
    body: form,
  });
}

/**
 * Absolute/relative URL for a challenge's public photo evidence.
 * Servers the bytes without auth — challenges and their photos are public.
 * Returns null when the challenge reports has_image: false.
 * @param {{ id: string, has_image?: boolean }} challenge
 */
export function getChallengeImageUrl(challenge) {
  if (!challenge || !challenge.id || !challenge.has_image) return null;
  return apiUrl(`/api/challenges/${encodeURIComponent(challenge.id)}/image`);
}

/**
 * No-key Google Maps URL for a challenge's public coordinates (lat/lng).
 * Coordinates only exist on the detail response; when either is missing or
 * out of range, returns null so callers render no broken map link.
 * @param {{ latitude?: number|null, longitude?: number|null }} challenge
 */
export function getChallengeMapUrl(challenge) {
  const lat = challenge?.latitude;
  const lng = challenge?.longitude;
  if (
    typeof lat !== "number" || typeof lng !== "number" ||
    !Number.isFinite(lat) || !Number.isFinite(lng) ||
    lat < -90 || lat > 90 || lng < -180 || lng > 180
  ) {
    return null;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lat + "," + lng)}`;
}
