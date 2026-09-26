import L from "leaflet";
import "leaflet/dist/leaflet.css";

const palette = { low: "#2d7d46", watch: "#d48a11", high: "#bd3131", no_data: "#68717c" };

export function createMap(element, onSelect) {
  const map = L.map(element, { attributionControl: false, zoomControl: true }).setView([22, 79], 5);
  let layer;
  function render(payload) {
    layer?.remove();
    layer = L.geoJSON(payload, {
      style: (feature) => ({ color: "#fff", weight: 1, fillColor: palette[feature.properties.tier], fillOpacity: 0.82 }),
      onEachFeature: (feature, mapLayer) => {
        const p = feature.properties;
        mapLayer.bindTooltip(`${p.region_id}: ${p.p_bust === null ? "No data" : `${Math.round(p.p_bust * 100)}% P(bust)`}`);
        mapLayer.on("click", () => onSelect(p.region_id));
      }
    }).addTo(map);
    const bounds = layer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.35));
  }
  return { render };
}

