const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function apiFetch<T>(
  path: string,
  token: string | null,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!response.ok)
    throw new Error("The IDHTM service could not complete that request.");
  return response.json();
}

export const telemetryService = {
  scenarios: (token: string | null) => apiFetch("/telemetry/scenarios", token),
  latest: (token: string | null) => apiFetch("/telemetry/latest", token),
  alerts: (token: string | null) => apiFetch("/alerts", token),
};

export const flightsService = {
  active: (token: string | null) => apiFetch("/flights/active", token),
  list: (token: string | null) => apiFetch("/flights", token),
  get: (token: string | null, flightId: number | string) =>
    apiFetch(`/flights/${flightId}`, token),
  start: (token: string | null, forceNew?: boolean) =>
    apiFetch(`/flights/start${forceNew ? "?force_new=true" : ""}`, token, {
      method: "POST",
    }),
  end: (token: string | null) =>
    apiFetch("/flights/end", token, { method: "POST" }),
};
