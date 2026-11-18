// Sesi = satu cookie `access_token` (JWT dari backend). Username, role, dan
// masa berlaku dibaca dari payload JWT, sehingga proxy, server component, dan
// API client selalu melihat keadaan yang sama.

export type UserRole = "basic" | "advanced";

export interface Session {
  username: string;
  role: UserRole;
  /** Epoch ms; null bila token tidak membawa klaim `exp`. */
  expiresAt: number | null;
}

export const TOKEN_COOKIE = "access_token";
export const LOGIN_PATH = "/login";
export const HOME_AFTER_LOGIN = "/audit";
export const ADVANCED_ONLY = ["/experiments", "/settings", "/testing"];

const SESSION_MAX_AGE = 8 * 3600;
// Peninggalan versi lama: tiga penyimpanan auth yang tidak sinkron.
const LEGACY_COOKIES = ["user_role"];
const LEGACY_STORAGE_KEYS = ["accessToken", "auth-storage", "ui-storage"];

function decodePayload(token: string): Record<string, unknown> | null {
  const part = token.split(".")[1];
  if (!part) return null;
  try {
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return null;
  }
}

/**
 * Baca sesi dari token tanpa memverifikasi tanda tangan. Ini hanya pemeriksaan
 * optimistis untuk routing dan tampilan; otorisasi sebenarnya tetap di backend.
 */
export function parseSession(token: string | null | undefined): Session | null {
  if (!token) return null;
  const payload = decodePayload(token);
  if (!payload) return null;

  const username = typeof payload.sub === "string" ? payload.sub : "";
  const role = payload.role;
  if (!username || (role !== "basic" && role !== "advanced")) return null;

  const expiresAt = typeof payload.exp === "number" ? payload.exp * 1000 : null;
  if (expiresAt !== null && expiresAt <= Date.now()) return null;

  return { username, role, expiresAt };
}

export function isAdvancedOnly(pathname: string): boolean {
  return ADVANCED_ONLY.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

/** Tujuan setelah login: hanya path internal, dan hanya yang boleh diakses role. */
export function resolveRedirect(from: string | null | undefined, role: UserRole): string {
  if (!from || !from.startsWith("/") || from.startsWith("//") || from.includes("\\")) {
    return HOME_AFTER_LOGIN;
  }
  const pathname = from.split(/[?#]/)[0];
  if (pathname === LOGIN_PATH) return HOME_AFTER_LOGIN;
  if (isAdvancedOnly(pathname) && role !== "advanced") return HOME_AFTER_LOGIN;
  return from;
}

// ── Browser only ─────────────────────────────────────────────────────────────

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  const entry = document.cookie.split("; ").find((c) => c.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

function expireCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0; SameSite=Lax`;
}

function clearLegacyState() {
  LEGACY_COOKIES.forEach(expireCookie);
  try {
    LEGACY_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
  } catch {
    // localStorage bisa diblokir; sesi tetap benar karena hanya bergantung cookie
  }
}

/** Token yang masih berlaku, atau null. */
export function getToken(): string | null {
  const token = readCookie(TOKEN_COOKIE);
  return parseSession(token) ? token : null;
}

export function saveSession(token: string): Session | null {
  const session = parseSession(token);
  if (!session) return null;

  const remaining = session.expiresAt
    ? Math.floor((session.expiresAt - Date.now()) / 1000)
    : SESSION_MAX_AGE;
  const maxAge = Math.max(0, Math.min(SESSION_MAX_AGE, remaining));
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
  clearLegacyState();
  return session;
}

export function clearSession() {
  expireCookie(TOKEN_COOKIE);
  clearLegacyState();
}

/**
 * Keluar lewat navigasi penuh, bukan router.push: cache router di browser ikut
 * terbuang sehingga halaman yang sudah di-prefetch untuk sesi lama tidak dipakai.
 */
export function redirectToLogin(withReturnPath = true) {
  const { pathname, search } = window.location;
  if (pathname === LOGIN_PATH) return;
  const from = withReturnPath && pathname !== "/" ? `?from=${encodeURIComponent(pathname + search)}` : "";
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- navigasi penuh disengaja, lihat komentar di atas
  window.location.assign(`${LOGIN_PATH}${from}`);
}
