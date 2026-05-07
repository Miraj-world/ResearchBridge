const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function parseEnvelope(response) {
  const json = await response.json();
  if (!response.ok || !json.success) {
    throw new Error(json.error || 'Request failed');
  }
  return json.data;
}

async function safeFetch(url, options) {
  try {
    return await fetch(url, options);
  } catch (_err) {
    throw new Error(
      'Failed to reach backend API at http://localhost:8000. Start backend and verify dependency preflight passed.'
    );
  }
}

export async function uploadPaper(file, userLevel) {
  const form = new FormData();
  form.append('file', file);
  form.append('user_level', userLevel);

  const response = await safeFetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: form
  });

  return parseEnvelope(response);
}

export async function getPaper(paperId) {
  const response = await safeFetch(`${API_BASE}/paper/${paperId}`);
  return parseEnvelope(response);
}

export async function listPapers() {
  const response = await safeFetch(`${API_BASE}/papers`);
  return parseEnvelope(response);
}

export async function sendChat(payload) {
  const response = await safeFetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return parseEnvelope(response);
}

export async function comparePapers(paperId1, paperId2) {
  const response = await safeFetch(`${API_BASE}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_id_1: paperId1, paper_id_2: paperId2 })
  });
  return parseEnvelope(response);
}
