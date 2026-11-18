import { API_URL } from "@/lib/config";
import { clearSession, getToken, redirectToLogin } from "@/lib/auth/session";
import { useSettingsStore } from "@/lib/stores/settings-store";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  json?: unknown;
  body?: FormData;
  query?: Query;
  /** false untuk endpoint publik (login): tanpa token dan tanpa redirect saat 401. */
  auth?: boolean;
}

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return `${API_URL}/${path.replace(/^\/+/, "")}${qs ? `?${qs}` : ""}`;
}

// Backend punya dua bentuk error: HTTPException → {detail}, handler kustom →
// {success: false, error: {code, message}}.
async function toApiError(response: Response): Promise<ApiError> {
  let code = `HTTP_${response.status}`;
  let message = `Permintaan gagal (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      message = body.detail;
    } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } else if (body?.error?.message) {
      message = body.error.message;
      code = body.error.code ?? code;
    }
  } catch {
    // body bukan JSON; pakai pesan bawaan
  }
  return new ApiError(code, message, response.status);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", json, body, query, auth = true } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  if (json !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : body,
      signal: AbortSignal.timeout(useSettingsStore.getState().apiTimeout),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError("TIMEOUT", "Permintaan melebihi batas waktu. Coba lagi.", 0);
    }
    throw new ApiError("NETWORK_ERROR", "Tidak dapat terhubung ke server.", 0);
  }

  if (!response.ok) {
    const apiError = await toApiError(response);
    if (auth && response.status === 401) {
      // Sesi kedaluwarsa/dicabut: buang cookie lalu kembali ke login.
      clearSession();
      redirectToLogin();
    }
    throw apiError;
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function errorMessage(error: unknown, fallback = "Terjadi kesalahan"): string {
  return error instanceof Error && error.message ? error.message : fallback;
}
