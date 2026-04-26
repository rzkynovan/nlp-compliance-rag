"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { format } from "date-fns";
import { id } from "date-fns/locale";
import {
  Clock, FileText, CheckCircle2, XCircle, AlertTriangle,
  HelpCircle, ChevronDown, ChevronUp, Search, Filter,
  MessageSquare, Ban, BarChart3, Zap, ShieldCheck, ShieldAlert,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getAuditHistory } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { ResultCard } from "@/components/audit/ResultCard";
import type { AuditResponse } from "@/lib/api/client";

// ── Type ──────────────────────────────────────────────────────────────
type AuditHistory = AuditResponse & {
  timestamp: string;
};

// ── Status config (all 6 + special) ──────────────────────────────────
const statusConfig: Record<string, {
  label: string;
  icon: React.ElementType;
  color: string;
  badgeClass: string;
}> = {
  COMPLIANT:          { label: "Patuh",          icon: CheckCircle2,  color: "text-emerald-600", badgeClass: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  NON_COMPLIANT:      { label: "Tidak Patuh",    icon: XCircle,       color: "text-red-600",     badgeClass: "bg-red-100 text-red-700 border-red-200" },
  PARTIALLY_COMPLIANT:{ label: "Sebagian Patuh", icon: AlertTriangle, color: "text-amber-600",   badgeClass: "bg-amber-100 text-amber-700 border-amber-200" },
  NEEDS_REVIEW:       { label: "Perlu Review",   icon: AlertTriangle, color: "text-amber-600",   badgeClass: "bg-amber-100 text-amber-700 border-amber-200" },
  NOT_ADDRESSED:      { label: "Tidak Diatur",   icon: HelpCircle,    color: "text-slate-500",   badgeClass: "bg-slate-100 text-slate-600 border-slate-200" },
  UNCLEAR:            { label: "Tidak Jelas",    icon: HelpCircle,    color: "text-slate-500",   badgeClass: "bg-slate-100 text-slate-600 border-slate-200" },
  greeting:           { label: "Sapaan",         icon: MessageSquare, color: "text-teal-600",    badgeClass: "bg-teal-100 text-teal-700 border-teal-200" },
  out_of_scope:       { label: "Di Luar Scope",  icon: Ban,           color: "text-rose-600",    badgeClass: "bg-rose-100 text-rose-700 border-rose-200" },
  noise_filtered:     { label: "Header/Noise",   icon: FileText,      color: "text-slate-400",   badgeClass: "bg-slate-100 text-slate-500 border-slate-200" },
};

const ALL_FILTERS = ["Semua", "COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT", "NEEDS_REVIEW", "NOT_ADDRESSED", "UNCLEAR"];

function getEffectiveStatus(item: AuditHistory): string {
  if (item.analysis_mode === "greeting") return "greeting";
  if (item.analysis_mode === "out_of_scope") return "out_of_scope";
  if (item.analysis_mode === "noise_filtered") return "noise_filtered";
  return item.final_status;
}

// ── Agent Pill — ringkasan verdict agent di card ──────────────────────
function AgentPill({
  label,
  status,
  confidence,
  violations,
}: {
  label: "BI" | "OJK";
  status: string;
  confidence: number;
  violations: number;
}) {
  const isBI = label === "BI";
  const isCompliant   = status === "COMPLIANT";
  const isNonCompliant= status === "NON_COMPLIANT";
  const isPartial     = ["PARTIALLY_COMPLIANT", "NEEDS_REVIEW"].includes(status);

  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full border",
      isBI
        ? "bg-blue-50 border-blue-200 text-blue-700"
        : "bg-violet-50 border-violet-200 text-violet-700"
    )}>
      <span className={cn(
        "font-bold",
        isBI ? "text-blue-800" : "text-violet-800"
      )}>{label}</span>
      <span className="opacity-60">·</span>
      {isCompliant    && <ShieldCheck className="h-3 w-3 text-emerald-500" />}
      {isNonCompliant && <ShieldAlert className="h-3 w-3 text-red-500" />}
      {isPartial      && <AlertTriangle className="h-3 w-3 text-amber-500" />}
      {!isCompliant && !isNonCompliant && !isPartial && <HelpCircle className="h-3 w-3 opacity-40" />}
      <span className={cn(
        isCompliant    ? "text-emerald-700" :
        isNonCompliant ? "text-red-700" :
        isPartial      ? "text-amber-700" : "text-slate-500"
      )}>
        {isCompliant ? "Patuh" : isNonCompliant ? "Tidak Patuh" : isPartial ? "Sebagian" : "—"}
      </span>
      <span className="opacity-40">·</span>
      <span className="opacity-70">{(confidence * 100).toFixed(0)}%</span>
      {violations > 0 && (
        <>
          <span className="opacity-40">·</span>
          <span className="text-red-600 font-semibold">{violations}⚠</span>
        </>
      )}
    </span>
  );
}

// ── Summary stat cards ────────────────────────────────────────────────
function SummaryBar({ history }: { history: AuditHistory[] }) {
  const stats = useMemo(() => {
    const compliant   = history.filter(h => h.final_status === "COMPLIANT").length;
    const nonCompliant = history.filter(h => h.final_status === "NON_COMPLIANT").length;
    const partial     = history.filter(h => ["PARTIALLY_COMPLIANT", "NEEDS_REVIEW"].includes(h.final_status)).length;
    const avgLatency  = history.length > 0
      ? (history.reduce((acc, h) => acc + (h.latency_ms || 0), 0) / history.length).toFixed(0)
      : "0";
    return { compliant, nonCompliant, partial, avgLatency, total: history.length };
  }, [history]);

  const complianceRate = stats.total > 0
    ? ((stats.compliant / stats.total) * 100).toFixed(0)
    : "0";

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: "Total Audit",       value: stats.total,       icon: FileText,    color: "text-slate-600",   bg: "bg-slate-100" },
        { label: "Patuh",             value: stats.compliant,   icon: CheckCircle2,color: "text-emerald-600", bg: "bg-emerald-100" },
        { label: "Tidak Patuh",       value: stats.nonCompliant,icon: XCircle,     color: "text-red-600",     bg: "bg-red-100" },
        { label: "Rata-rata Latency", value: `${stats.avgLatency}ms`, icon: Zap,   color: "text-blue-600",    bg: "bg-blue-100" },
      ].map((s) => (
        <div key={s.label} className="rounded-xl border border-slate-200 bg-white p-4">
          <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center mb-2", s.bg)}>
            <s.icon className={cn("h-4 w-4", s.color)} />
          </div>
          <p className="text-xl font-bold text-slate-900">{s.value}</p>
          <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// ── History card ──────────────────────────────────────────────────────
function HistoryCard({
  item,
  index,
  isExpanded,
  onToggle,
}: {
  item: AuditHistory;
  index: number;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const effectiveStatus = getEffectiveStatus(item);
  const cfg = statusConfig[effectiveStatus] ?? statusConfig.UNCLEAR;
  const StatusIcon = cfg.icon;

  const biViolations    = (item.bi_verdict?.violations  ?? []).length;
  const ojkViolations   = (item.ojk_verdict?.violations ?? []).length;
  const totalViolations = biViolations + ojkViolations;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
    >
      {/* ── Card header — always visible, clickable ── */}
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          "w-full text-left px-5 py-4 transition-colors",
          "hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset",
          isExpanded && "bg-slate-50"
        )}
      >
        <div className="flex items-start gap-4">
          {/* Status icon */}
          <div className={cn("mt-0.5 shrink-0 h-9 w-9 rounded-full flex items-center justify-center",
            effectiveStatus === "COMPLIANT"          ? "bg-emerald-100" :
            effectiveStatus === "NON_COMPLIANT"      ? "bg-red-100" :
            effectiveStatus === "PARTIALLY_COMPLIANT"? "bg-amber-100" :
            effectiveStatus === "NEEDS_REVIEW"       ? "bg-amber-100" :
            effectiveStatus === "greeting"           ? "bg-teal-100" :
            effectiveStatus === "out_of_scope"       ? "bg-rose-100" :
            "bg-slate-100"
          )}>
            <StatusIcon className={cn("h-5 w-5", cfg.color)} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Top row: status badge + timestamp */}
            <div className="flex items-center gap-2 flex-wrap mb-1.5">
              <span className={cn(
                "inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border",
                cfg.badgeClass
              )}>
                {cfg.label}
              </span>
              <span className="text-xs text-slate-400">
                {format(new Date(item.timestamp), "d MMM yyyy, HH:mm", { locale: id })}
              </span>
              {item.from_cache && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                  cache
                </span>
              )}
            </div>

            {/* Clause preview */}
            <p className="text-sm text-slate-700 line-clamp-2 leading-relaxed">
              {item.clause}
            </p>

            {/* Bottom meta row */}
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Clock className="h-3 w-3" />
                {item.latency_ms?.toFixed(0) ?? "—"}ms
              </span>
              <span className="text-xs text-slate-400">
                Confidence: <span className="font-medium text-slate-600">
                  {item.overall_confidence !== undefined
                    ? `${(item.overall_confidence * 100).toFixed(0)}%`
                    : "—"}
                </span>
              </span>
              {totalViolations > 0 && (
                <span className="flex items-center gap-1 text-xs text-red-600 font-medium">
                  <XCircle className="h-3 w-3" />
                  {totalViolations} pelanggaran
                </span>
              )}
            </div>

            {/* Agent verdict summary pills */}
            {(item.bi_verdict || item.ojk_verdict) && (
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {item.bi_verdict && (
                  <AgentPill
                    label="BI"
                    status={item.bi_verdict.status}
                    confidence={item.bi_verdict.confidence}
                    violations={(item.bi_verdict.violations ?? []).length}
                  />
                )}
                {item.ojk_verdict && (
                  <AgentPill
                    label="OJK"
                    status={item.ojk_verdict.status}
                    confidence={item.ojk_verdict.confidence}
                    violations={(item.ojk_verdict.violations ?? []).length}
                  />
                )}
              </div>
            )}
          </div>

          {/* Expand chevron */}
          <div className="shrink-0 mt-1">
            {isExpanded
              ? <ChevronUp className="h-4 w-4 text-slate-400" />
              : <ChevronDown className="h-4 w-4 text-slate-400" />}
          </div>
        </div>
      </button>

      {/* ── Expanded detail ── */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden border-t border-slate-100"
          >
            <div className="p-5">
              <ResultCard data={item} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Export helpers ────────────────────────────────────────────────────
function exportJSON(items: AuditHistory[]) {
  const payload = {
    exported_at: new Date().toISOString(),
    total: items.length,
    results: items.map(h => ({
      request_id:         h.request_id,
      timestamp:          h.timestamp,
      clause:             h.clause,
      final_status:       h.final_status,
      overall_confidence: h.overall_confidence,
      risk_score:         h.risk_score,
      latency_ms:         h.latency_ms,
      analysis_mode:      h.analysis_mode,
      query_type:         h.query_type,
      retrieval_mode:     h.retrieval_mode,
      from_cache:         h.from_cache,
      summary:            h.summary,
      bi_verdict:         h.bi_verdict,
      ojk_verdict:        h.ojk_verdict,
      violations:         h.violations,
      recommendations:    h.recommendations,
    })),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit_results_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCSV(items: AuditHistory[]) {
  const headers = [
    "request_id", "timestamp", "final_status", "overall_confidence",
    "risk_score", "latency_ms", "query_type", "retrieval_mode", "from_cache",
    "bi_status", "bi_confidence", "bi_violations_count",
    "ojk_status", "ojk_confidence", "ojk_violations_count",
    "total_violations", "clause_preview",
  ];

  const rows = items.map(h => {
    const biV = (h.bi_verdict?.violations ?? []).length;
    const ojkV = (h.ojk_verdict?.violations ?? []).length;
    const clause = (h.clause ?? "").replace(/"/g, '""').slice(0, 200);
    return [
      h.request_id,
      h.timestamp,
      h.final_status,
      h.overall_confidence?.toFixed(3) ?? "",
      h.risk_score?.toFixed(3) ?? "",
      h.latency_ms?.toFixed(0) ?? "",
      h.query_type ?? "",
      h.retrieval_mode ?? "",
      h.from_cache ? "true" : "false",
      h.bi_verdict?.status ?? "",
      h.bi_verdict?.confidence?.toFixed(3) ?? "",
      biV,
      h.ojk_verdict?.status ?? "",
      h.ojk_verdict?.confidence?.toFixed(3) ?? "",
      ojkV,
      biV + ojkV,
      `"${clause}"`,
    ].join(",");
  });

  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit_results_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Export button ─────────────────────────────────────────────────────
function ExportMenu({ items, label }: { items: AuditHistory[]; label: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          "flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-all",
          "bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300"
        )}
      >
        <Download className="h-3.5 w-3.5" />
        Export {label}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-[140px]">
            <button
              onClick={() => { exportJSON(items); setOpen(false); }}
              className="w-full text-left text-xs px-3 py-2 hover:bg-slate-50 text-slate-700"
            >
              JSON (lengkap)
            </button>
            <button
              onClick={() => { exportCSV(items); setOpen(false); }}
              className="w-full text-left text-xs px-3 py-2 hover:bg-slate-50 text-slate-700"
            >
              CSV (ringkasan)
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────
export default function HistoryPage() {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [activeFilter, setActiveFilter] = useState("Semua");
  const [search, setSearch] = useState("");

  const { data: history, isLoading, error } = useQuery<AuditHistory[]>({
    queryKey: ["audit-history"],
    queryFn: () => getAuditHistory(0, 100) as Promise<AuditHistory[]>,
    refetchInterval: 30_000,
  });

  const filtered = useMemo(() => {
    if (!history) return [];
    let items = history;

    if (activeFilter !== "Semua") {
      items = items.filter(h => {
        const eff = getEffectiveStatus(h);
        return eff === activeFilter;
      });
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(h =>
        h.clause?.toLowerCase().includes(q) ||
        h.request_id?.toLowerCase().includes(q)
      );
    }

    return items;
  }, [history, activeFilter, search]);

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Riwayat Audit</h1>
          <p className="text-sm text-slate-500 mt-1">
            Daftar semua audit yang telah dilakukan · Klik kartu untuk melihat detail
          </p>
        </div>
        {history && history.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <BarChart3 className="h-3.5 w-3.5" />
              {history.length} total
            </div>
            {filtered.length < history.length && filtered.length > 0 && (
              <ExportMenu items={filtered} label={`(${filtered.length} filtered)`} />
            )}
            <ExportMenu items={history} label="semua" />
          </div>
        )}
      </div>

      {/* ── Summary stats ── */}
      {history && history.length > 0 && <SummaryBar history={history} />}

      {/* ── Search + filter ── */}
      {history && history.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Cari klausa atau ID audit..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg bg-white
                placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Filter pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
            <Filter className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            {ALL_FILTERS.map(f => {
              const cfg = f !== "Semua" ? statusConfig[f] : null;
              return (
                <button
                  key={f}
                  onClick={() => setActiveFilter(f)}
                  className={cn(
                    "shrink-0 text-xs px-3 py-1.5 rounded-full border font-medium transition-all",
                    activeFilter === f
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  )}
                >
                  {cfg?.label ?? f}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Content ── */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="rounded-xl border border-slate-200 bg-white p-5 animate-pulse">
              <div className="flex items-start gap-4">
                <div className="h-9 w-9 rounded-full bg-slate-100 shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="flex gap-2">
                    <div className="h-5 w-20 bg-slate-100 rounded-full" />
                    <div className="h-5 w-28 bg-slate-100 rounded-full" />
                  </div>
                  <div className="h-4 bg-slate-100 rounded w-full" />
                  <div className="h-4 bg-slate-100 rounded w-3/4" />
                  <div className="flex gap-3">
                    <div className="h-3 w-16 bg-slate-100 rounded" />
                    <div className="h-3 w-20 bg-slate-100 rounded" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-8 flex flex-col items-center gap-3 text-center">
            <div className="h-12 w-12 rounded-full bg-red-100 flex items-center justify-center">
              <XCircle className="h-6 w-6 text-red-500" />
            </div>
            <div>
              <p className="font-medium text-slate-900">Gagal memuat riwayat</p>
              <p className="text-sm text-slate-500 mt-1">Pastikan backend berjalan dan coba lagi</p>
            </div>
          </CardContent>
        </Card>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {search || activeFilter !== "Semua" ? (
            <p className="text-xs text-slate-400 px-1">
              {filtered.length} hasil{search ? ` untuk "${search}"` : ""}
            </p>
          ) : null}
          {filtered.map((item, idx) => (
            <HistoryCard
              key={item.request_id}
              item={item}
              index={idx}
              isExpanded={expandedIds.has(item.request_id)}
              onToggle={() => toggleExpand(item.request_id)}
            />
          ))}
        </div>
      ) : history && history.length > 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-12 flex flex-col items-center gap-3 text-center">
          <Search className="h-10 w-10 text-slate-300" />
          <div>
            <p className="font-medium text-slate-600">Tidak ada hasil</p>
            <p className="text-sm text-slate-400 mt-1">Coba ubah filter atau kata kunci pencarian</p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-16 flex flex-col items-center gap-3 text-center">
          <div className="h-16 w-16 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm">
            <FileText className="h-7 w-7 text-slate-300" />
          </div>
          <div>
            <p className="font-medium text-slate-600">Belum ada riwayat audit</p>
            <p className="text-sm text-slate-400 mt-1">Audit pertama Anda akan muncul di sini</p>
          </div>
        </div>
      )}
    </div>
  );
}
