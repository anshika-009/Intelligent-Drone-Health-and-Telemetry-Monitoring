const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!response.ok)
    throw new Error("The IDHTM service could not complete that request.");
  return response.json();
}
export const authService = {
  login: (email: string, password: string) =>
    apiFetch<{ token: string; user: { email: string; name?: string } }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    ),
  register: (email: string, password: string, name: string) =>
    apiFetch<{ token: string; user: { email: string; name: string } }>(
      "/auth/register",
      { method: "POST", body: JSON.stringify({ email, password, name }) },
    ),
};
export const telemetryService = {
  scenarios: () => apiFetch("/telemetry/scenarios"),
  latest: () => apiFetch("/telemetry/latest"),
  alerts: () => apiFetch("/alerts"),
};
