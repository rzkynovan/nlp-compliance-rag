import { apiRequest } from "./client";
import type {
  AuditHistoryStats,
  AuditRequest,
  AuditResponse,
  ExperimentListResponse,
  GoldenDatasetResponse,
  LoginResponse,
  MeResponse,
  UploadDocumentResult,
  UsageStats,
} from "./types";

export * from "./types";
export { ApiError, errorMessage } from "./client";
export { queryKeys } from "./query-keys";

// ── Auth ─────────────────────────────────────────────────────────────────────

export function loginApi(username: string, password: string) {
  return apiRequest<LoginResponse>("auth/login", {
    method: "POST",
    json: { username, password },
    auth: false,
  });
}

export function getMeApi() {
  return apiRequest<MeResponse>("auth/me");
}

export function logoutApi() {
  return apiRequest<unknown>("auth/logout", { method: "POST" });
}

// ── Audit ────────────────────────────────────────────────────────────────────

export function analyzeSop(data: AuditRequest) {
  return apiRequest<AuditResponse>("audit/analyze", { method: "POST", json: data });
}

export function getAuditHistory(skip = 0, limit = 20, search = "", status = "") {
  return apiRequest<AuditResponse[]>("audit/history", {
    query: { skip, limit, search, status },
  });
}

export function getAuditHistoryStats() {
  return apiRequest<AuditHistoryStats>("audit/history/stats");
}

export function uploadDocument(file: File, useLlamaparseCache?: boolean) {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<UploadDocumentResult>("audit/upload", {
    method: "POST",
    body,
    query: { use_llamaparse_cache: useLlamaparseCache },
  });
}

// ── Lainnya ──────────────────────────────────────────────────────────────────

export function searchRegulations(query: string, regulator?: string, topK = 5) {
  return apiRequest<unknown>("regulations/search", {
    method: "POST",
    json: { query, regulator, top_k: topK },
  });
}

export function getExperiments(skip = 0, limit = 20) {
  return apiRequest<ExperimentListResponse>("experiments/list", { query: { skip, limit } });
}

export function healthCheck() {
  return apiRequest<{ status: string }>("health", { auth: false });
}

export function getUsageStats() {
  return apiRequest<UsageStats>("usage");
}

export function getGoldenDataset() {
  return apiRequest<GoldenDatasetResponse>("evaluation/golden-dataset");
}
