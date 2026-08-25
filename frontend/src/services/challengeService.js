/**
 * Challenge Service — handles all communication with the FastAPI Challenge Engine.
 */

import { apiRequest } from "./api.js";

/**
 * Fetch a paginated list of community challenges.
 * @param {Object} params
 * @param {number} [params.skip=0]
 * @param {number} [params.limit=20]
 * @returns {Promise<Array>} List of challenges ordered by created_at DESC
 */
export async function getChallenges({ skip = 0, limit = 20 } = {}) {
  const query = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
  }).toString();

  return apiRequest(`/api/challenges?${query}`);
}

/**
 * Fetch a single challenge by its unique UUID.
 * @param {string} id - Challenge UUID
 * @returns {Promise<Object>} Challenge details
 */
export async function getChallenge(id) {
  if (!id) {
    throw new Error("Challenge ID is required");
  }
  return apiRequest(`/api/challenges/${encodeURIComponent(id)}`);
}

/**
 * Submit a new community challenge.
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} payload.description
 * @param {string} payload.location
 * @returns {Promise<Object>} Created challenge with status 'submitted'
 */
export async function createChallenge(payload) {
  return apiRequest("/api/challenges", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
