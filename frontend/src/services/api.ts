const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Simple token storage in localStorage (client-side only)
const getAuthToken = () => {
  if (typeof window !== "undefined") {
    return localStorage.getItem("auth_token");
  }
  return null;
};

const setAuthToken = (token: string | null) => {
  if (typeof window !== "undefined") {
    if (token) localStorage.setItem("auth_token", token);
    else localStorage.removeItem("auth_token");
  }
};

async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers: any = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    setAuthToken(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API request failed: ${response.statusText}`);
  }

  return response.json();
}

export async function login(email: string, password: string) {
  const data = await apiFetch(`/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
    method: "POST",
  });
  
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

export async function register(email: string, password: string, full_name: string) {
  return apiFetch(`/auth/register?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}&full_name=${encodeURIComponent(full_name)}`, {
    method: "POST",
  });
}

export async function logout() {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } finally {
    setAuthToken(null);
  }
}

export async function fetchHealth() {
  return apiFetch("/health");
}

export async function fetchDashboard() {
  return apiFetch("/monitoring/dashboard");
}

export async function fetchSystemMetrics(detailed = true) {
  return apiFetch(`/monitoring/system?detailed=${detailed}`);
}

export async function fetchAlerts(limit = 50) {
  return apiFetch(`/monitoring/alerts?limit=${limit}`);
}

export async function fetchApplicationMetrics() {
  return apiFetch("/monitoring/application");
}

export async function fetchPerformanceSummary() {
  return apiFetch("/monitoring/performance/summary");
}

export async function fetchSubscriptionAudit() {
  return apiFetch("/audit/subscriptions");
}

export async function fetchBottlenecks() {
  return apiFetch("/analysis/bottlenecks");
}
