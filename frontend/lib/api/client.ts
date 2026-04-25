import ky, { type KyInstance, type Options } from "ky";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface AuditRequest {
  clause: string;
  clause_id?: string;
  context?: string;
  top_k?: number;
  regulator?: "all" | "BI" | "OJK";
}

export type ComplianceStatus =
  | "COMPLIANT"
  | "NON_COMPLIANT"
  | "PARTIALLY_COMPLIANT"
  | "NEEDS_REVIEW"
  | "NOT_ADDRESSED"
  | "UNCLEAR";

export type QueryType =
  | "exact_regulation"
  | "hybrid_regulation"
  | "semantic_compliance"
  | "greeting"
  | "out_of_scope";

export type AnalysisMode = "multi_agent_rag" | "llm_only" | "greeting" | "out_of_scope";
export type RetrievalMode = "exact" | "hybrid" | "dense" | "dense_only" | "none";

export interface AgentVerdict {
  agent_name: string;
  status: string;
  confidence: number;
  violations: string[];
  evidence: {
    regulation: string;
    article: string;
    article_text: string;
    relevance_score: number;
  }[];
  reasoning: string;
}

export interface AuditResponse {
  request_id: string;
  timestamp: string;
  clause: string;
  clause_id?: string;
  regulator?: string;
  bi_verdict: AgentVerdict | null;
  ojk_verdict: AgentVerdict | null;
  final_status: ComplianceStatus;
  overall_confidence: number;
  risk_score: number;
  violations: string[];
  recommendations: string[];
  latency_ms: number;
  model_used?: string;
  tokens_used?: number;
  // Phase 7+: retrieval & query classification
  analysis_mode?: AnalysisMode;
  retrieval_mode?: RetrievalMode;
  query_type?: QueryType;
  summary?: string; // diisi untuk GREETING dan OUT_OF_SCOPE
  from_cache?: boolean;
}

const createApiClient = (options?: Options): KyInstance => {
  return ky.create({
    prefixUrl: API_URL,
    timeout: 120_000, // 2 menit — audit RAG bisa butuh waktu
    ...options,
    hooks: {
      beforeRequest: [
        (request) => {
          const token = typeof window !== "undefined" ? localStorage.getItem("accessToken") : null;
          if (token) {
            request.headers.set("Authorization", `Bearer ${token}`);
          }
        },
      ],
      afterResponse: [
        async (_request, _options, response) => {
          if (!response.ok) {
            try {
              const error = await response.json<{ error?: { code?: string; message?: string } }>();
              throw new ApiError(
                error.error?.code || "UNKNOWN_ERROR",
                error.error?.message || "An error occurred",
                response.status
              );
            } catch {
              throw new ApiError("NETWORK_ERROR", "Network error occurred", response.status);
            }
          }
        },
      ],
    },
  });
};

export const apiClient = createApiClient();

export { queryKeys } from "./query-keys";