const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json();
}

export const getHealth = () => request("/health");
export const getReplay = (init, lead) => request(`/v1/replay?init=${init}&lead=${lead}`);
export const getRegion = (id, init, lead) => request(`/v1/region/${id}?init=${init}&lead=${lead}`);
export const getEvaluation = () => request("/v1/evaluation");

