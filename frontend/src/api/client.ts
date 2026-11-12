import type { AuthTokensResponse } from "@/types/api";

const STORAGE_KEY = "clearguard_admin_tokens";
const API_URL_STORAGE_KEY = "clearguard_api_base_url";

export const DEFAULT_API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/+$/, "");

export function getApiBaseUrl(): string {
  const custom = localStorage.getItem(API_URL_STORAGE_KEY);
  return (custom?.trim() || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export function setApiBaseUrl(url: string): void {
  const trimmed = url.trim().replace(/\/+$/, "");
  if (!trimmed || trimmed === DEFAULT_API_BASE_URL) {
    localStorage.removeItem(API_URL_STORAGE_KEY);
  } else {
    localStorage.setItem(API_URL_STORAGE_KEY, trimmed);
  }
}

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

export function getStoredTokens(): StoredTokens | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredTokens>;
    if (!parsed.accessToken || !parsed.refreshToken) return null;
    return {
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
    };
  } catch {
    return null;
  }
}

export function saveTokens(tokens: AuthTokensResponse): void {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    } satisfies StoredTokens),
  );
}

export function clearTokens(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const current = getStoredTokens();
    if (!current?.refreshToken) return null;

    try {
      const response = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: current.refreshToken }),
      });

      if (!response.ok) {
        clearTokens();
        return null;
      }

      const data = (await response.json()) as AuthTokensResponse;
      saveTokens(data);
      return data.access_token;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

function extractErrorDetail(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const obj = payload as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  if (Array.isArray(obj.detail)) {
    const first = obj.detail[0] as Record<string, unknown> | undefined;
    if (first && typeof first.msg === "string") return first.msg;
  }
  if (typeof obj.message === "string") return obj.message;
  return fallback;
}

export interface RequestOptions extends RequestInit {
  auth?: boolean;
  _retried?: boolean;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { auth = true, _retried = false, headers, body, ...rest } = options;
  const url = `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;

  const reqHeaders = new Headers(headers);
  if (body && !reqHeaders.has("Content-Type")) {
    reqHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    const tokens = getStoredTokens();
    if (tokens?.accessToken) {
      reqHeaders.set("Authorization", `Bearer ${tokens.accessToken}`);
    }
  }

  const response = await fetch(url, {
    ...rest,
    headers: reqHeaders,
    body,
  });

  if (response.status === 401 && auth && !_retried) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest<T>(path, { ...options, _retried: true });
    }
  }

  if (!response.ok) {
    let errorData: unknown = null;
    try {
      errorData = await response.json();
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(
      response.status,
      extractErrorDetail(errorData, `Request failed with status ${response.status}`),
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

