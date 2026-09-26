import { getEvaluation, getHealth, getRegion, getReplay } from "./api.js";
import { createMap } from "./map.js";
import { renderRegion } from "./region.js";
import { renderTrust } from "./trust.js";
import "./styles.css";

const initSelect = document.querySelector("#init");
const lead = document.querySelector("#lead");
const leadValue = document.querySelector("#lead-value");
const provenance = document.querySelector("#provenance");
const panel = document.querySelector("#region-panel");
const ribbon = document.querySelector("#fixture-ribbon");
let current = { init: "2018-08-01", lead: 1 };

const map = createMap(document.querySelector("#map"), async (regionId) => {
  try { renderRegion(panel, await getRegion(regionId, current.init, current.lead)); }
  catch (error) { panel.innerHTML = `<h2>Region details</h2><p>${error.message}</p>`; }
});

async function loadReplay() {
  current = { init: initSelect.value, lead: Number(lead.value) };
  leadValue.value = current.lead;
  leadValue.textContent = current.lead;
  try {
    const replay = await getReplay(current.init, current.lead);
    map.render(replay);
    provenance.textContent = `Issue ${current.init} 00 UTC · ${replay.model} · ${replay.truth_source}`;
  } catch (error) {
    provenance.textContent = error.message;
  }
}

async function boot() {
  try {
    const health = await getHealth();
    ribbon.hidden = health.data_mode !== "fixture";
    ["2018-08-01"].forEach((date) => initSelect.add(new Option(date, date)));
    await loadReplay();
    renderTrust(document.querySelector("#trust"), await getEvaluation());
  } catch (error) {
    provenance.textContent = `Unable to reach local API: ${error.message}`;
  }
}

initSelect.addEventListener("change", loadReplay);
lead.addEventListener("input", loadReplay);
boot();

