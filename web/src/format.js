/**
 * Formatting and safety utilities for Synoptiq dashboard.
 */

/**
 * Escapes unsafe HTML characters to prevent XSS.
 * @param {any} val
 * @returns {string}
 */
export function escapeHtml(val) {
  if (val === null || val === undefined) return "";
  return String(val)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Formats a probability value [0, 1] into a percentage string.
 * @param {number|null|undefined} prob
 * @returns {string}
 */
export function formatProbability(prob) {
  if (prob === null || prob === undefined || Number.isNaN(Number(prob))) {
    return "Unavailable";
  }
  return `${Math.round(Number(prob) * 100)}%`;
}

/**
 * Formats a precipitation value in millimeters.
 * @param {number|null|undefined} mm
 * @returns {string}
 */
export function formatMm(mm) {
  if (mm === null || mm === undefined || Number.isNaN(Number(mm))) {
    return "Not available";
  }
  return `${Number(mm).toFixed(1)} mm`;
}

/**
 * Formats an ISO UTC timestamp into a compact, readable string: YYYY-MM-DD HH:MM UTC
 * @param {string|null|undefined} isoString
 * @returns {string}
 */
export function formatUtcTime(isoString) {
  if (!isoString) return "Unavailable";
  try {
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return String(isoString);
    const pad = (n) => String(n).padStart(2, "0");
    const year = d.getUTCFullYear();
    const month = pad(d.getUTCMonth() + 1);
    const day = pad(d.getUTCDate());
    const hours = pad(d.getUTCHours());
    const minutes = pad(d.getUTCMinutes());
    return `${year}-${month}-${day} ${hours}:${minutes}Z`;
  } catch {
    return String(isoString);
  }
}

/**
 * Formats a valid interval window: [start, end) UTC
 * @param {string|null|undefined} startUtc
 * @param {string|null|undefined} endUtc
 * @returns {string}
 */
export function formatWindowInterval(startUtc, endUtc) {
  if (!startUtc || !endUtc) return "Accumulation window unaudited";
  return `${formatUtcTime(startUtc)} → ${formatUtcTime(endUtc)}`;
}
