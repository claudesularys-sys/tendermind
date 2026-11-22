const BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("tm_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  auth: {
    register: (email: string, password: string) =>
      request<{ access_token: string }>("/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string }>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<User>("/v1/auth/me"),
  },

  tenders: {
    list: (params?: { country_code?: string; source_id?: string; page?: number }) => {
      const q = new URLSearchParams();
      if (params?.country_code) q.set("country_code", params.country_code);
      if (params?.source_id) q.set("source_id", params.source_id);
      if (params?.page) q.set("page", String(params.page));
      return request<TenderListResponse>(`/v1/tenders?${q}`);
    },
    save: (id: string) =>
      request<{ saved: boolean }>(`/v1/tenders/${id}/save`, { method: "POST" }),
    favorites: () => request<FavoriteOut[]>("/v1/tenders/favorites"),
  },

  profile: {
    get: () => request<CompanyProfile | null>("/v1/profile"),
    update: (data: Partial<CompanyProfile>) =>
      request<CompanyProfile>("/v1/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  sources: {
    list: () => request<SourceStatus[]>("/v1/sources"),
    trigger: (id: string) =>
      request<{ queued: boolean }>(`/v1/sources/${id}/trigger`, { method: "POST" }),
  },

  analytics: {
    map: () => request<MapItem[]>("/v1/analytics/map"),
  },
};

// ——— Types ———

export interface User {
  id: string;
  email: string;
  telegram_id: number | null;
  notif_enabled: boolean;
  created_at: string;
}

export interface Tender {
  id: string;
  external_id: string;
  source_id: string;
  country_code: string;
  country_name: string;
  city: string | null;
  title: string;
  title_en: string | null;
  equipment_summary: string | null;
  budget_usd: number | null;
  currency_original: string | null;
  budget_original: number | null;
  deadline: string;
  is_active: boolean;
  url: string;
  created_at: string;
  vector_score: number | null;
}

export interface TenderListResponse {
  items: Tender[];
  total: number;
  page: number;
  per_page: number;
}

export interface FavoriteOut {
  id: string;
  tender: Tender;
  note: string | null;
  saved_at: string;
}

export interface CompanyProfile {
  id: string;
  user_id: string;
  company_name: string;
  transformer_types: string[];
  power_kva_min: number | null;
  power_kva_max: number | null;
  voltage_kv: string[];
  certifications: string[];
  max_delivery_days: number | null;
  target_countries: string[];
  min_budget_usd: number | null;
  keywords_extra: string[];
  updated_at: string;
}

export interface SourceStatus {
  source_id: string;
  country_code: string;
  country_name: string;
  region: string;
  last_run_at: string | null;
  last_status: string | null;
  last_fetched: number | null;
  last_new: number | null;
  schedule: string;
}

export interface MapItem {
  country_code: string;
  country_name: string;
  count: number;
}
