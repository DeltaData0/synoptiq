/**
 * Risk tier legend and palette definition for Synoptiq.
 * Renders server-reported risk tiers without deriving cutoffs on the client.
 */

export const PALETTE = {
  low: {
    fill: "#0d9488",
    stroke: "#2dd4bf",
    label: "Low",
    description: "Server-reported low risk tier.",
  },
  watch: {
    fill: "#d97706",
    stroke: "#fbbf24",
    label: "Watch",
    description: "Server-reported watch risk tier.",
  },
  high: {
    fill: "#dc2626",
    stroke: "#f87171",
    label: "High",
    description: "Server-reported high risk tier.",
  },
  no_data: {
    fill: "#475569",
    stroke: "#94a3b8",
    label: "No data",
    description: "Server-reported unavailable or no-data tier. Never implies 0% risk.",
  },
};

/**
 * Returns the fill color for a given tier.
 * @param {string} tier
 * @returns {string}
 */
export function getTierColor(tier) {
  return PALETTE[tier]?.fill ?? PALETTE.no_data.fill;
}

/**
 * Returns the border stroke color for a given tier.
 * @param {string} tier
 * @returns {string}
 */
export function getTierStroke(tier) {
  return PALETTE[tier]?.stroke ?? PALETTE.no_data.stroke;
}

/**
 * Renders the interactive legend into the container.
 * @param {HTMLElement} container
 */
export function renderLegend(container) {
  const tiers = [
    { key: "high", ...PALETTE.high },
    { key: "watch", ...PALETTE.watch },
    { key: "low", ...PALETTE.low },
    { key: "no_data", ...PALETTE.no_data },
  ];

  container.innerHTML = `
    <div class="legend-header">
      <span class="legend-title">RISK TIERS</span>
    </div>
    <div class="legend-items">
      ${tiers
        .map(
          (t) => `
        <div class="legend-row tier-${t.key}" title="${t.description}">
          <span class="legend-swatch" style="background-color: ${t.fill}; border-color: ${t.stroke};"></span>
          <div class="legend-meta">
            <span class="legend-label">${t.label}</span>
          </div>
        </div>
      `,
        )
        .join("")}
    </div>
    <div class="legend-caption">
      Server-reported risk tiers for historical replay.
    </div>
  `;
}
