"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ChevronDown, FileSearch, FileText, Info, Keyboard, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { AuditForm } from "@/components/audit/AuditForm";
import { FileUploadZone } from "@/components/audit/FileUploadZone";
import { ResultCard } from "@/components/audit/ResultCard";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { analyzeSop, type AuditRequest, type AuditResponse, errorMessage, queryKeys } from "@/lib/api";
import { resultMeta } from "@/lib/compliance";
import { notifyAuditDone } from "@/lib/notify";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { cn, formatLatency } from "@/lib/utils";

type InputMode = "text" | "upload";

interface BatchItem {
  clause: string;
  result?: AuditResponse;
  error?: string;
}

export default function AuditPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<InputMode>("text");
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [singlePending, setSinglePending] = useState(false);
  const [singleError, setSingleError] = useState<string | null>(null);
  const [prefilledClause, setPrefilledClause] = useState("");
  const [batchItems, setBatchItems] = useState<BatchItem[]>([]);
  const [batchTotal, setBatchTotal] = useState(0);
  const [isBatchRunning, setIsBatchRunning] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set([0]));
  // Reset di tengah batch membatalkan sisa antrean lewat nomor run ini.
  const runIdRef = useRef(0);

  const isBatchMode = batchItems.length > 0 || isBatchRunning;
  const hasResults = result !== null || batchItems.length > 0;

  function refreshHistory() {
    void queryClient.invalidateQueries({ queryKey: queryKeys.audits.all });
    void queryClient.invalidateQueries({ queryKey: queryKeys.usage });
  }

  async function handleSingleSubmit(data: AuditRequest) {
    const runId = ++runIdRef.current;
    setSinglePending(true);
    setSingleError(null);
    setResult(null);
    setBatchItems([]);
    setIsBatchRunning(false);
    try {
      const response = await analyzeSop(data);
      if (runId !== runIdRef.current) return;
      setResult(response);
      notifyAuditDone("Audit selesai", `Status: ${resultMeta(response).label} · ${formatLatency(response.latency_ms)}`);
      refreshHistory();
    } catch (error) {
      if (runId !== runIdRef.current) return;
      const message = errorMessage(error);
      setSingleError(message);
      toast.error("Audit gagal", { description: message });
    } finally {
      if (runId === runIdRef.current) setSinglePending(false);
    }
  }

  async function handleClausesSelect(clauses: string[], useCache: boolean) {
    if (clauses.length === 1) {
      // Satu klausa: isi form agar bisa diperiksa/diedit sebelum diaudit.
      setPrefilledClause(clauses[0]);
      setMode("text");
      toast.info("Klausa dipilih", {
        description: "Periksa dan edit klausa di form, lalu klik Jalankan Audit.",
      });
      return;
    }

    const runId = ++runIdRef.current;
    const { defaultRegulator, defaultTopK } = useSettingsStore.getState();
    setMode("text");
    setResult(null);
    setSingleError(null);
    setSinglePending(false);
    setBatchItems([]);
    setBatchTotal(clauses.length);
    setIsBatchRunning(true);
    setExpanded(new Set([0]));

    const items: BatchItem[] = [];
    for (let i = 0; i < clauses.length; i++) {
      try {
        const response = await analyzeSop({
          clause: clauses[i],
          regulator: defaultRegulator,
          top_k: defaultTopK,
          use_cache: useCache,
        });
        items.push({ clause: clauses[i], result: response });
      } catch (error) {
        const message = errorMessage(error);
        if (runId === runIdRef.current) {
          toast.error(`Klausa #${i + 1} gagal diaudit`, { description: message });
        }
        // Tetap dicatat supaya nomor urut klausa konsisten.
        items.push({ clause: clauses[i], error: message });
      }
      if (runId !== runIdRef.current) return;
      setBatchItems([...items]);
    }

    setIsBatchRunning(false);
    notifyAuditDone("Batch audit selesai", `${items.length} klausa diproses`);
    refreshHistory();
  }

  function handleReset() {
    runIdRef.current++;
    setResult(null);
    setBatchItems([]);
    setBatchTotal(0);
    setIsBatchRunning(false);
    setPrefilledClause("");
    setSingleError(null);
    setSinglePending(false);
  }

  function toggleExpand(index: number, open: boolean) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (open) next.add(index);
      else next.delete(index);
      return next;
    });
  }

  return (
    <>
      <PageHeader
        title="Audit Kepatuhan"
        description="Analisis klausa terhadap regulasi Bank Indonesia dan OJK menggunakan Multi-Agent RAG"
      >
        {(hasResults || isBatchRunning || singleError) && (
          <Button variant="outline" size="sm" onClick={handleReset}>
            <RotateCcw data-icon="inline-start" />
            Reset
          </Button>
        )}
      </PageHeader>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <Card>
          <CardContent>
            <Tabs value={mode} onValueChange={(value) => setMode(value as InputMode)} className="gap-5">
              <TabsList className="w-full">
                <TabsTrigger value="text">
                  <Keyboard />
                  Input Teks
                </TabsTrigger>
                <TabsTrigger value="upload">
                  <FileText />
                  Upload Dokumen
                </TabsTrigger>
              </TabsList>

              <TabsContent value="text" className="flex flex-col gap-4">
                <p className="text-xs text-muted-foreground">Ketik atau tempel klausa yang ingin diaudit.</p>
                <AuditForm
                  key={prefilledClause}
                  onSubmit={handleSingleSubmit}
                  isPending={singlePending || isBatchRunning}
                  defaultValues={prefilledClause ? { clause: prefilledClause } : undefined}
                />
              </TabsContent>

              {/* forceMount: dokumen yang sudah di-upload tidak hilang saat pindah tab */}
              <TabsContent value="upload" forceMount className="flex flex-col gap-4 data-[state=inactive]:hidden">
                <Alert>
                  <Info />
                  <AlertDescription>
                    Upload file PDF, TXT, atau MD. Pilih satu atau lebih klausa, lalu klik <strong>Audit</strong>.
                    Batch audit akan memproses semua klausa terpilih secara otomatis.
                  </AlertDescription>
                </Alert>
                <FileUploadZone onClausesSelect={handleClausesSelect} disabled={isBatchRunning || singlePending} />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <div className="flex min-w-0 flex-col gap-4" aria-live="polite">
          {isBatchRunning && (
            <Card size="sm">
              <CardContent className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <Spinner />
                    Memproses batch audit...
                  </p>
                  <span className="font-mono text-sm text-muted-foreground tabular-nums">
                    {batchItems.length} / {batchTotal}
                  </span>
                </div>
                <Progress value={batchTotal ? (batchItems.length / batchTotal) * 100 : 0} />
                <p className="text-xs text-muted-foreground">
                  Mengaudit klausa #{Math.min(batchItems.length + 1, batchTotal)}...
                </p>
              </CardContent>
            </Card>
          )}

          {isBatchMode && batchItems.length > 0 && (
            <BatchResultList items={batchItems} expanded={expanded} onToggle={toggleExpand} />
          )}

          {singlePending && !isBatchMode && (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
                <Spinner className="size-8 text-primary" />
                <div>
                  <p className="text-sm font-medium">Menganalisis klausa...</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">Multi-agent RAG sedang bekerja</p>
                </div>
              </CardContent>
            </Card>
          )}

          {singleError && !singlePending && !isBatchMode && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertTitle>Audit gagal</AlertTitle>
              <AlertDescription>
                <p>{singleError}</p>
                <Button variant="outline" size="sm" className="mt-2" onClick={handleReset}>
                  Coba lagi
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {result && !singlePending && !isBatchMode && <ResultCard result={result} />}

          {!hasResults && !singlePending && !singleError && !isBatchRunning && (
            <Empty className="border border-dashed">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <FileSearch />
                </EmptyMedia>
                <EmptyTitle>Hasil audit akan muncul di sini</EmptyTitle>
                <EmptyDescription>Isi form atau upload dokumen, lalu klik Jalankan Audit</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </div>
      </div>
    </>
  );
}

function BatchResultList({
  items,
  expanded,
  onToggle,
}: {
  items: BatchItem[];
  expanded: Set<number>;
  onToggle: (index: number, open: boolean) => void;
}) {
  const failed = items.filter((item) => item.error).length;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-muted-foreground">
        {items.length} klausa diaudit{failed > 0 && ` · ${failed} gagal`}
      </p>
      {items.map((item, index) => {
        const open = expanded.has(index);
        return (
          <Collapsible key={index} open={open} onOpenChange={(value) => onToggle(index, value)}>
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg border bg-card px-3 py-2.5 text-left transition-colors outline-none hover:bg-muted/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
                  open && "rounded-b-none border-b-0 bg-muted/40",
                )}
              >
                <span className="font-mono text-xs text-muted-foreground tabular-nums">
                  #{String(index + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm">{item.clause}</span>
                {item.result ? (
                  <StatusBadge meta={resultMeta(item.result)} />
                ) : (
                  <Badge variant="destructive">Gagal</Badge>
                )}
                <ChevronDown
                  className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
                />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="rounded-b-lg border border-t-0 p-3">
              {item.result ? (
                <ResultCard result={item.result} />
              ) : (
                <Alert variant="destructive">
                  <AlertCircle />
                  <AlertTitle>Klausa gagal diaudit</AlertTitle>
                  <AlertDescription>{item.error}</AlertDescription>
                </Alert>
              )}
            </CollapsibleContent>
          </Collapsible>
        );
      })}
    </div>
  );
}
