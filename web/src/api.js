/**
 * Synoptiq Replay API client.
 * Connects to local FastAPI backend; supports both static production mount and Vite dev proxy.
 */

function getApiBase() {
  if (import.meta.env.VITE_API_BASE !== undefined) {
    return import.meta.env.VITE_API_BASE;
  }
  if (typeof window !== "undefined" && (window.location.port === "5173" || window.location.port === "3000")) {
    return "http://127.0.0.1:8000";
  }
  return "";
}

async function request(path) {
  const base = getApiBase();
  const url = `${base}${path}`;
  const response = await fetch(url);

  if (!response.ok) {
    let errorDetail = null;
    try {
      errorDetail = await response.json();
    } catch {
      // ignore JSON parse failure
    }

    const message =
      (typeof errorDetail?.detail === "string" ? errorDetail.detail : errorDetail?.detail?.message) ||
      `API request failed (${response.status})`;

    const error = new Error(message);
    error.status = response.status;
    error.detail = errorDetail?.detail;
    throw error;
  }

  return response.json();
}

export const getHealth = () => request("/health");

export const getReplay = (init, lead) => request(`/v1/replay?init=${encodeURIComponent(init)}&lead=${lead}`);

export const getRegion = (regionId, init, lead) =>
  request(`/v1/region/${encodeURIComponent(regionId)}?init=${encodeURIComponent(init)}&lead=${lead}`);

export const getEvaluation = () => request("/v1/evaluation");

/**
 * Request the supplied regional records for all fixed leads.
 *
 * Results intentionally preserve an absent/error state per lead rather than
 * filling values from neighbouring days. The inspector can therefore render a
 * curve only from actual API responses and retain Day 10 as unavailable.
 */
export async function getRegionLeadCurve(regionId, init) {
  const leads = Array.from({ length: 10 }, (_, index) => index + 1);
  return Promise.all(
    leads.map(async (lead) => {
      try {
        const data = await getRegion(regionId, init, lead);
        return { lead, data, error: null };
      } catch (error) {
        return { lead, data: null, error };
      }
    })
  );
}

/**
 * Discovers available initialization dates dynamically from the API contract.
 * @returns {Promise<string[]>}
 */
export async function getAvailableInits() {
  try {
    // Attempt an exploratory query that returns the frozen available_inits list in the 404 detail
    const base = getApiBase();
    const res = await fetch(`${base}/v1/replay?init=0000-00-00&lead=1`);
    if (res.status === 404) {
      const data = await res.json();
      if (Array.isArray(data?.detail?.available_inits) && data.detail.available_inits.length > 0) {
        return data.detail.available_inits;
      }
    }
  } catch (err) {
    console.warn("Could not query available inits dynamically, using fallback", err);
  }
  return ["2018-08-01"];
}
