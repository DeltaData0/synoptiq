export function renderRegion(panel, data) {
  const probability = data.p_bust === null ? "No data" : `${Math.round(data.p_bust * 100)}%`;
  panel.innerHTML = `
    <h2>${data.region_id}</h2>
    <dl>
      <dt>P(bust)</dt><dd>${probability}</dd>
      <dt>Forecast rain</dt><dd>${data.forecast_mm ?? "Not available"} mm</dd>
      <dt>Threshold</dt><dd>${data.threshold_mm ?? "Not available"} mm/day</dd>
      <dt>Window quality</dt><dd>${data.window_quality}</dd>
    </dl>
    <p class="caveat">${data.caveats.join(" ")}</p>`;
}

