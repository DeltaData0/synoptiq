/**
 * Risk tier legend and palette definition for Synoptiq.
 */

export const PALETTE = {
  low: {
    fill: "#0d9488",
    stroke: "#2dd4bf",
    label: "Low Risk",
    range: "< 25% P(bust)",
    description: "Model forecast unlikely to exceed regional 90th percentile error floor.",
  },
  watch: {
    fill: "#d97706",
    stroke: "#fbbf24",
    label: "Watch",
    range: "25% – 50% P(bust)",
    description: "Elevated probability of forecast bust; active monitoring recommended.",
  },
  high: {
    fill: "#dc2626",
    stroke: "#f87171",
    label: "High Risk",
    range: "≥ 50% P(bust)",
    description: "High probability that 24h rainfall error exceeds regional threshold.",
  },
  no_data: {
    fill: "#475569",
    stroke: "#94a3b8",
    label: "No Data / Unaudited",
    range: "Unavailable",
    description: "Accumulation interval not audited or outside land domain. Never implies 0% risk.",
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
      <span class="legend-sub">P(error &gt; q90)</span>
    </div>
    <div class="legend-items">
      ${tiers
        .map(
          (t) => `
        <div class="legend-row tier-${t.key}" title="${t.description}">
          <span class="legend-swatch" style="background-color: ${t.fill}; border-color: ${t.stroke};"></span>
          <div class="legend-meta">
            <span class="legend-label">${t.label}</span>
            <span class="legend-range">${t.range}</span>
          </div>
        </div>
      `,
        )
        .join("")}
    </div>
    <div class="legend-caption">
      Bust threshold: regional &times; seasonal train q90 with 10 mm/day floor.
    </div>
  `;
}
