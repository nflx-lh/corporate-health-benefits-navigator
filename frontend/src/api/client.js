/**
 * API client for the Corporate Health Benefits Navigator backend.
 * Calls POST /v1/query-orchestrated (Phase 3 endpoint).
 */

const BASE = "/v1";

/**
 * Submit a benefits query via the orchestrated endpoint.
 *
 * @param {string} employeeId
 * @param {string} question
 * @returns {Promise<object>} Parsed response body.
 * @throws {Error} With `.status` and `.code` properties on HTTP errors.
 */
export async function queryBenefits(employeeId, question) {
  const res = await fetch(`${BASE}/query-orchestrated`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ employee_id: employeeId, question }),
  });

  const body = await res.json();

  if (!res.ok) {
    const err = new Error(
      body?.error?.message || `Request failed (${res.status})`,
    );
    err.status = res.status;
    err.code = body?.error?.code || "UNKNOWN";
    throw err;
  }

  return body;
}
