"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowUpDown, Calendar, CheckCircle2, ExternalLink, FlaskConical, RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { errorMessage, type ExperimentRun, getExperiments, queryKeys } from "@/lib/api";
import { toneClasses } from "@/lib/compliance";
import { MLFLOW_URL } from "@/lib/config";
import { cn, formatDateTime } from "@/lib/utils";

// Metrik yang dilaporkan di Bab 4 (skema 6 kelas), urut sesuai tabel laporan
const KEY_METRICS: [key: string, label: string][] = [
  ["accuracy", "Akurasi"],
  ["macro_f1", "Macro-F1"],
  ["recall_non_compliant_strict", "Recall NC ketat"],
  ["recall_non_compliant_broad", "Recall NC longgar"],
  ["mrr", "MRR"],
  ["hit_rate_at_5", "Hit@5"],
  ["citation_grounding_rate", "Grounding"],
];

function ExperimentCard({ run }: { run: ExperimentRun }) {
  const finished = run.status === "FINISHED";
  const params = run.params ?? {};
  const tags = run.tags ?? {};
  const metrics = KEY_METRICS.flatMap(([key, label]) => {
    const value = run.metrics?.[key];
    return typeof value === "number" ? [[label, value.toFixed(3)] as const] : [];
  });
  const latency = run.metrics?.avg_latency_ms;
  if (typeof latency === "number") metrics.push(["Latensi", `${(latency / 1000).toFixed(1)} dtk`]);

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="truncate" title={run.run_name ?? run.run_id}>
          {String(params.model ?? run.experiment_name ?? run.run_id)}
        </CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-1.5">
          {tags.strategy && <Badge variant="secondary">{tags.strategy}</Badge>}
          {tags.repeat_group && <Badge variant="outline">ulangan x3</Badge>}
          <Badge variant="outline" className={cn("border-transparent", (finished ? toneClasses.success : toneClasses.warning).soft)}>
            {finished ? <CheckCircle2 data-icon="inline-start" /> : <FlaskConical data-icon="inline-start" />}
            {run.status}
          </Badge>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Calendar className="size-4" />
          <span>{formatDateTime(run.start_time)}</span>
        </div>
        {metrics.length > 0 && (
          <div className="border-t pt-3">
            <div className="mb-2 flex items-center gap-1 text-xs font-medium">
              <ArrowUpDown className="size-3" />
              Metrics
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              {metrics.map(([label, value]) => (
                <div key={label} className="flex min-w-0 justify-between gap-2">
                  <dt className="truncate text-muted-foreground">{label}</dt>
                  <dd className="font-mono tabular-nums">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ExperimentsPage() {
  const { data, isPending, isFetching, error, refetch } = useQuery({
    queryKey: queryKeys.experiments.list(),
    queryFn: () => getExperiments(),
  });
  const experiments = data?.experiments ?? [];

  return (
    <>
      <PageHeader title="Eksperimen MLflow" description="Track dan bandingkan hasil eksperimen model">
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw data-icon="inline-start" className={cn(isFetching && "animate-spin")} />
          Refresh
        </Button>
      </PageHeader>

      {isPending ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-36 rounded-xl" />
          ))}
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Gagal memuat eksperimen</AlertTitle>
          <AlertDescription>{errorMessage(error)}</AlertDescription>
          <AlertAction>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Coba lagi
            </Button>
          </AlertAction>
        </Alert>
      ) : experiments.length > 0 ? (
        <>
          <p className="text-sm text-muted-foreground">
            Menampilkan {experiments.length} dari {data?.total ?? experiments.length} run
          </p>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {experiments.map((run) => (
              <ExperimentCard key={run.run_id} run={run} />
            ))}
          </div>
        </>
      ) : (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FlaskConical />
            </EmptyMedia>
            <EmptyTitle>Belum ada eksperimen</EmptyTitle>
            <EmptyDescription>Eksperimen MLflow akan muncul di sini</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Tentang MLflow Tracking</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
          <p>
            Setiap run evaluasi pada golden dataset (<code>src/evaluation_runner.py</code>) dicatat di MLflow beserta
            parameter, metrik, dan file hasilnya. Audit dari halaman Audit tidak dicatat di sini; riwayatnya ada di
            halaman Riwayat.
          </p>
          <ul className="list-inside list-disc space-y-1">
            <li>Klasifikasi 6 kelas: akurasi, macro-F1, recall Non-Compliant ketat dan longgar</li>
            <li>Retrieval: MRR dan Hit@3/Hit@5</li>
            <li>Citation grounding rate dan rata-rata latensi per klausul</li>
            <li>Model LLM dan strategi retrieval (query_aware, rrf_equal, dense)</li>
          </ul>
          <p>Run yang diberi label &ldquo;ulangan x3&rdquo; adalah tiga ulangan yang dirata-ratakan di laporan.</p>
          <Button asChild variant="outline" size="sm" className="self-start">
            <a href={MLFLOW_URL} target="_blank" rel="noopener noreferrer">
              Buka MLflow UI
              <ExternalLink data-icon="inline-end" />
            </a>
          </Button>
        </CardContent>
      </Card>
    </>
  );
}
