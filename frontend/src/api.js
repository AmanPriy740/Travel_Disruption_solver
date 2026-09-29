const BASE = "/api";

async function j(res) {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  itineraries: () => fetch(`${BASE}/itineraries`).then(j),
  feed: (since = 0) => fetch(`${BASE}/feed?since=${since}`).then(j),
  notifications: () => fetch(`${BASE}/notifications`).then(j),
  auditLog: () => fetch(`${BASE}/audit-log`).then(j),
  metrics: () => fetch(`${BASE}/metrics`).then(j),
  injectSingle: (paxId) =>
    fetch(`${BASE}/inject/single${paxId ? `?pax_id=${paxId}` : ""}`, {
      method: "POST",
    }).then(j),
  injectStorm: (count = 12) =>
    fetch(`${BASE}/inject/storm?count=${count}`, { method: "POST" }).then(j),
  approve: (auditId) =>
    fetch(`${BASE}/audit-log/${auditId}/approve`, { method: "POST" }).then(j),
  decline: (auditId) =>
    fetch(`${BASE}/audit-log/${auditId}/decline`, { method: "POST" }).then(j),
};
