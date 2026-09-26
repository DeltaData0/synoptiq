/**
 * Right Region Inspector component for Synoptiq.
 * Renders regional forecast verification, threshold q90,
 * grouped diagnostic evidence, reserved lead trajectory, and caveats.
 */

import { formatMm, formatProbability, escapeHtml } from "./format.js";
import { PALETTE } from "./legend.js";

const REASON_GROUPS = [
  { key: "ensemble_disagreement", label: "Ensemble Disagreement", icon: "📊" },
  { key: "moisture", label: "Atmospheric Moisture", icon: "💧" },
  { key: "circulation", label: "Circulation & Dynamics", icon: "🌀" },
  { key: "analog_error_memory", label: "Analog-Error Memory", icon: "🧠" },
  { key: "lead_season", label: "Lead Horizon & Season", icon: "📅" },
];

/**
 * Renders the detailed Region Inspector view.
 * @param {HTMLElement} panel
 * @param {object} options
 */
export function renderRegion(panel, { regionData, fallbackProperties, lead, onSelectLead }) {
  // Merge full regionData (from /v1/region) with fallbackProperties (from /v1/replay feature)
  const isFallback = !regionData;
  const regionId = regionData?.region_id || fallbackProperties?.region_id || "Unknown";
  const pBust = regionData?.p_bust ?? fallbackProperties?.p_bust;
  // Use API tier field only; never derive tier from p_bust
  const tier = regionData?.tier || fallbackProperties?.tier || "no_data";
  const tierMeta = PALETTE[tier] || PALETTE.no_data;
  const thresholdMm = regionData?.threshold_mm ?? fallbackProperties?.threshold_mm;
  const forecastMm = regionData?.forecast_mm;
  const observedMm = regionData?.observed_mm;
  const windowQuality = regionData?.window_quality || fallbackProperties?.window_quality || "unavailable";
  const noDataReason = fallbackProperties?.no_data_reason;
  const confidence = regionData?.confidence_complement;
  const reasons = regionData?.reasons || [];
  const caveats = regionData?.caveats || [];
  const provenance = regionData?.provenance || fallbackProperties?.provenance || "fixture-contract-v1";
  const dataMode = regionData?.data_mode || fallbackProperties?.data_mode || "fixture";

  const isFixtureEvidence =
    dataMode === "fixture" || reasons.some((r) => r.evidence_layer === "fixture");

  // Build Reasons Grouped HTML
  const groupedReasonsHtml = REASON_GROUPS.map((grp) => {
    const matching = reasons.filter((r) => r.group === grp.key);
    if (matching.length === 0) {
      return `
        <div class="reason-group group-empty">
          <div class="group-header">
            <span class="group-icon">${grp.icon}</span>
            <span class="group-name">${escapeHtml(grp.label)}</span>
            <span class="group-count">0 signals</span>
          </div>
          <p class="group-empty-note">Not provided for this replay.</p>
        </div>
      `;
    }

    return `
      <div class="reason-group group-active">
        <div class="group-header">
          <span class="group-icon">${grp.icon}</span>
          <span class="group-name">${escapeHtml(grp.label)}</span>
          <span class="group-count">${matching.length} signal${matching.length > 1 ? "s" : ""}</span>
        </div>
        <div class="reason-items">
          ${matching
            .map((r) => {
              const isIncrease = r.direction?.toLowerCase().includes("increase");
              const dirClass = isIncrease ? "dir-increase" : "dir-decrease";
              const dirIcon = isIncrease ? "▲" : "▼";
              const isFixtureLayer = r.evidence_layer === "fixture";

              return `
                <div class="reason-card">
                  <div class="reason-title-row">
                    <span class="reason-feature font-mono">${escapeHtml(r.feature)}</span>
                    <span class="reason-dir ${dirClass}">
                      ${dirIcon} ${escapeHtml(r.direction)}
                    </span>
                  </div>
                  <div class="reason-val-row font-mono">
                    <span class="val-label">Value:</span>
                    <span class="val-num">${r.value !== null && r.value !== undefined ? escapeHtml(r.value) : "—"}</span>
                    <span class="reason-layer-badge">
                      ${isFixtureLayer ? "fixture (illustrative only — no model claim)" : escapeHtml(r.evidence_layer)}
                    </span>
                  </div>
                  <div class="reason-caption">${escapeHtml(r.caption)}</div>
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
    `;
  }).join("");

  panel.innerHTML = `
    <div class="inspector-content" role="region" aria-label="Region Detail View">
      <!-- Header -->
      <div class="inspector-header">
        <div class="inspector-badge-row">
          <span class="inspector-region-id font-mono">${escapeHtml(regionId)}</span>
          <span class="inspector-lead-tag font-mono">Lead Day ${escapeHtml(lead)}</span>
          <span class="tier-pill tier-${tier}">${escapeHtml(tierMeta.label)}</span>
        </div>
        <div class="probability-headline">
          <div class="prob-num font-mono ${pBust === null ? "prob-null" : ""}">${formatProbability(pBust)}</div>
          <div class="prob-meta">
            <span class="prob-label">Forecast Bust Probability</span>
            <span class="prob-sub font-mono">P(|F &minus; O| &gt; threshold)</span>
          </div>
        </div>
      </div>

      <!-- No-data warning banner if reason exists -->
      ${
        noDataReason
          ? `
        <div class="inspector-alert alert-nodata" role="alert">
          <div class="alert-icon">⚠️</div>
          <div class="alert-body">
            <strong>Data Unavailable:</strong> ${escapeHtml(noDataReason)}
          </div>
        </div>
      `
          : ""
      }

      ${
        isFallback && !noDataReason
          ? `
        <div class="inspector-alert alert-info">
          <div class="alert-icon">ℹ️</div>
          <div class="alert-body">
            Full diagnostic payload is unavailable for this cell in the fixture asset. Showing verified map feature telemetry.
          </div>
        </div>
      `
          : ""
      }

      <!-- Telemetry Grid -->
      <div class="inspector-section">
        <div class="section-title">VERIFICATION &amp; TELEMETRY</div>
        <div class="telemetry-grid">
          <div class="telemetry-cell">
            <span class="t-lbl">Forecast Rain (F)</span>
            <span class="t-val font-mono">${formatMm(forecastMm)}</span>
          </div>
          <div class="telemetry-cell">
            <span class="t-lbl">Observed Rain (O)</span>
            <span class="t-val font-mono">${formatMm(observedMm)}</span>
          </div>
          <div class="telemetry-cell">
            <span class="t-lbl">Bust Threshold (q90)</span>
            <span class="t-val font-mono">${thresholdMm !== null && thresholdMm !== undefined ? `${thresholdMm} mm/day` : "Not available"}</span>
          </div>
          <div class="telemetry-cell">
            <span class="t-lbl">Window Semantics</span>
            <span class="t-val font-mono ${windowQuality === "unavailable" ? "val-warning" : windowQuality === "approximate" ? "val-approx" : ""}">${escapeHtml(
              windowQuality === "exact"
                ? "Exact"
                : windowQuality === "approximate"
                ? "Approximate"
                : windowQuality === "unavailable"
                ? "Unavailable"
                : "Awaiting replay data"
            )}</span>
          </div>

          ${
            confidence !== null && confidence !== undefined
              ? `
            <div class="telemetry-cell">
              <span class="t-lbl">Confidence Margin</span>
              <span class="t-val font-mono">${formatProbability(confidence)}</span>
            </div>
          `
              : ""
          }
        </div>
      </div>

      <!-- Reserved Lead Trajectory Graph Panel -->
      <div class="inspector-section">
        <div class="section-title">LEAD TRAJECTORY (DAY 1 – 10)</div>
        <div class="trajectory-card">
          <div class="trajectory-chart-mock" aria-hidden="true">
            <svg viewBox="0 0 320 70" class="trajectory-svg">
              <line x1="20" y1="55" x2="300" y2="55" stroke="rgba(148,163,184,0.3)" stroke-width="1" stroke-dasharray="3,3" />
              <line x1="20" y1="20" x2="300" y2="20" stroke="rgba(148,163,184,0.2)" stroke-width="1" stroke-dasharray="2,2" />
              <!-- Lead dots placeholder -->
              <circle cx="35" cy="35" r="4" fill="#38bdf8" />
              <text x="35" y="65" text-anchor="middle" font-size="8" fill="#94a3b8" font-family="monospace">D1</text>
              <circle cx="65" cy="55" r="2.5" fill="#475569" />
              <text x="65" y="65" text-anchor="middle" font-size="8" fill="#64748b" font-family="monospace">D2</text>
              <circle cx="95" cy="55" r="2.5" fill="#475569" />
              <circle cx="125" cy="55" r="2.5" fill="#475569" />
              <circle cx="155" cy="55" r="2.5" fill="#475569" />
              <circle cx="185" cy="55" r="2.5" fill="#475569" />
              <circle cx="215" cy="55" r="2.5" fill="#475569" />
              <circle cx="245" cy="55" r="2.5" fill="#475569" />
              <circle cx="275" cy="55" r="2.5" fill="#475569" />
              <circle cx="295" cy="55" r="3" fill="#64748b" stroke="#94a3b8" />
              <text x="295" y="65" text-anchor="middle" font-size="8" fill="#64748b" font-family="monospace">D10</text>
            </svg>
          </div>
          <div class="trajectory-notice">
            <span class="trajectory-notice-title">Multi-lead trajectory reserved</span>
            <span class="trajectory-notice-desc">
              Continuous lead trajectory requires a future replay artifact containing multi-lead values. Synthesized trajectory data is strictly prohibited.
            </span>
          </div>
        </div>
      </div>

      <!-- Diagnostic Evidence / Reason Groups -->
      <div class="inspector-section">
        <div class="section-header-row">
          <span class="section-title">DIAGNOSTIC EVIDENCE</span>
          <span class="evidence-tag">Diagnostic evidence</span>
        </div>
        <div class="shap-disclaimer">
          ${
            isFixtureEvidence
              ? "⚠️ Illustrative fixture example only: this reason payload is an integration test fixture and makes no model or meteorological claim."
              : "Score evidence: feature attribution reflects model-score sensitivity, not a proven meteorological causal mechanism."
          }
        </div>
        <div class="reasons-accordion">
          ${groupedReasonsHtml}
        </div>
      </div>

      <!-- Caveats and Provenance -->
      <div class="inspector-section inspector-caveats-section">
        <div class="section-title">CONTRACT &amp; CAVEATS</div>
        <ul class="caveats-list">
          ${caveats.map((c) => `<li>${escapeHtml(c)}</li>`).join("")}
          <li>Data mode: <code class="font-mono">${escapeHtml(dataMode)}</code></li>
          <li>Provenance: <code class="font-mono">${escapeHtml(provenance)}</code></li>
        </ul>
      </div>
    </div>
  `;
}
