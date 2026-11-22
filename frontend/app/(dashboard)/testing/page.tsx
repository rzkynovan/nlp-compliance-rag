"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Database, Download, ListChecks, MinusCircle, RefreshCw, Target, XCircle } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { errorMessage, getGoldenDataset, type GoldenDatasetItem, queryKeys } from "@/lib/api";
import { toneClasses, verdictMeta } from "@/lib/compliance";
import { cn, csvCell, downloadFile, formatDateTime } from "@/lib/utils";

const CLAUSE_PREVIEW_LENGTH = 100;

function exportCSV(items: GoldenDatasetItem[]) {
  const headers = [
    "ID",
    "Kategori",
    "Klausa SOP",
    "Kesalahan yang Dirancang",
    "Label Benar",
    "Prediksi Sistem",
    "Benar?",
    "Latency (ms)",
  ];
  const rows = items.map((item) => [
    item.clause_id,
    item.category,
    item.clause,
    item.error_description,
    item.expected_status,
    item.predicted_status ?? "N/A",
    item.is_correct == null ? "N/A" : item.is_correct ? "Ya" : "Tidak",
    item.latency_ms ?? "N/A",
  ]);
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  downloadFile(`﻿${csv}`, "golden_dataset_testing.csv", "text/csv;charset=utf-8;");
}

function ExpandableClause({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > CLAUSE_PREVIEW_LENGTH;

  return (
    <p className="text-sm leading-relaxed">
      {expanded || !isLong ? text : `${text.slice(0, CLAUSE_PREVIEW_LENGTH)}...`}
      {isLong && (
        <Button
          variant="link"
          size="xs"
          className="ml-1 h-auto p-0 align-baseline"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Sembunyikan" : "Lihat lengkap"}
        </Button>
      )}
    </p>
  );
}

function CorrectIcon({ value }: { value: boolean | null | undefined }) {
  if (value == null) return <MinusCircle className="mx-auto size-4.5 text-muted-foreground/50" aria-label="Belum ada prediksi" />;
  return value ? (
    <CheckCircle2 className={cn("mx-auto size-4.5", toneClasses.success.text)} aria-label="Benar" />
  ) : (
    <XCircle className={cn("mx-auto size-4.5", toneClasses.danger.text)} aria-label="Salah" />
  );
}

export default function TestingPage() {
  const { data, isPending, isFetching, error, refetch } = useQuery({
    queryKey: queryKeys.evaluation.goldenDataset,
    queryFn: getGoldenDataset,
    staleTime: 60_000,
  });

  return (
    <>
      <PageHeader
        title="Dokumen Testing"
        description={`Golden dataset dummy NusantaraPay — ${data?.total ?? 12} klausul dengan ground truth dan prediksi sistem`}
      >
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw data-icon="inline-start" className={cn(isFetching && "animate-spin")} />
          Refresh
        </Button>
        {data && (
          <Button onClick={() => exportCSV(data.items)}>
            <Download data-icon="inline-start" />
            Export CSV
          </Button>
        )}
      </PageHeader>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Klausul" value={data?.total ?? "—"} icon={ListChecks} loading={isPending} />
        <StatCard
          label="Prediksi Benar"
          value={data?.correct ?? "—"}
          icon={CheckCircle2}
          iconClassName={toneClasses.success.soft}
          loading={isPending}
        />
        <StatCard
          label="Akurasi"
          value={data?.accuracy != null ? `${(data.accuracy * 100).toFixed(1)}%` : "—"}
          icon={Target}
          iconClassName={toneClasses.info.soft}
          loading={isPending}
        />
        <StatCard
          label="Data Prediksi"
          value={data ? (data.has_predictions ? "Ada" : "Belum") : "—"}
          icon={Database}
          iconClassName={data?.has_predictions ? toneClasses.success.soft : undefined}
          loading={isPending}
        />
      </div>

      {data?.evaluation_file && (
        <div className="flex flex-col gap-1 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
          <p>
            Prediksi dari satu run evaluasi
            {data.model && <> · {data.model}</>}
            {data.retrieval_strategy && <> · {data.retrieval_strategy}</>}
            {data.evaluation_timestamp && <> · {formatDateTime(data.evaluation_timestamp)}</>}
            {data.repeat && (
              <>
                {" "}
                (ulangan ke-{data.repeat.run_index} dari {data.repeat.n_runs})
              </>
            )}
          </p>
          {data.repeat?.accuracy_mean != null && (
            <p>
              Akurasi rerata {data.repeat.n_runs} ulangan (angka di laporan):{" "}
              <span className="font-medium text-foreground tabular-nums">
                {data.repeat.accuracy_mean.toFixed(3)} ± {(data.repeat.accuracy_sd ?? 0).toFixed(3)}
              </span>
            </p>
          )}
          <p>
            Sumber: <span className="font-mono break-all">{data.evaluation_file}</span>
          </p>
        </div>
      )}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Gagal memuat golden dataset</AlertTitle>
          <AlertDescription>{errorMessage(error)}</AlertDescription>
          <AlertAction>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Coba lagi
            </Button>
          </AlertAction>
        </Alert>
      ) : (
        <Card className="overflow-hidden py-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="w-20">ID</TableHead>
                <TableHead className="w-24">Kategori</TableHead>
                <TableHead className="min-w-64">Klausa</TableHead>
                <TableHead className="min-w-56">Kesalahan yang Dirancang</TableHead>
                <TableHead className="w-36">Label Benar</TableHead>
                <TableHead className="w-36">Prediksi Sistem</TableHead>
                <TableHead className="w-20 text-center">Benar?</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isPending &&
                [0, 1, 2, 3].map((i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton className="h-8 w-full" />
                    </TableCell>
                  </TableRow>
                ))}
              {data?.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                    Golden dataset kosong
                  </TableCell>
                </TableRow>
              )}
              {data?.items.map((item) => (
                <TableRow key={item.clause_id} className={cn("align-top", item.is_correct === false && "bg-red-500/5")}>
                  <TableCell className="font-mono text-xs text-muted-foreground">{item.clause_id}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{item.category}</Badge>
                  </TableCell>
                  <TableCell className="max-w-sm whitespace-normal">
                    <ExpandableClause text={item.clause} />
                    {item.violated_articles.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {item.violated_articles.map((article) => (
                          <Badge key={article} variant="outline" className={cn("border-transparent", toneClasses.info.soft)}>
                            {article}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="max-w-xs whitespace-normal text-xs leading-relaxed text-muted-foreground">
                    {item.error_description}
                  </TableCell>
                  <TableCell>
                    <StatusBadge meta={verdictMeta(item.expected_status)} />
                  </TableCell>
                  <TableCell>
                    {item.predicted_status ? (
                      <StatusBadge meta={verdictMeta(item.predicted_status)} />
                    ) : (
                      <span className="text-xs text-muted-foreground">Belum ada</span>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    <CorrectIcon value={item.is_correct} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      <p className="text-xs text-muted-foreground">
        Prediksi diambil dari file evaluasi terbaru GPT-5.4-mini. Jalankan{" "}
        <code className="rounded bg-muted px-1 py-0.5 font-mono">run_ablation.sh</code> untuk memperbarui.
      </p>
    </>
  );
}
