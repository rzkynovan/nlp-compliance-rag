"use client";

import { useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  X,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface UploadResult {
  filename: string;
  file_size_kb: number;
  text: string;
  clauses: string[];
  clause_count: number;
}

interface FileUploadZoneProps {
  onClauseSelect: (clause: string) => void;
  apiUrl: string;
}

export function FileUploadZone({ onClauseSelect, apiUrl }: FileUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = useCallback(async (selectedFile: File) => {
    setError(null);
    setUploadResult(null);
    setSelectedIndex(null);
    setFile(selectedFile);
    setIsUploading(true);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(`${apiUrl}/audit/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload gagal (${res.status})`);
      }

      const data: UploadResult = await res.json();
      setUploadResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload gagal. Coba lagi.");
      setFile(null);
    } finally {
      setIsUploading(false);
    }
  }, [apiUrl]);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped) handleUpload(dropped);
    },
    [handleUpload],
  );

  const onFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) handleUpload(selected);
      e.target.value = "";
    },
    [handleUpload],
  );

  const reset = () => {
    setFile(null);
    setUploadResult(null);
    setSelectedIndex(null);
    setError(null);
  };

  const handleSelect = (idx: number) => {
    setSelectedIndex(idx);
  };

  const handleAudit = () => {
    if (selectedIndex !== null && uploadResult) {
      onClauseSelect(uploadResult.clauses[selectedIndex]);
    }
  };

  // ── Empty / drag-drop state ────────────────────────────────────────
  if (!uploadResult && !isUploading) {
    return (
      <div className="space-y-3">
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={onDrop}
          className={cn(
            "relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-all duration-200",
            isDragOver
              ? "border-blue-500 bg-blue-50"
              : "border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white",
          )}
        >
          <div className={cn(
            "flex h-14 w-14 items-center justify-center rounded-full transition-colors",
            isDragOver ? "bg-blue-100" : "bg-white border border-slate-200",
          )}>
            <Upload className={cn("h-6 w-6", isDragOver ? "text-blue-500" : "text-slate-400")} />
          </div>

          <div>
            <p className="text-sm font-medium text-slate-700">
              {isDragOver ? "Lepaskan file di sini" : "Seret & lepaskan dokumen"}
            </p>
            <p className="mt-0.5 text-xs text-slate-400">PDF, TXT, MD · Maks. 10 MB</p>
          </div>

          <label className="cursor-pointer">
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={onFileInput}
              className="sr-only"
            />
            <Button type="button" variant="outline" size="sm" className="pointer-events-none">
              Pilih File
            </Button>
          </label>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }

  // ── Loading state ──────────────────────────────────────────────────
  if (isUploading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-10 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <div>
          <p className="text-sm font-medium text-slate-700">Membaca dokumen...</p>
          <p className="text-xs text-slate-400 mt-0.5">{file?.name}</p>
        </div>
      </div>
    );
  }

  // ── Result: clause list ────────────────────────────────────────────
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="result"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-4"
      >
        {/* File info bar */}
        <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <FileText className="h-4 w-4 text-blue-500 shrink-0" />
            <div>
              <p className="text-sm font-medium text-slate-800 leading-none">
                {uploadResult!.filename}
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                {uploadResult!.file_size_kb} KB · {uploadResult!.clause_count} klausa ditemukan
              </p>
            </div>
          </div>
          <button
            onClick={reset}
            className="rounded-md p-1 hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
            title="Upload ulang"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Instruction */}
        <p className="text-xs text-slate-500 px-1">
          Pilih klausa yang ingin diaudit, lalu klik <strong>Audit Klausa</strong>.
        </p>

        {/* Clause list */}
        <div className="h-72 overflow-y-auto rounded-lg border border-slate-200">
          <div className="p-2 space-y-1.5">
            {uploadResult!.clauses.map((clause, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelect(idx)}
                className={cn(
                  "w-full text-left rounded-md px-3 py-2.5 text-sm transition-all border",
                  selectedIndex === idx
                    ? "bg-blue-50 border-blue-300 text-blue-900"
                    : "bg-white border-transparent hover:border-slate-200 hover:bg-slate-50 text-slate-700",
                )}
              >
                <div className="flex items-start gap-2">
                  <span className={cn(
                    "mt-0.5 shrink-0 text-xs font-mono",
                    selectedIndex === idx ? "text-blue-400" : "text-slate-300",
                  )}>
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  <span className="line-clamp-3 leading-relaxed">{clause}</span>
                  {selectedIndex === idx && (
                    <CheckCircle2 className="h-4 w-4 text-blue-500 shrink-0 mt-0.5 ml-auto" />
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Action */}
        <Button
          type="button"
          onClick={handleAudit}
          disabled={selectedIndex === null}
          className="w-full"
        >
          <ChevronRight className="h-4 w-4 mr-1" />
          Audit Klausa {selectedIndex !== null ? `#${selectedIndex + 1}` : ""}
        </Button>
      </motion.div>
    </AnimatePresence>
  );
}
