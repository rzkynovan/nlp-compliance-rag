import { cn } from "@/lib/utils";
import type { AuditResponse } from "@/lib/api";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  FileText,
  Clock,
  Zap,
} from "lucide-react";

interface ResultCardProps {
  data: AuditResponse;
}

const statusConfig = {
  COMPLIANT: {
    icon: CheckCircle2,
    label: "Patuh",
    color: "text-green-600",
    bg: "bg-green-50",
    border: "border-green-200",
  },
  NON_COMPLIANT: {
    icon: XCircle,
    label: "Tidak Patuh",
    color: "text-red-600",
    bg: "bg-red-50",
    border: "border-red-200",
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
};

export function ResultCard({ data }: ResultCardProps) {
  const statusInfo = statusConfig[data.final_status as keyof typeof statusConfig] || statusConfig.NOT_ADDRESSED;
  const StatusIcon = statusInfo.icon;

  return (
    <div className={cn("rounded-lg border p-6", statusInfo.bg, statusInfo.border)}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon className={cn("h-8 w-8", statusInfo.color)} />
          <div>
            <h3 className="font-semibold text-lg text-slate-900">
              {statusInfo.label}
            </h3>
            <p className="text-sm text-slate-500">
              Confidence: {(data.overall_confidence * 100).toFixed(0)}%
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 text-sm text-slate-500">
            <Clock className="h-4 w-4" />
            {data.latency_ms.toFixed(0)}ms
          </div>
          {data.tokens_used !== undefined && (
            <div className="flex items-center gap-1 text-sm text-slate-500">
              <Zap className="h-4 w-4" />
              {data.tokens_used} tokens
            </div>
          )}
        </div>
      </div>

      {/* Clause */}
      <div className="mb-4 rounded-md bg-white p-4 border border-slate-200">
        <p className="text-sm text-slate-600 leading-relaxed">{data.clause}</p>
      </div>

      {/* Agent Verdicts */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {data.bi_verdict && (
          <AgentVerdictCard
            title="BI Specialist"
            verdict={data.bi_verdict}
          />
        )}
        {data.ojk_verdict && (
          <AgentVerdictCard
            title="OJK Specialist"
            verdict={data.ojk_verdict}
          />
        )}
      </div>

      {/* Violations */}
      {data.violations.length > 0 && (
        <div className="mb-4">
          <h4 className="font-medium text-slate-900 mb-2">Pelanggaran Ditemukan:</h4>
          <ul className="space-y-2">
            {data.violations.map((violation, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-red-700 bg-red-50 rounded-md p-3"
              >
                <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
                {violation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div>
          <h4 className="font-medium text-slate-900 mb-2">Rekomendasi:</h4>
          <ul className="space-y-2">
            {data.recommendations.map((rec, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-slate-700 bg-slate-50 rounded-md p-3"
              >
                <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0 text-green-600" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence Trail */}
      {(data.bi_verdict || data.ojk_verdict) && (
        <div className="mt-4 pt-4 border-t border-slate-200">
          <h4 className="font-medium text-slate-900 mb-2 flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Evidence Trail
          </h4>
          <div className="space-y-2">
            {data.bi_verdict?.evidence.map((ev, i) => (
              <EvidenceItem key={`bi-${i}`} evidence={ev} source="BI" />
            ))}
            {data.ojk_verdict?.evidence.map((ev, i) => (
              <EvidenceItem key={`ojk-${i}`} evidence={ev} source="OJK" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AgentVerdictCard({
  title,
  verdict,
}: {
  title: string;
  verdict: NonNullable<AuditResponse["bi_verdict"]>;
}) {
  const statusInfo = statusConfig[verdict.status as keyof typeof statusConfig];
  const StatusIcon = statusInfo.icon;

  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-700">{title}</span>
        <div className={cn("flex items-center gap-1", statusInfo.color)}>
          <StatusIcon className="h-4 w-4" />
          <span className="text-sm">{statusInfo.label}</span>
        </div>
      </div>
      <div className="text-sm text-slate-500">
        Confidence: {(verdict.confidence * 100).toFixed(0)}%
      </div>
      {verdict.violations.length > 0 && (
        <div className="mt-2 text-sm text-red-600">
          {verdict.violations.length} pelanggaran
        </div>
      )}
    </div>
  );
}

function EvidenceItem({
  evidence,
  source,
}: {
  evidence: { regulation: string; article: string; article_text: string; relevance_score: number };
  source: string;
}) {
  return (
    <div className="rounded-md bg-white border border-slate-200 p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-slate-900">
          {evidence.regulation} - {evidence.article}
        </span>
        <span
          className={cn(
            "text-xs px-2 py-0.5 rounded-full",
            source === "BI" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"
          )}
        >
          {source}
        </span>
      </div>
      <p className="text-sm text-slate-600 line-clamp-2">{evidence.article_text}</p>
      <div className="mt-1 text-xs text-slate-400">
        Relevance: {(evidence.relevance_score * 100).toFixed(0)}%
      </div>
    </div>
  );
}