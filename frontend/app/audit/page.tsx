"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  FileText, Keyboard, RotateCcw, Info, ChevronDown, ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { analyzeSop, type AuditResponse } from "@/lib/api";
import { AuditForm } from "@/components/audit/AuditForm";
import { ResultCard } from "@/components/audit/ResultCard";
import { FileUploadZone } from "@/components/audit/FileUploadZone";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type InputMode = "text" | "upload";

interface BatchProgress {
  current: number;
  total: number;
}

export default function AuditPage() {
  const [mode, setMode] = useState<InputMode>("text");
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [batchResults, setBatchResults] = useState<AuditResponse[]>([]);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [prefilledClause, setPrefilledClause] = useState<string>("");
  const [singlePending, setSinglePending] = useState(false);
  const [singleError, setSingleError] = useState<Error | null>(null);
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set([0]));

  const isBatchMode = batchResults.length > 0;

  // ── Single clause audit (from text form) ──────────────────────────
  const handleSingleSubmit = async (data: { clause: string; context?: string; top_k?: number; regulator?: "all" | "BI" | "OJK" }) => {
    setSinglePending(true);
    setSingleError(null);
    setResult(null);
    setBatchResults([]);
    try {
      const res = await analyzeSop(data);
      setResult(res);
      toast.success("Audit selesai", {
        description: `Status: ${res.final_status} · ${res.latency_ms.toFixed(0)}ms`,
      });
    } catch (e) {
      const err = e instanceof Error ? e : new Error("Terjadi kesalahan.");
      setSingleError(err);
      toast.error("Audit gagal", { description: err.message });
    } finally {
      setSinglePending(false);
    }
  };

  // ── Batch audit (from file upload multi-select) ────────────────────
  const handleClausesSelect = async (clauses: string[]) => {
    if (clauses.length === 1) {
      // Single clause: switch to text tab + prefill
      setPrefilledClause(clauses[0]);
      setMode("text");
      toast.info("Klausa dipilih", {
        description: "Periksa dan edit klausa di form, lalu klik Jalankan Audit.",
      });
      return;
    }

    // Multiple clauses: run batch
    setMode("text"); // switch away from upload tab during processing
    setBatchResults([]);
    setResult(null);
    setSingleError(null);
    setIsBatchRunning(true);
    setExpandedResults(new Set([0]));

    const results: AuditResponse[] = [];

    for (let i = 0; i < clauses.length; i++) {
      setBatchProgress({ current: i + 1, total: clauses.length });
      try {
        const res = await analyzeSop({ clause: clauses[i] });
        results.push(res);
        setBatchResults([...results]);
      } catch (e) {
        toast.error(`Klausa #${i + 1} gagal diaudit`, {
          description: e instanceof Error ? e.message : "Terjadi kesalahan.",
        });
        // Push a placeholder so indices stay consistent
        results.push({
          request_id: `error-${i}`,
          timestamp: new Date().toISOString(),
          clause: clauses[i],
          bi_verdict: null,
          ojk_verdict: null,
          final_status: "UNCLEAR",
          overall_confidence: 0,
          risk_score: 0,
          violations: [],
          recommendations: [],
          latency_ms: 0,
        });
        setBatchResults([...results]);
      }
    }

    setIsBatchRunning(false);
    setBatchProgress(null);
    toast.success(`Batch audit selesai`, {
      description: `${results.length} klausa diproses`,
    });
  };

  const handleReset = () => {
    setResult(null);
    setBatchResults([]);
    setBatchProgress(null);
    setIsBatchRunning(false);
    setPrefilledClause("");
    setSingleError(null);
    setSinglePending(false);
  };

  const toggleExpand = (idx: number) => {
    setExpandedResults((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const hasResults = result !== null || batchResults.length > 0;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Audit Kepatuhan</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Analisis klausa SOP terhadap regulasi Bank Indonesia dan OJK menggunakan Multi-Agent RAG
          </p>
        </div>
        {(hasResults || isBatchRunning) && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* ── Left: Input panel ── */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          {/* Input mode tabs */}
          <div className="flex border-b border-slate-100">
            <TabButton
              active={mode === "text"}
              onClick={() => setMode("text")}
              icon={<Keyboard className="h-3.5 w-3.5" />}
              label="Input Teks"
            />
            <TabButton
              active={mode === "upload"}
              onClick={() => setMode("upload")}
              icon={<FileText className="h-3.5 w-3.5" />}
              label="Upload Dokumen"
            />
          </div>

          <div className="p-6">
            <AnimatePresence mode="wait">
              {mode === "text" ? (
                <motion.div
                  key="text"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.18 }}
                >
                  <p className="text-xs text-slate-400 mb-4">
                    Ketik atau tempel klausa SOP yang ingin diaudit.
                  </p>
                  <AuditForm
                    key={prefilledClause}
                    onSubmit={handleSingleSubmit}
                    isPending={singlePending}
                    defaultValues={
                      prefilledClause ? { clause: prefilledClause } : undefined
                    }
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  <div className="flex items-start gap-2 rounded-lg bg-blue-50 border border-blue-100 p-3 mb-4">
                    <Info className="h-3.5 w-3.5 text-blue-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-blue-700">
                      Upload file PDF, TXT, atau MD. Pilih satu atau lebih klausa, lalu klik
                      <strong> Audit</strong>. Batch audit akan memproses semua klausa terpilih secara otomatis.
                    </p>
                  </div>
                  <FileUploadZone
                    onClausesSelect={handleClausesSelect}
                    apiUrl={API_URL}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* ── Right: Results panel ── */}
        <div>
          <AnimatePresence mode="wait">
            {/* ── Batch running ── */}
            {isBatchRunning && (
              <motion.div
                key="batch-loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                {/* Progress bar */}
                <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-medium text-slate-700">
                      Memproses batch audit...
                    </p>
                    <span className="text-sm font-mono text-slate-500">
                      {batchProgress?.current ?? 0} / {batchProgress?.total ?? 0}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <motion.div
                      className="h-full bg-blue-600 rounded-full"
                      animate={{
                        width: batchProgress
                          ? `${(batchProgress.current / batchProgress.total) * 100}%`
                          : "0%",
                      }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Mengaudit klausa #{batchProgress?.current}...
                  </p>
                </div>

                {/* Partial results */}
                {batchResults.length > 0 && (
                  <BatchResultList
                    results={batchResults}
                    expandedResults={expandedResults}
                    onToggle={toggleExpand}
                  />
                )}
              </motion.div>
            )}

            {/* ── Single loading ── */}
            {singlePending && !isBatchRunning && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="rounded-xl border border-slate-200 bg-white shadow-sm p-10 flex flex-col items-center justify-center gap-3 text-center"
              >
                <div className="relative h-12 w-12">
                  <div className="absolute inset-0 rounded-full border-4 border-slate-200" />
                  <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-700">Menganalisis klausa...</p>
                  <p className="text-xs text-slate-400 mt-0.5">Multi-agent RAG sedang bekerja</p>
                </div>
              </motion.div>
            )}

            {/* ── Single error ── */}
            {singleError && !singlePending && !isBatchMode && (
              <motion.div
                key="error"
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="rounded-xl border border-red-200 bg-red-50 p-8 flex flex-col items-center gap-3 text-center"
              >
                <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-red-500 text-xl">!</span>
                </div>
                <div>
                  <p className="font-medium text-red-800">Audit gagal</p>
                  <p className="text-sm text-red-600 mt-1">{singleError.message}</p>
                </div>
                <button
                  onClick={handleReset}
                  className="text-sm text-red-600 underline underline-offset-2"
                >
                  Coba lagi
                </button>
              </motion.div>
            )}

            {/* ── Batch results (complete) ── */}
            {isBatchMode && !isBatchRunning && (
              <motion.div
                key="batch-results"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <BatchResultList
                  results={batchResults}
                  expandedResults={expandedResults}
                  onToggle={toggleExpand}
                />
              </motion.div>
            )}

            {/* ── Single result ── */}
            {result && !singlePending && !isBatchMode && (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <ResultCard data={result} />
              </motion.div>
            )}

            {/* ── Empty state ── */}
            {!hasResults && !singlePending && !singleError && !isBatchRunning && (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-12 flex flex-col items-center justify-center gap-3 text-center"
              >
                <div className="h-14 w-14 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                  <FileText className="h-6 w-6 text-slate-300" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Hasil audit akan muncul di sini</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Isi form atau upload dokumen, lalu klik Jalankan Audit
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

// ── Batch result list ────────────────────────────────────────────────
function BatchResultList({
  results,
  expandedResults,
  onToggle,
}: {
  results: AuditResponse[];
  expandedResults: Set<number>;
  onToggle: (idx: number) => void;
}) {
  const statusColors: Record<string, string> = {
    COMPLIANT: "text-green-600 bg-green-50 border-green-200",
    NON_COMPLIANT: "text-red-600 bg-red-50 border-red-200",
    PARTIALLY_COMPLIANT: "text-amber-600 bg-amber-50 border-amber-200",
    NEEDS_REVIEW: "text-amber-600 bg-amber-50 border-amber-200",
    NOT_ADDRESSED: "text-slate-500 bg-slate-50 border-slate-200",
    UNCLEAR: "text-slate-500 bg-slate-50 border-slate-200",
  };

  const statusLabel: Record<string, string> = {
    COMPLIANT: "Patuh",
    NON_COMPLIANT: "Tidak Patuh",
    PARTIALLY_COMPLIANT: "Sebagian Patuh",
    NEEDS_REVIEW: "Perlu Review",
    NOT_ADDRESSED: "Tidak Diatur",
    UNCLEAR: "Tidak Jelas",
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 font-medium px-1">
        {results.length} klausa diaudit
      </p>
      {results.map((r, idx) => {
        const isExpanded = expandedResults.has(idx);
        const colorClass = statusColors[r.final_status] ?? statusColors.UNCLEAR;
        const label = statusLabel[r.final_status] ?? "Tidak Jelas";

        return (
          <div key={r.request_id} className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            {/* Collapsed header */}
            <button
              type="button"
              onClick={() => onToggle(idx)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs font-mono text-slate-400 shrink-0">
                  #{String(idx + 1).padStart(2, "0")}
                </span>
                <p className="text-sm text-slate-700 truncate">
                  {r.clause.slice(0, 80)}{r.clause.length > 80 ? "…" : ""}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-3">
                <span className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded-full border",
                  colorClass,
                )}>
                  {label}
                </span>
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4 text-slate-400" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-slate-400" />
                )}
              </div>
            </button>

            {/* Expanded: full ResultCard */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22, ease: "easeInOut" }}
                  className="overflow-hidden border-t border-slate-100"
                >
                  <div className="p-4">
                    <ResultCard data={r} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2",
        active
          ? "border-blue-600 text-blue-700 bg-blue-50/60"
          : "border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50",
      )}
    >
      {icon}
      {label}
    </button>
  );
}
