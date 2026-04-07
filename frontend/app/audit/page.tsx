"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { FileText, Keyboard, RotateCcw, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { analyzeSop, type AuditResponse } from "@/lib/api";
import { AuditForm } from "@/components/audit/AuditForm";
import { ResultCard } from "@/components/audit/ResultCard";
import { FileUploadZone } from "@/components/audit/FileUploadZone";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type InputMode = "text" | "upload";

export default function AuditPage() {
  const [mode, setMode] = useState<InputMode>("text");
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [prefilledClause, setPrefilledClause] = useState<string>("");

  const mutation = useMutation({
    mutationFn: analyzeSop,
    onSuccess: (data) => {
      setResult(data);
      toast.success("Audit selesai", {
        description: `Status: ${data.final_status} · ${data.latency_ms.toFixed(0)}ms`,
      });
    },
    onError: (err) => {
      toast.error("Audit gagal", {
        description: err instanceof Error ? err.message : "Terjadi kesalahan.",
      });
    },
  });

  const handleClauseSelect = (clause: string) => {
    setPrefilledClause(clause);
    setMode("text");
    toast.info("Klausa dipilih", {
      description: "Periksa dan edit klausa di form, lalu klik Jalankan Audit.",
    });
  };

  const handleReset = () => {
    setResult(null);
    setPrefilledClause("");
    mutation.reset();
  };

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
        {result && (
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
                    onSubmit={(data) => mutation.mutate(data)}
                    isPending={mutation.isPending}
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
                      Upload file PDF, TXT, atau MD. Sistem akan mengekstrak teks dan menampilkan
                      daftar klausa yang dapat dipilih untuk diaudit.
                    </p>
                  </div>
                  <FileUploadZone
                    onClauseSelect={handleClauseSelect}
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
            {mutation.isPending && (
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

            {mutation.isError && !mutation.isPending && (
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
                  <p className="text-sm text-red-600 mt-1">
                    {mutation.error instanceof Error
                      ? mutation.error.message
                      : "Terjadi kesalahan saat memproses audit."}
                  </p>
                </div>
                <button
                  onClick={() => mutation.reset()}
                  className="text-sm text-red-600 underline underline-offset-2"
                >
                  Coba lagi
                </button>
              </motion.div>
            )}

            {result && !mutation.isPending && (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <ResultCard data={result} />
              </motion.div>
            )}

            {!result && !mutation.isPending && !mutation.isError && (
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
