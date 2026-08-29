/**
 * Dashboard Service — communication with the public AIKYRA impact dashboard
 * surface (aggregate ecosystem, pipeline, support and impact figures).
 */

import { apiRequest } from "./api.js";

/**
 * Fetch the aggregate ecosystem dashboard (public, no authentication).
 * Every figure is a live database count — the dashboard never hardcodes.
 */
export async function getDashboard() {
  return apiRequest("/api/dashboard");
}