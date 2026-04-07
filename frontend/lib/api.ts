import { apiClient } from "@/lib/api/client";
import type { AuditRequest, AuditResponse } from "@/lib/api/client";

export type { AuditRequest, AuditResponse };
export { apiClient };

export interface UploadDocumentResult {
  filename: string;
  file_size_kb: number;
  text: string;
  clauses: string[];
  clause_count: number;
}

export async function analyzeSop(data: AuditRequest): Promise<AuditResponse> {
  return apiClient.post("audit/analyze", { json: data }).json<AuditResponse>();
}

export async function getAuditHistory(skip: number = 0, limit: number = 20) {
  return apiClient.get("audit/history", { searchParams: { skip, limit } }).json();
}

export async function uploadDocument(file: File): Promise<UploadDocumentResult> {
  const formData = new FormData();
  formData.append("file", file);
  // Use ky without json Content-Type so multipart is set automatically
  return apiClient.post("audit/upload", { body: formData }).json<UploadDocumentResult>();
}

export async function searchRegulations(query: string, regulator?: string, topK: number = 5) {
  return apiClient.post("regulations/search", {
    json: { query, regulator, top_k: topK },
  }).json();
}

export async function getExperiments(skip: number = 0, limit: number = 20) {
  return apiClient.get("experiments/list", { searchParams: { skip, limit } }).json();
}

export async function healthCheck() {
  return apiClient.get("health").json();
}

export async function getUsageStats() {
  return apiClient.get("usage").json<{
    today: {
      date: string;
      total_tokens: number;
      total_cost_usd: number;
      api_calls: number;
      budget_limit_usd: number;
      remaining_usd: number;
      budget_percentage: number;
    };
    monthly: { monthly_cost_usd: number; monthly_api_calls: number };
    cache_stats: { memory_cache_size: number; disk_cache_count: number; ttl_hours: number };
  }>();
}