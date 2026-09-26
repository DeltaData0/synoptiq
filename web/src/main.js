/**
 * Synoptiq Web Dashboard — Main Orchestrator.
 * Coordinates offline Leaflet map, mission control dock, region inspector,
 * bottom trust strip, and truth-preserving error states.
 */

import { getAvailableInits, getEvaluation, getHealth, getRegion, getReplay } from "./api.js";
import { setupControls } from "./controls.js";
import { clearMapEmptyState, renderInspectorPrompt, renderMapEmptyState } from "./empty_state.js";
import { createMap } from "./map.js";
import { renderRegion } from "./region.js";
import { renderTrust } from "./trust.js";
import "./styles.css";

// App state
const state = {
  init: "2018-08-01",
  lead: 1,
  selectedRegionId: null,
  currentReplay: null,
  availableInits: ["2018-08-01"],
  dataMode: "fixture",
};

// DOM references
const ribbonEl = document.querySelector("#fixture-ribbon");
const navInitTime = document.querySelector("#nav-init-time");
const navLeadHorizon = document.querySelector("#nav-lead-horizon");
const navWindowSemantics = document.querySelector("#nav-window-semantics");
const navModeBadge = document.querySelector("#nav-mode-badge");
const navModeText = document.querySelector("#nav-mode-text");
const controlDockEl = document.querySelector("#control-dock");
const mapEl = document.querySelector("#map");
const mapOverlayEl = document.querySelector("#map-overlay");
const regionPanelEl = document.querySelector("#region-panel");
const trustEl = document.querySelector("#trust");

let controlsHandle = null;

// Initialize Map
const map = createMap(mapEl, async (regionId, feature) => {
  state.selectedRegionId = regionId;
  await loadRegionDetails(regionId, feature?.properties);
});

/**
 * Loads and displays regional inspector details.
 */
async function loadRegionDetails(regionId, fallbackProperties) {
  try {
    const regionData = await getRegion(regionId, state.init, state.lead);
    renderRegion(regionPanelEl, {
      regionData,
      fallbackProperties,
      lead: state.lead,
      onSelectLead: (l) => loadReplay(state.init, l),
    });
  } catch (err) {
    // If the region details endpoint returns 404 (common in fixture where only 1 cell has deep diagnostics),
    // truthfully render the map feature properties with an honest fallback notice.
    renderRegion(regionPanelEl, {
      regionData: null,
      fallbackProperties: fallbackProperties || { region_id: regionId, lead_day: state.lead },
      lead: state.lead,
      onSelectLead: (l) => loadReplay(state.init, l),
    });
  }
}

/**
 * Loads replay GeoJSON for the current init date and lead day.
 */
async function loadReplay(newInit, newLead) {
  state.init = newInit ?? state.init;
  state.lead = Number(newLead ?? state.lead);

  // Update navigation telemetry
  if (navInitTime) navInitTime.textContent = `${state.init} 00:00Z`;
  if (navLeadHorizon) navLeadHorizon.textContent = `Lead Day ${state.lead} (+${state.lead * 24}h)`;

  // Update controls state
  controlsHandle?.updateSelectedLead(state.lead);

  try {
    const replay = await getReplay(state.init, state.lead);
    state.currentReplay = replay;
    clearMapEmptyState(mapOverlayEl);

    // Render features on map
    map.render(replay, state.lead, state.selectedRegionId);

    // Determine window semantics to display in top bar
    const firstProps = replay.features?.[0]?.properties;
    if (navWindowSemantics) {
      if (firstProps?.window_quality === "unavailable") {
        navWindowSemantics.textContent = "Unaudited Window (Gray)";
      } else if (firstProps?.valid_start_utc && firstProps?.valid_end_utc) {
        navWindowSemantics.textContent = "Exact 03:00–03:00Z";
      } else {
        navWindowSemantics.textContent = "Unavailable";
      }
    }

    // Update controls specs
    controlsHandle?.updateProvenance({
      model: replay.model,
      truth_source: replay.truth_source,
      window_quality: firstProps?.window_quality,
    });

    // Check if the previously selected region still exists in this lead
    const matchedFeature = replay.features?.find(
      (f) => f.properties?.region_id === state.selectedRegionId
    );

    if (matchedFeature) {
      await loadRegionDetails(state.selectedRegionId, matchedFeature.properties);
    } else {
      state.selectedRegionId = null;
      renderInspectorPrompt(regionPanelEl);
    }
  } catch (error) {
    // When lead has no replay data (such as Day 2-9 returning 404 in fixture):
    // CLEAR STALE GEOMETRY IMMEDIATELY! Never show stale polygons.
    state.currentReplay = null;
    state.selectedRegionId = null;
    map.clear(state.lead);

    if (navWindowSemantics) {
      navWindowSemantics.textContent = "Data Unavailable";
    }

    // Render truthful empty state overlay on the map surface
    renderMapEmptyState(mapOverlayEl, {
      lead: state.lead,
      title: `Replay Data Unavailable: Day ${state.lead}`,
      message: `The local fixture contract only defines integration slices for Day 1 and Day 10. Per project rules, missing lead data is never fabricated.`,
      onReset: () => loadReplay(state.init, 1),
    });

    // Truthful inspector notice
    regionPanelEl.innerHTML = `
      <div class="inspector-prompt" role="status">
        <div class="prompt-icon">⚠️</div>
        <h3>Lead Day ${state.lead} Unavailable</h3>
        <p class="prompt-text">
          No historical replay slice exists for Lead Day ${state.lead} in the current fixture store.
        </p>
        <div class="prompt-hint">
          <span>Switch back to Day 1 to inspect active fixture polygons.</span>
        </div>
      </div>
    `;
  }
}

/**
 * Boots the application and loads initial contracts.
 */
async function boot() {
  try {
    // 1. Health check & Mode determination
    const health = await getHealth();
    state.dataMode = health.data_mode || "fixture";

    // Non-negotiable fixture warning strip: must remain visible in fixture mode
    if (ribbonEl) {
      ribbonEl.hidden = health.data_mode !== "fixture";
    }

    if (navModeBadge) {
      navModeBadge.className = `mode-badge mode-${health.data_mode}`;
    }
    if (navModeText) {
      navModeText.textContent = health.data_mode === "fixture" ? "FIXTURE MODE" : "HISTORICAL REPLAY";
    }

    // 2. Discover available initialization dates from API
    const inits = await getAvailableInits();
    state.availableInits = inits;
    if (!inits.includes(state.init) && inits.length > 0) {
      state.init = inits[0];
    }

    // 3. Initialize Control Dock
    controlsHandle = setupControls(controlDockEl, {
      inits: state.availableInits,
      selectedInit: state.init,
      selectedLead: state.lead,
      onInitChange: (init) => loadReplay(init, state.lead),
      onLeadChange: (lead) => loadReplay(state.init, lead),
    });

    // 4. Initial Inspector Prompt
    renderInspectorPrompt(regionPanelEl);

    // 5. Load Evaluation & Trust Strip
    const evaluation = await getEvaluation();
    renderTrust(trustEl, evaluation);

    // 6. Load Replay
    await loadReplay(state.init, state.lead);
  } catch (error) {
    console.error("Boot error:", error);
    if (regionPanelEl) {
      regionPanelEl.innerHTML = `
        <div class="inspector-prompt" role="alert">
          <div class="prompt-icon">❌</div>
          <h3>API Connection Error</h3>
          <p class="prompt-text">Unable to connect to local Synoptiq API: ${error.message}</p>
        </div>
      `;
    }
  }
}

// Window resize handling for Leaflet
window.addEventListener("resize", () => {
  map.invalidateSize();
});

// Boot the app
boot();
