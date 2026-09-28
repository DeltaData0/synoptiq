/**
 * Right Region Inspector component for Synoptiq.
 * Renders regional forecast verification, threshold q90,
 * grouped diagnostic evidence, reserved lead trajectory, and caveats.
 */

import { formatMm, formatProbability, formatWindowInterval, escapeHtml } from "./format.js";
import { PALETTE } from "./legend.js";

const REASON_GROUPS = [
  { key: "forecast_control", label: "Control Forecast Rain", icon: "🌧️" },
  { key: "regional_context", label: "Regional Context", icon: "🗺️" },
  { key: "ensemble_disagreement", label: "Ensemble Disagreement", icon: "📊" },
  { key: "moisture", label: "Atmospheric Moisture", icon: "💧" },
  { key: "circulation", label: "Circulation & Dynamics", icon: "🌀" },
  { key: "analog_error_memory", label: "Analog-Error Memory", icon: "🧠" },
  { key: "lead_season", label: "Lead Horizon & Season", icon: "📅" },
];

function formatCoverage(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Not supplied";
  return `${Math.round(Number(value) * 100)}%`;
}

function formatProvenance(value) {
  if (typeof value === "string" && value.trim()) return value;
  if (value && typeof value === "object") {
    return Object.entries(value)
      .filter(([, item]) => item !== null && item !== undefined && String(item).trim())
      .map(([key, item]) => `${key}=${item}`)
      .join("; ");
  }
  return "Not supplied";
}

function renderLeadTrajectory(leadCurve, activeLead) {
  if (!Array.isArray(leadCurve) || leadCurve.length === 0) {
    return `
      <div class="trajectory-notice">
        <span class="trajectory-notice-title">Lead records not supplied</span>
        <span class="trajectory-notice-desc">This selection has no separately supplied per-lead regional records. Synoptiq does not infer a curve.</span>
      </div>
    `;
  }

  const supplied = leadCurve.filter((point) => point.status === "available" && point.p_bust !== null);
  if (supplied.length === 0) {
    return `
      <div class="trajectory-notice">
        <span class="trajectory-notice-title">No score curve available</span>
        <span class="trajectory-notice-desc">The API returned no scored exact Day 1–9 records for this region and initialization.</span>
      </div>
    `;
  }

  return `
    <div class="trajectory-scale" aria-hidden="true"><span>100%</span><span>0%</span></div>
    <div class="trajectory-chart" role="group" aria-label="Supplied forecast bust probabilities by lead day">
      ${leadCurve
        .map((point) => {
          const isAvailable = point.status === "available" && point.p_bust !== null;
          const isSelected = Number(point.lead) === Number(activeLead);
          const statusLabel = isAvailable
            ? `${formatProbability(point.p_bust)} bust probability; threshold ${formatMm(point.threshold_mm)}`
            : point.status === "unavailable"
            ? "Unavailable"
            : point.status === "error"
            ? "Request failed"
            : "Not supplied";
          const barHeight = isAvailable ? Math.max(5, Math.round(point.p_bust * 100)) : 3;
          return `
            <button
              type="button"
              class="trajectory-point ${isAvailable ? "trajectory-point-available" : "trajectory-point-unavailable"} ${isSelected ? "trajectory-point-selected" : ""}"
              data-curve-lead="${escapeHtml(point.lead)}"
              ${isAvailable ? "" : "disabled"}
              aria-pressed="${isSelected ? "true" : "false"}"
              title="Lead Day ${escapeHtml(point.lead)}: ${escapeHtml(statusLabel)}"
            >
              <span class="trajectory-bar-wrap"><span class="trajectory-bar" style="height:${barHeight}%"></span></span>
              <span class="trajectory-prob font-mono">${isAvailable ? escapeHtml(formatProbability(point.p_bust)) : "—"}</span>
              <span class="trajectory-day font-mono">D${escapeHtml(point.lead)}</span>
            </button>
          `;
        })
        .join("")}
    </div>
    <p class="trajectory-caption">Bars are direct regional API responses. Missing, failed, and unavailable leads are never estimated by the dashboard.</p>
  `;
}

/**
 * Renders the detailed Region Inspector view.
 * @param {HTMLElement} panel
 * @param {object} options
 */
export function renderRegion(panel, { regionData, fallbackProperties, lead, leadCurve, detailError, onSelectLead }) {
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
  const noDataReason = regionData?.no_data_reason || fallbackProperties?.no_data_reason;
  const confidence = regionData?.confidence_complement;
  const reasons = regionData?.reasons || [];
  const caveats = regionData?.caveats || [];
  const provenance = formatProvenance(regionData?.provenance || fallbackProperties?.provenance);
  const dataMode = regionData?.data_mode || fallbackProperties?.data_mode || "fixture";
  const validStartUtc = regionData?.valid_start_utc || fallbackProperties?.valid_start_utc;
  const validEndUtc = regionData?.valid_end_utc || fallbackProperties?.valid_end_utc;
  const sourceKey = regionData?.source_key || fallbackProperties?.source_key || null;
  const gribSteps = regionData?.grib_steps || fallbackProperties?.grib_steps || null;
  const coverageFraction = regionData?.coverage_fraction ?? fallbackProperties?.coverage_fraction;
  const analogs = Array.isArray(regionData?.analogs) ? regionData.analogs : [];

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
            ${
              detailError && detailError.status !== 404
                ? `Regional diagnostics could not be loaded: ${escapeHtml(detailError.message)}. Showing only map fields supplied for this selection.`
                : "Full regional diagnostics are not supplied for this replay selection. Showing the replay fields that are available."
            }
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

          <div class="telemetry-cell telemetry-cell-wide">
            <span class="t-lbl">Verified UTC Interval</span>
            <span class="t-val font-mono">${escapeHtml(formatWindowInterval(validStartUtc, validEndUtc))}</span>
          </div>

          <div class="telemetry-cell">
            <span class="t-lbl">Regional Coverage</span>
            <span class="t-val font-mono">${escapeHtml(formatCoverage(coverageFraction))}</span>
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

      <div class="inspector-section">
        <div class="section-title">LEAD TRAJECTORY</div>
        <div class="trajectory-card">
          ${renderLeadTrajectory(leadCurve, lead)}
        </div>
      </div>

      <div class="inspector-section">
        <div class="section-header-row">
          <span class="section-title">COMPARABLE EARLIER CASES</span>
          <span class="evidence-tag">Earlier-only</span>
        </div>
        <div class="analog-list">
          ${
            analogs.length
              ? analogs
                  .map((analog) => {
                    const analogInit = analog.init_utc || analog.init || "Earlier case";
                    const analogError = analog.error_mm ?? analog.error ?? null;
                    const outcome = analog.bust === true ? "Bust" : analog.bust === false ? "No bust" : "Outcome unavailable";
                    return `<div class="analog-card"><strong class="font-mono">${escapeHtml(analogInit)}</strong><span>${escapeHtml(outcome)}${analogError === null ? "" : ` · ${escapeHtml(formatMm(analogError))} error`}</span></div>`;
                  })
                  .join("")
              : `<div class="empty-evidence">No earlier comparable cases were supplied for this replay.</div>`
          }
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
        <dl class="region-provenance-grid">
          <div><dt>Source key</dt><dd class="font-mono">${escapeHtml(sourceKey || "Not supplied")}</dd></div>
          <div><dt>GRIB steps</dt><dd class="font-mono">${escapeHtml(gribSteps || "Not supplied")}</dd></div>
          <div class="region-provenance-wide"><dt>Provenance</dt><dd class="font-mono">${escapeHtml(provenance)}</dd></div>
        </dl>
        <ul class="caveats-list">
          ${caveats.map((c) => `<li>${escapeHtml(c)}</li>`).join("")}
          <li>Data mode: <code class="font-mono">${escapeHtml(dataMode)}</code></li>
          <li>Provenance: <code class="font-mono">${escapeHtml(provenance)}</code></li>
        </ul>
      </div>
    </div>
  `;

  panel.querySelectorAll("[data-curve-lead]").forEach((button) => {
    button.addEventListener("click", () => onSelectLead?.(Number(button.dataset.curveLead)));
  });
}
