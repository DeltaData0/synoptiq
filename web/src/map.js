/**
 * Center Geospatial Leaflet Map component for Synoptiq.
 * Renders fixed 2-degree regional GeoJSON choropleth offline without external map tiles.
 */

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { formatProbability, formatUtcTime, formatWindowInterval, escapeHtml } from "./format.js";
import { getTierColor, getTierStroke, PALETTE } from "./legend.js";

export function createMap(containerElement, onSelectRegion) {
  // Initialize Leaflet map centered on central India with NO external tile layers
  const map = L.map(containerElement, {
    attributionControl: false,
    zoomControl: false,
    minZoom: 3,
    maxZoom: 9,
  }).setView([21.5, 78.5], 5);

  // Add custom zoom control in top-right
  L.control.zoom({ position: "topright" }).addTo(map);

  let currentLayer = null;
  let selectedId = null;

  // Floating HUD element inside map container
  let hudElement = containerElement.querySelector(".map-hud");
  if (!hudElement) {
    hudElement = document.createElement("div");
    hudElement.className = "map-hud";
    hudElement.setAttribute("aria-live", "polite");
    hudElement.innerHTML = `
      <div class="hud-item hud-lead">
        <span class="hud-label">TARGET LEAD</span>
        <span class="hud-val" id="hud-lead-val">Day 1 (+24h)</span>
      </div>
      <div class="hud-item hud-window">
        <span class="hud-label">VALID INTERVAL</span>
        <span class="hud-val" id="hud-window-val">—</span>
      </div>
      <div class="hud-item hud-mode">
        <span class="hud-label">STATUS</span>
        <span class="hud-val" id="hud-mode-val">Initializing...</span>
      </div>
    `;
    containerElement.appendChild(hudElement);
  }

  function getFeatureStyle(feature, isSelected) {
    const p = feature.properties || {};
    const tier = p.tier || "no_data";
    const fillColor = getTierColor(tier);
    const strokeColor = getTierStroke(tier);

    if (isSelected) {
      return {
        fillColor,
        fillOpacity: 0.92,
        color: "#38bdf8", // bright cyan selected outline
        weight: 3.5,
        opacity: 1,
      };
    }

    return {
      fillColor,
      fillOpacity: tier === "no_data" ? 0.45 : 0.78,
      color: strokeColor,
      weight: 1.5,
      opacity: 0.85,
    };
  }

  function render(geojsonPayload, activeLead, selectedRegionId = null) {
    selectedId = selectedRegionId;
    if (currentLayer) {
      currentLayer.remove();
      currentLayer = null;
    }

    // Update Floating HUD
    const features = geojsonPayload.features || [];
    const firstFeature = features[0]?.properties;
    const hudLead = containerElement.querySelector("#hud-lead-val");
    const hudWindow = containerElement.querySelector("#hud-window-val");
    const hudMode = containerElement.querySelector("#hud-mode-val");

    if (hudLead) hudLead.textContent = `Day ${activeLead} (+${activeLead * 24}h)`;
    if (hudWindow) {
      if (firstFeature?.valid_start_utc && firstFeature?.valid_end_utc) {
        hudWindow.textContent = `${formatUtcTime(firstFeature.valid_start_utc)} → ${formatUtcTime(
          firstFeature.valid_end_utc
        )}`;
      } else if (firstFeature?.window_quality === "unavailable") {
        hudWindow.textContent = "Accumulation window unaudited";
      } else {
        hudWindow.textContent = "Window unavailable";
      }
    }
    if (hudMode) {
      hudMode.textContent = `${geojsonPayload.data_mode?.toUpperCase() || "FIXTURE"} · ${features.length} REGIONS`;
    }

    // Create GeoJSON layer
    currentLayer = L.geoJSON(geojsonPayload, {
      style: (feature) => getFeatureStyle(feature, feature.properties.region_id === selectedId),
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        const tierMeta = PALETTE[p.tier] || PALETTE.no_data;
        const probText = formatProbability(p.p_bust);
        const thresholdText = p.threshold_mm !== null && p.threshold_mm !== undefined ? `${p.threshold_mm} mm` : "N/A";
        const reasonHtml = p.no_data_reason
          ? `<div class="map-tooltip-reason">⚠️ ${escapeHtml(p.no_data_reason)}</div>`
          : "";

        const tooltipHtml = `
          <div class="map-tooltip-card">
            <div class="map-tooltip-header">
              <span class="map-tooltip-id">${escapeHtml(p.region_id)}</span>
              <span class="map-tooltip-badge tier-${p.tier}">${escapeHtml(tierMeta.label)}</span>
            </div>
            <div class="map-tooltip-body">
              <div class="map-tooltip-stat">
                <span class="stat-lbl">P(bust):</span>
                <span class="stat-val font-mono">${escapeHtml(probText)}</span>
              </div>
              <div class="map-tooltip-stat">
                <span class="stat-lbl">Threshold:</span>
                <span class="stat-val font-mono">${escapeHtml(thresholdText)}</span>
              </div>
              <div class="map-tooltip-stat">
                <span class="stat-lbl">Window:</span>
                <span class="stat-val font-mono">${escapeHtml(p.window_quality)}</span>
              </div>
            </div>
            ${reasonHtml}
          </div>
        `;

        layer.bindTooltip(tooltipHtml, {
          className: "custom-leaflet-tooltip",
          sticky: true,
          direction: "top",
          offset: [0, -10],
          opacity: 1,
        });

        // Hover interaction
        layer.on("mouseover", () => {
          if (feature.properties.region_id !== selectedId) {
            layer.setStyle({
              weight: 2.5,
              color: "#f8fafc",
              fillOpacity: 0.9,
            });
          }
        });

        layer.on("mouseout", () => {
          if (feature.properties.region_id !== selectedId) {
            layer.setStyle(getFeatureStyle(feature, false));
          }
        });

        // Click interaction
        layer.on("click", () => {
          setSelected(p.region_id);
          onSelectRegion(p.region_id, feature);
        });
      },
    }).addTo(map);

    const bounds = currentLayer.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.35));
    }
  }

  function clear(lead) {
    if (currentLayer) {
      currentLayer.remove();
      currentLayer = null;
    }
    selectedId = null;

    const hudLead = containerElement.querySelector("#hud-lead-val");
    const hudWindow = containerElement.querySelector("#hud-window-val");
    const hudMode = containerElement.querySelector("#hud-mode-val");

    if (hudLead && lead) hudLead.textContent = `Day ${lead} (+${lead * 24}h)`;
    if (hudWindow) hudWindow.textContent = "Data unavailable";
    if (hudMode) hudMode.textContent = "NO DATA";
  }

  function setSelected(regionId) {
    selectedId = regionId;
    if (!currentLayer) return;

    currentLayer.eachLayer((layer) => {
      const featId = layer.feature?.properties?.region_id;
      layer.setStyle(getFeatureStyle(layer.feature, featId === selectedId));
      if (featId === selectedId) {
        layer.bringToFront();
      }
    });
  }

  return {
    render,
    clear,
    setSelected,
    invalidateSize: () => map.invalidateSize(),
  };
}
