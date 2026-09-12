const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function apiFetch<T>(path: string, token: string | null, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!response.ok) throw new Error('The IDHTM service could not complete that request.');
  return response.json();
}

export const telemetryService = {
  scenarios: (token: string | null) => apiFetch('/telemetry/scenarios', token),
  latest: (token: string | null) => apiFetch('/telemetry/latest', token),
  alerts: (token: string | null) => apiFetch('/alerts', token),
};
