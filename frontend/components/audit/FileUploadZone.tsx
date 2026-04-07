"use client";

import { useCallback, useState } from "react";
import {
  Upload,
  FileText,
  X,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ListChecks,
  Square,
  CheckSquare,
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
  onClausesSelect: (clauses: string[]) => void;
  apiUrl: string;
}

export function FileUploadZone({ onClausesSelect, apiUrl }: FileUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = useCallback(async (selectedFile: File) => {
    setError(null);
    setUploadResult(null);
    setSelectedIndices(new Set());
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
    setSelectedIndices(new Set());
    setError(null);
  };

  const toggleIndex = (idx: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    if (!uploadResult) return;
    if (selectedIndices.size === uploadResult.clauses.length) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(uploadResult.clauses.map((_, i) => i)));
    }
  };

  const handleAudit = () => {
    if (selectedIndices.size === 0 || !uploadResult) return;
    const clauses = Array.from(selectedIndices).sort((a, b) => a - b).map((i) => uploadResult.clauses[i]);
    onClausesSelect(clauses);
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
  const allSelected = uploadResult!.clauses.length > 0 &&
    selectedIndices.size === uploadResult!.clauses.length;

  return (
    <div className="space-y-3">
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

      {/* Selection controls */}
      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-slate-500">
          {selectedIndices.size === 0
            ? "Pilih satu atau lebih klausa untuk diaudit"
            : `${selectedIndices.size} klausa dipilih`}
        </p>
        <button
          type="button"
          onClick={toggleAll}
          className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
        >
          {allSelected ? (
            <><CheckSquare className="h-3.5 w-3.5" /> Hapus Semua</>
          ) : (
            <><Square className="h-3.5 w-3.5" /> Pilih Semua</>
          )}
        </button>
      </div>

      {/* Clause list */}
      <div
        className="h-[280px] overflow-y-auto overflow-x-hidden rounded-lg border border-slate-200 bg-white"
        style={{ WebkitOverflowScrolling: "touch" }}
      >
        <div className="p-2 space-y-1">
          {uploadResult!.clauses.map((clause, idx) => {
            const isSelected = selectedIndices.has(idx);
            return (
              <div
                key={idx}
                role="checkbox"
                aria-checked={isSelected}
                tabIndex={0}
                onClick={() => toggleIndex(idx)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") toggleIndex(idx);
                }}
                className={cn(
                  "w-full text-left rounded-md px-3 py-2.5 text-sm transition-all border select-none cursor-pointer",
                  isSelected
                    ? "bg-blue-50 border-blue-300 text-blue-900"
                    : "bg-white border-transparent hover:border-slate-200 hover:bg-slate-50 text-slate-700",
                )}
              >
                <div className="flex items-start gap-2.5">
                  {/* Checkbox */}
                  <div className={cn(
                    "mt-0.5 shrink-0 h-4 w-4 rounded border-2 flex items-center justify-center transition-colors",
                    isSelected
                      ? "bg-blue-600 border-blue-600"
                      : "border-slate-300 bg-white",
                  )}>
                    {isSelected && <CheckCircle2 className="h-3 w-3 text-white" />}
                  </div>
                  {/* Number */}
                  <span className={cn(
                    "shrink-0 text-xs font-mono mt-0.5",
                    isSelected ? "text-blue-500" : "text-slate-300",
                  )}>
                    {String(idx + 1).padStart(2, "0")}
                  </span>
                  {/* Text */}
                  <span className="line-clamp-3 leading-relaxed flex-1">{clause}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action button */}
      <Button
        type="button"
        onClick={handleAudit}
        disabled={selectedIndices.size === 0}
        className="w-full"
      >
        <ListChecks className="h-4 w-4 mr-1.5" />
        {selectedIndices.size === 0
          ? "Pilih Klausa untuk Diaudit"
          : selectedIndices.size === 1
            ? `Audit 1 Klausa`
            : `Audit ${selectedIndices.size} Klausa Sekaligus`}
      </Button>
    </div>
  );
}
