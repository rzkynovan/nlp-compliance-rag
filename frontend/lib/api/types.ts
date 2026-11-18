import type { UserRole } from "@/lib/auth/session";

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
  | "out_of_scope"
  | "noise"
  | "unclear";

export type AnalysisMode =
  | "multi_agent_rag"
  | "llm_only"
  | "gate_rejected"
  | "noise_filtered"
  | "unclear_text"
  | "greeting"
  | "out_of_scope";

export type RetrievalMode = "exact" | "hybrid" | "dense" | "dense_only" | "none";

export interface AuditRequest {
  clause: string;
  clause_id?: string;
  context?: string;
  top_k?: number;
  regulator?: "all" | "BI" | "OJK";
  use_cache?: boolean;
}

export interface EvidenceItem {
  regulation: string;
  article: string;
  article_text: string;
  relevance_score: number;
}

export interface AgentVerdict {
  agent_name: string;
  status: ComplianceStatus;
  confidence: number;
  violations: string[];
  evidence: EvidenceItem[];
  reasoning: string;
  checklist_topic?: string | null;
  checklist_covered?: string[];
  missing_elements?: string[];
}

/** Rujukan pasal Top-K (Subbab 3.3.3 proposal). */
export interface EvidenceTrailItem {
  agent?: string;
  regulator?: string;
  document?: string;
  bab?: string;
  pasal?: string;
  relevance_score?: number;
  rank?: number | null;
}

export interface AuditResponse {
  request_id: string;
  timestamp: string;
  clause: string;
  clause_id?: string | null;
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
  is_sop_clause?: boolean;
  gate_confidence?: number;
  gate_model?: string;
  gate_decision?: "REGULATION_CLAUSE_VALID" | "NOT_REGULATION_CLAUSE";
  evidence_trail?: EvidenceTrailItem[];
  analysis_mode?: AnalysisMode | null;
  retrieval_mode?: RetrievalMode | null;
  query_type?: QueryType;
  summary?: string;
  from_cache?: boolean;
}

export interface AuditHistoryStats {
  total: number;
  compliant: number;
  non_compliant: number;
  partially_compliant: number;
  not_addressed: number;
  unclear: number;
  avg_latency_ms: number;
}

export interface UploadDocumentResult {
  filename: string;
  file_size_kb: number;
  text: string;
  clauses: string[];
  clause_count: number;
  parsed_from_cache: boolean;
}

export interface UsageStats {
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
}

export interface ExperimentRun {
  run_id: string;
  experiment_id: string;
  experiment_name: string;
  status: string;
  start_time: string;
  end_time?: string | null;
  params?: Record<string, unknown> | null;
  metrics?: Record<string, unknown> | null;
  artifacts?: string[];
  tags?: Record<string, string>;
}

export interface ExperimentListResponse {
  experiments: ExperimentRun[];
  total: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
}

export interface MeResponse {
  username: string;
  role: UserRole;
}

export interface GoldenDatasetItem {
  clause_id: string;
  clause: string;
  category: string;
  expected_status: string;
  expected_bi: string;
  expected_ojk: string;
  violated_articles: string[];
  error_description: string;
  predicted_status?: string | null;
  predicted_bi?: string | null;
  predicted_ojk?: string | null;
  is_correct?: boolean | null;
  latency_ms?: number | null;
}

export interface GoldenDatasetResponse {
  total: number;
  correct?: number | null;
  accuracy?: number | null;
  has_predictions: boolean;
  evaluation_file?: string | null;
  items: GoldenDatasetItem[];
}
