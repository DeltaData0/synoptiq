/**
 * Left Control Dock component for Synoptiq.
 * Manages issue-time selection, discrete Day 1-10 selector buttons,
 * risk legend, and provenance telemetry.
 */

import { escapeHtml } from "./format.js";
import { renderLegend } from "./legend.js";

/**
 * Initializes and binds the control dock.
 * @param {HTMLElement} container
 * @param {object} options
 */
export function setupControls(container, { inits, selectedInit, selectedLead, onInitChange, onLeadChange }) {
  container.innerHTML = `
    <div class="dock-section">
      <div class="dock-title-row">
        <span class="dock-eyebrow">REPLAY PARAMETERS</span>
      </div>

      <div class="control-group">
        <label for="init-select" class="control-label">
          <span>ISSUE INITIALIZATION</span>
          <span class="control-tag">00 UTC</span>
        </label>
        <div class="select-wrapper">
          <select id="init-select" class="select-init" aria-label="Forecast issue date">
            ${inits
              .map(
                (d) => `<option value="${escapeHtml(d)}" ${d === selectedInit ? "selected" : ""}>${escapeHtml(d)}</option>`
              )
              .join("")}
          </select>
        </div>
      </div>

      <div class="control-group">
        <div class="control-label-row">
          <label class="control-label" id="lead-label">FORECAST LEAD HORIZON</label>
          <span class="lead-active-pill" id="lead-active-display">Lead Day ${selectedLead}</span>
        </div>

        <div class="lead-button-grid" role="group" aria-labelledby="lead-label">
          ${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            .map((day) => {
              const isSelected = day === selectedLead;
              const isDay10 = day === 10;
              const tooltip = isDay10
                ? "Day 10 is unavailable because the exact +240–+243-hour accumulation is not evidenced."
                : `Lead Day ${day}`;

              return `
                <button
                  type="button"
                  class="btn-lead ${isSelected ? "btn-lead-active" : ""} ${isDay10 ? "btn-lead-day10" : ""}"
                  data-lead="${day}"
                  title="${escapeHtml(tooltip)}"
                  aria-pressed="${isSelected ? "true" : "false"}"
                >
                  <span class="lead-num">D${day}</span>
                  ${isDay10 ? '<span class="lead-badge-gray">N/A</span>' : ""}
                </button>
              `;
            })
            .join("")}
        </div>
        <p class="lead-hint">
          Click Day 10 to inspect the audited unavailable state. Days 2–9 test fixture absence.
        </p>
      </div>
    </div>

    <div class="dock-section dock-legend-section" id="dock-legend-container"></div>

    <div class="dock-section dock-summary-section">
      <div class="dock-title-row">
        <span class="dock-eyebrow">SOURCE ARCHITECTURE</span>
      </div>
      <dl class="provenance-specs">
        <div>
          <dt>Forecast Model</dt>
          <dd id="spec-model">GEFSv12 Reforecast (00 UTC)</dd>
        </div>
        <div>
          <dt>Truth Target</dt>
          <dd id="spec-truth">IMD 0.25&deg; Daily (03–03 UTC)</dd>
        </div>
        <div>
          <dt>Spatial Unit</dt>
          <dd id="spec-domain">Fixture geometry; final land grid pending D1-05</dd>
        </div>
        <div>
          <dt>Window Semantics</dt>
          <dd id="spec-window">Awaiting replay data</dd>
        </div>
      </dl>
    </div>
  `;

  // Render the legend inside the dock
  const legendContainer = container.querySelector("#dock-legend-container");
  if (legendContainer) {
    renderLegend(legendContainer);
  }

  // Bind Init select change
  const selectInit = container.querySelector("#init-select");
  selectInit.addEventListener("change", (e) => {
    onInitChange(e.target.value);
  });

  // Bind Lead buttons
  const leadButtons = container.querySelectorAll(".btn-lead");
  leadButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const lead = Number(btn.getAttribute("data-lead"));
      onLeadChange(lead);
    });
  });

  return {
    updateSelectedLead(lead) {
      const display = container.querySelector("#lead-active-display");
      if (display) display.textContent = `Lead Day ${lead}`;

      const buttons = container.querySelectorAll(".btn-lead");
      buttons.forEach((btn) => {
        const bLead = Number(btn.getAttribute("data-lead"));
        const isActive = bLead === lead;
        btn.classList.toggle("btn-lead-active", isActive);
        btn.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    },
    updateAvailableInits(initsList, currentInit) {
      if (selectInit) {
        selectInit.innerHTML = initsList
          .map(
            (d) => `<option value="${escapeHtml(d)}" ${d === currentInit ? "selected" : ""}>${escapeHtml(d)}</option>`
          )
          .join("");
      }
    },
    updateProvenance({ model, truth_source, window_quality, window_text, data_mode, lead }) {
      const specModel = container.querySelector("#spec-model");
      const specTruth = container.querySelector("#spec-truth");
      const specWindow = container.querySelector("#spec-window");
      const specDomain = container.querySelector("#spec-domain");
      if (specModel && model) specModel.textContent = model;
      if (specTruth && truth_source) specTruth.textContent = truth_source;
      if (specDomain) {
        specDomain.textContent =
          data_mode === "historical_replay"
            ? "Fixed 2° India-Land Grid"
            : "Fixture geometry; final land grid pending D1-05";
      }
      if (specWindow) {
        if (window_text) {
          specWindow.textContent = window_text;
        } else if (window_quality === "exact") {
          specWindow.textContent = "Exact (03:00–03:00 UTC)";
        } else if (window_quality === "approximate") {
          specWindow.textContent = "Approximate window";
        } else if (window_quality === "unavailable") {
          specWindow.textContent =
            Number(lead) === 10
              ? "Unavailable (exact +240–+243h not evidenced)"
              : "Unavailable";
        } else {
          specWindow.textContent = "Awaiting replay data";
        }
      }
    },
  };
}
