const API_BASE = import.meta.env.VITE_API_URL || '';

async function getAuthHeaders() {
  // Try to get Supabase session token from localStorage
  const raw = localStorage.getItem('nexus_session');
  if (raw) {
    try {
      const session = JSON.parse(raw);
      if (session?.access_token) {
        return { Authorization: `Bearer ${session.access_token}` };
      }
    } catch {}
  }
  return {};
}

async function request(method, path, body, isFormData = false) {
  const headers = await getAuthHeaders();
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  const opts = { method, headers };
  if (body) {
    opts.body = isFormData ? body : JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json();
  if (!res.ok) {
    const msg = data?.error?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

// ── Scans ───────────────────────────────────────────────────────
export function submitScan(payload) {
  return request('POST', '/api/scans', payload);
}

export function getScan(scanId) {
  return request('GET', `/api/scans/${scanId}`);
}

export function listScans(page = 1, pageSize = 20) {
  return request('GET', `/api/scans?page=${page}&page_size=${pageSize}`);
}

// ── Reports / SOAR artifacts ────────────────────────────────────
export function getReports(scanId) {
  return request('GET', `/api/reports/${scanId}`);
}

// ── Connections ─────────────────────────────────────────────────
export function startConnection(provider) {
  return request('POST', '/api/connections', { provider });
}

export function listConnections() {
  return request('GET', '/api/connections');
}

export function deleteConnection(id) {
  return request('DELETE', `/api/connections/${id}`);
}

export function syncConnection(id) {
  return request('POST', `/api/connections/${id}/sync`);
}

// ── Agent Profiles ──────────────────────────────────────────────
export function listAgentProfiles() {
  return request('GET', '/api/agent-profiles');
}

export function saveAgentProfile(payload) {
  return request('POST', '/api/agent-profiles', payload);
}

// ── Auth / Session ──────────────────────────────────────────────
export function validateSession() {
  return request('POST', '/api/auth/session');
}

// ── WebSocket helper ────────────────────────────────────────────
export function connectScanSocket(scanId, onMessage) {
  const wsBase = API_BASE.replace(/^http/, 'ws') || `ws://${window.location.host}`;
  const ws = new WebSocket(`${wsBase}/ws/scan/${scanId}`);
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onMessage(data);
    } catch {}
  };
  ws.onerror = () => {};
  ws.onclose = () => {};
  return ws;
}
