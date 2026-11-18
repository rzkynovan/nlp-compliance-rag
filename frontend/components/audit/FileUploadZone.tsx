"use client";

import { useRef, useState } from "react";
import { AlertCircle, FileText, Play, UploadCloud, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { errorMessage, uploadDocument, type UploadDocumentResult } from "@/lib/api";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { cn } from "@/lib/utils";

const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md"];
const MAX_FILE_SIZE = 10 * 1024 * 1024;

interface FileUploadZoneProps {
  onClausesSelect: (clauses: string[], useCache: boolean) => void;
  disabled?: boolean;
}

function CacheSwitch({
  id,
  label,
  hint,
  checked,
  onCheckedChange,
}: {
  id: string;
  label: string;
  hint: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start gap-3">
      <Switch id={id} size="sm" checked={checked} onCheckedChange={onCheckedChange} className="mt-0.5" />
      <Label htmlFor={id} className="flex flex-col items-start gap-0.5 font-normal">
        <span>{label}</span>
        <span className="text-xs text-muted-foreground">{hint}</span>
      </Label>
    </div>
  );
}

export function FileUploadZone({ onClausesSelect, disabled }: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploadingName, setUploadingName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadDocumentResult | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [useLlamaCache, setUseLlamaCache] = useState(true);
  const [useAuditCache, setUseAuditCache] = useState(() => useSettingsStore.getState().enableCache);

  async function handleFile(file: File) {
    const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError(`Format file tidak didukung (${extension}). Gunakan: ${ACCEPTED_EXTENSIONS.join(", ")}`);
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("Ukuran file melebihi 10 MB.");
      return;
    }

    setError(null);
    setUploadingName(file.name);
    try {
      // Cache LlamaParse hanya relevan untuk PDF.
      const data = await uploadDocument(file, extension === ".pdf" ? useLlamaCache : undefined);
      setResult(data);
      setSelected(new Set());
    } catch (err) {
      setError(errorMessage(err, "Upload gagal"));
    } finally {
      setUploadingName(null);
    }
  }

  function resetUpload() {
    setResult(null);
    setSelected(new Set());
    setError(null);
  }

  function toggleClause(index: number, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(index);
      else next.delete(index);
      return next;
    });
  }

  function submitSelection() {
    if (!result || selected.size === 0) return;
    const clauses = [...selected].sort((a, b) => a - b).map((index) => result.clauses[index]);
    onClausesSelect(clauses, useAuditCache);
  }

  if (uploadingName) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-6 py-12 text-center">
        <Spinner className="size-6 text-primary" />
        <div>
          <p className="text-sm font-medium">Membaca dokumen...</p>
          <p className="mt-0.5 max-w-xs truncate text-xs text-muted-foreground">{uploadingName}</p>
        </div>
      </div>
    );
  }

  if (result) {
    const count = selected.size;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <FileText className="size-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{result.filename}</p>
            <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
              <span>{result.file_size_kb.toFixed(1)} KB</span>
              <span>·</span>
              <span>{result.clause_count} klausa ditemukan</span>
              {result.parsed_from_cache && <Badge variant="secondary">cache</Badge>}
            </p>
          </div>
          <Button variant="ghost" size="icon-sm" aria-label="Upload ulang" title="Upload ulang" onClick={resetUpload}>
            <X />
          </Button>
        </div>

        {result.clauses.length === 0 ? (
          <Alert>
            <AlertCircle />
            <AlertTitle>Tidak ada klausa yang terdeteksi</AlertTitle>
            <AlertDescription>Coba dokumen lain atau tempel klausa langsung di tab Input Teks.</AlertDescription>
          </Alert>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-muted-foreground">
                {count === 0 ? "Pilih satu atau lebih klausa untuk diaudit" : `${count} klausa dipilih`}
              </p>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelected(new Set(result.clauses.map((_, index) => index)))}
                >
                  Pilih Semua
                </Button>
                <Button variant="ghost" size="sm" disabled={count === 0} onClick={() => setSelected(new Set())}>
                  Hapus Semua
                </Button>
              </div>
            </div>

            <ScrollArea className="h-[280px] rounded-lg border">
              <ul className="divide-y">
                {result.clauses.map((clause, index) => {
                  const checked = selected.has(index);
                  return (
                    <li key={index}>
                      <label
                        className={cn(
                          "flex cursor-pointer items-start gap-3 px-3 py-2.5 text-sm transition-colors hover:bg-muted/50",
                          checked && "bg-primary/5",
                        )}
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={(value) => toggleClause(index, value === true)}
                          className="mt-0.5"
                        />
                        <span className="font-mono text-xs leading-5 text-muted-foreground tabular-nums">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <span className="line-clamp-3 min-w-0 flex-1 leading-5">{clause}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </ScrollArea>

            <CacheSwitch
              id="audit-cache"
              label="Gunakan cache hasil audit"
              hint="Nonaktifkan untuk paksa re-run."
              checked={useAuditCache}
              onCheckedChange={setUseAuditCache}
            />

            <Button size="lg" className="w-full" disabled={count === 0 || disabled} onClick={submitSelection}>
              <Play data-icon="inline-start" />
              {count === 0
                ? "Pilih Klausa untuk Diaudit"
                : count === 1
                  ? "Audit 1 Klausa"
                  : `Audit ${count} Klausa Sekaligus`}
            </Button>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files[0];
          if (file) void handleFile(file);
        }}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "hover:border-muted-foreground/40",
        )}
      >
        <div className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <UploadCloud className="size-5" />
        </div>
        <div>
          <p className="text-sm font-medium">{dragging ? "Lepaskan file di sini" : "Seret & lepaskan dokumen"}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">PDF, TXT, MD · Maks. 10 MB</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
          Pilih File
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="sr-only"
          tabIndex={-1}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void handleFile(file);
            event.target.value = "";
          }}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Upload gagal</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <CacheSwitch
        id="llama-cache"
        label="Gunakan cache LlamaParse untuk PDF"
        hint="Nonaktifkan untuk paksa re-parse."
        checked={useLlamaCache}
        onCheckedChange={setUseLlamaCache}
      />
      <CacheSwitch
        id="audit-cache-initial"
        label="Gunakan cache hasil audit"
        hint="Nonaktifkan untuk paksa re-run."
        checked={useAuditCache}
        onCheckedChange={setUseAuditCache}
      />
    </div>
  );
}
