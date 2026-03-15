const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error("Failed to fetch health");
  return response.json();
}

export async function fetchDashboard() {
  const response = await fetch(`${API_BASE_URL}/monitoring/dashboard`);
  if (!response.ok) throw new Error("Failed to fetch dashboard");
  return response.json();
}

export async function fetchSystemMetrics() {
  const response = await fetch(`${API_BASE_URL}/monitoring/system?detailed=true`);
  if (!response.ok) throw new Error("Failed to fetch system metrics");
  return response.json();
}

export async function fetchLogs(limit = 50) {
  const response = await fetch(`${API_BASE_URL}/monitoring/alerts?limit=${limit}`);
  if (!response.ok) throw new Error("Failed to fetch logs");
  return response.json();
}
