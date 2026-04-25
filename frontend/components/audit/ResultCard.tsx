"use client";

import { cn } from "@/lib/utils";
import type { AuditResponse, AgentVerdict } from "@/lib/api/client";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  FileText,
  Clock,
  Zap,
  MessageSquare,
  Ban,
  Search,
  GitMerge,
  Layers,
} from "lucide-react";

interface ResultCardProps {
  data: AuditResponse;
}

// ── Status config (6 kelas) ────────────────────────────────────────────
const statusConfig: Record<string, {
  icon: React.ElementType;
  label: string;
  color: string;
  bg: string;
  border: string;
}> = {
  COMPLIANT: {
    icon: CheckCircle2,
    label: "Patuh",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  NON_COMPLIANT: {
    icon: XCircle,
    label: "Tidak Patuh",
    color: "text-red-600",
    bg: "bg-red-50",
    border: "border-red-200",
  },
  PARTIALLY_COMPLIANT: {
    icon: AlertTriangle,
    label: "Sebagian Patuh",
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  NEEDS_REVIEW: {
    icon: AlertTriangle,
    label: "Perlu Review",
    color: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  NOT_ADDRESSED: {
    icon: HelpCircle,
    label: "Tidak Diatur",
    color: "text-slate-500",
    bg: "bg-slate-50",
    border: "border-slate-200",
  },
  UNCLEAR: {
    icon: HelpCircle,
    label: "Tidak Jelas",
    color: "text-slate-500",
    bg: "bg-slate-50",
    border: "border-slate-200",
  },
};

// ── Query type badge ───────────────────────────────────────────────────
const queryTypeConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  exact_regulation:   { label: "Exact Match",   icon: Search,    color: "text-blue-700 bg-blue-100" },
  hybrid_regulation:  { label: "Hybrid Search", icon: GitMerge,  color: "text-violet-700 bg-violet-100" },
  semantic_compliance:{ label: "Semantic",       icon: Layers,    color: "text-sky-700 bg-sky-100" },
  greeting:           { label: "Sapaan",         icon: MessageSquare, color: "text-teal-700 bg-teal-100" },
  out_of_scope:       { label: "Di Luar Scope",  icon: Ban,       color: "text-rose-700 bg-rose-100" },
};

const retrievalModeLabel: Record<string, string> = {
  exact:      "BM25 Exact",
  hybrid:     "Hybrid (BM25+Dense)",
  dense:      "Dense",
  dense_only: "Dense Only",
  none:       "—",
};

export function ResultCard({ data }: ResultCardProps) {
  const isGreeting   = data.analysis_mode === "greeting";
  const isOutOfScope = data.analysis_mode === "out_of_scope";
  const isSpecial    = isGreeting || isOutOfScope;

  const statusInfo = statusConfig[data.final_status] ?? statusConfig.UNCLEAR;
  const StatusIcon = statusInfo.icon;

  const qtCfg = data.query_type ? queryTypeConfig[data.query_type] : null;

  // ── GREETING / OUT_OF_SCOPE: tampilkan ringkasan saja ─────────────
  if (isSpecial) {
    return (
      <div className={cn(
        "rounded-xl border p-6",
        isGreeting
          ? "bg-teal-50 border-teal-200"
          : "bg-rose-50 border-rose-200"
      )}>
        <div className="flex items-center gap-3 mb-3">
          {isGreeting
            ? <MessageSquare className="h-7 w-7 text-teal-500" />
            : <Ban className="h-7 w-7 text-rose-500" />}
          <div>
            <h3 className={cn("font-semibold text-base",
              isGreeting ? "text-teal-800" : "text-rose-800"
            )}>
              {isGreeting ? "Sapaan Diterima" : "Pertanyaan Di Luar Cakupan"}
            </h3>
            <p className={cn("text-xs mt-0.5",
              isGreeting ? "text-teal-600" : "text-rose-600"
            )}>
              {isGreeting
                ? "Sistem menerima sapaan — tidak ada retrieval yang dijalankan"
                : "Pertanyaan tidak berkaitan dengan kepatuhan regulasi BI/OJK"}
            </p>
          </div>
        </div>
        {data.summary && (
          <p className={cn("text-sm leading-relaxed rounded-lg p-4 border",
            isGreeting
              ? "bg-white border-teal-100 text-teal-900"
              : "bg-white border-rose-100 text-rose-900"
          )}>
            {data.summary}
          </p>
        )}
      </div>
    );
  }

  // ── NORMAL audit result ────────────────────────────────────────────
  return (
    <div className={cn("rounded-xl border p-6 space-y-4", statusInfo.bg, statusInfo.border)}>

      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <StatusIcon className={cn("h-8 w-8 shrink-0", statusInfo.color)} />
          <div>
            <h3 className="font-semibold text-lg text-slate-900">{statusInfo.label}</h3>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-sm text-slate-500">
                Confidence: <span className="font-medium text-slate-700">
                  {(data.overall_confidence * 100).toFixed(0)}%
                </span>
              </span>
              {data.risk_score > 0 && (
                <span className="text-sm text-slate-500">
                  · Risk: <span className={cn("font-medium",
                    data.risk_score >= 0.7 ? "text-red-600"
                    : data.risk_score >= 0.4 ? "text-amber-600"
                    : "text-emerald-600"
                  )}>
                    {(data.risk_score * 100).toFixed(0)}%
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right shrink-0 space-y-1">
          <div className="flex items-center justify-end gap-1 text-xs text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            {data.latency_ms.toFixed(0)}ms
          </div>
          {data.tokens_used !== undefined && (
            <div className="flex items-center justify-end gap-1 text-xs text-slate-500">
              <Zap className="h-3.5 w-3.5" />
              {data.tokens_used} tokens
            </div>
          )}
          {data.from_cache && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-600">
              cache
            </span>
          )}
        </div>
      </div>

      {/* ── Meta badges: query_type + retrieval_mode ── */}
      {(qtCfg || data.retrieval_mode) && (
        <div className="flex flex-wrap gap-2">
          {qtCfg && (
            <span className={cn(
              "inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full",
              qtCfg.color
            )}>
              <qtCfg.icon className="h-3 w-3" />
              Query: {qtCfg.label}
            </span>
          )}
          {data.retrieval_mode && data.retrieval_mode !== "none" && (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full text-slate-600 bg-slate-100">
              <Search className="h-3 w-3" />
              Retrieval: {retrievalModeLabel[data.retrieval_mode] ?? data.retrieval_mode}
            </span>
          )}
          {data.analysis_mode === "llm_only" && (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full text-orange-700 bg-orange-100">
              LLM Only (no ChromaDB)
            </span>
          )}
        </div>
      )}

      {/* ── Clause ── */}
      <div className="rounded-lg bg-white p-4 border border-slate-200">
        <p className="text-xs text-slate-400 font-medium mb-1.5 uppercase tracking-wide">Klausa SOP</p>
        <p className="text-sm text-slate-700 leading-relaxed">{data.clause}</p>
      </div>

      {/* ── Agent Verdicts ── */}
      {(data.bi_verdict || data.ojk_verdict) && (
        <div className="grid grid-cols-2 gap-3">
          {data.bi_verdict && (
            <AgentVerdictCard title="BI Specialist" verdict={data.bi_verdict} />
          )}
          {data.ojk_verdict && (
            <AgentVerdictCard title="OJK Specialist" verdict={data.ojk_verdict} />
          )}
        </div>
      )}

      {/* ── Violations ── */}
      {data.violations.length > 0 && (
        <div>
          <h4 className="font-medium text-sm text-slate-900 mb-2 flex items-center gap-1.5">
            <XCircle className="h-4 w-4 text-red-500" />
            Pelanggaran Ditemukan ({data.violations.length})
          </h4>
          <ul className="space-y-1.5">
            {data.violations.map((v, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-700 bg-red-50 rounded-lg p-3 border border-red-100">
                <XCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Recommendations ── */}
      {data.recommendations.length > 0 && (
        <div>
          <h4 className="font-medium text-sm text-slate-900 mb-2 flex items-center gap-1.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            Rekomendasi ({data.recommendations.length})
          </h4>
          <ul className="space-y-1.5">
            {data.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700 bg-white rounded-lg p-3 border border-slate-200">
                <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-500" />
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Evidence Trail ── */}
      {(data.bi_verdict?.evidence?.length || data.ojk_verdict?.evidence?.length) ? (
        <div className="pt-3 border-t border-slate-200">
          <h4 className="font-medium text-sm text-slate-900 mb-2 flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-slate-500" />
            Evidence Trail
          </h4>
          <div className="space-y-2">
            {data.bi_verdict?.evidence?.map((ev, i) => (
              <EvidenceItem key={`bi-${i}`} evidence={ev} source="BI" />
            ))}
            {data.ojk_verdict?.evidence?.map((ev, i) => (
              <EvidenceItem key={`ojk-${i}`} evidence={ev} source="OJK" />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ── AgentVerdictCard ───────────────────────────────────────────────────
function AgentVerdictCard({ title, verdict }: { title: string; verdict: AgentVerdict }) {
  const cfg = statusConfig[verdict.status] ?? statusConfig.UNCLEAR;
  const StatusIcon = cfg.icon;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">{title}</span>
        <div className={cn("flex items-center gap-1", cfg.color)}>
          <StatusIcon className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">{cfg.label}</span>
        </div>
      </div>
      <div className="text-xs text-slate-500">
        Confidence: <span className="font-medium text-slate-700">
          {(verdict.confidence * 100).toFixed(0)}%
        </span>
      </div>
      {verdict.violations.length > 0 && (
        <div className="text-xs text-red-600 font-medium">
          {verdict.violations.length} pelanggaran
        </div>
      )}
      {verdict.reasoning && (
        <p className="text-xs text-slate-500 line-clamp-2 italic">
          "{verdict.reasoning}"
        </p>
      )}
    </div>
  );
}

// ── EvidenceItem ───────────────────────────────────────────────────────
function EvidenceItem({
  evidence,
  source,
}: {
  evidence: { regulation: string; article: string; article_text: string; relevance_score: number };
  source: "BI" | "OJK";
}) {
  return (
    <div className="rounded-lg bg-white border border-slate-200 p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-slate-800">
          {evidence.regulation} · {evidence.article}
        </span>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full font-medium",
          source === "BI"
            ? "bg-blue-100 text-blue-700"
            : "bg-violet-100 text-violet-700"
        )}>
          {source}
        </span>
      </div>
      <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
        {evidence.article_text}
      </p>
      <div className="mt-1.5 text-xs text-slate-400">
        Relevansi: {(evidence.relevance_score * 100).toFixed(0)}%
      </div>
    </div>
  );
}
