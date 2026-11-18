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

const MAX_METRICS = 4;

function ExperimentCard({ run }: { run: ExperimentRun }) {
  const finished = run.status === "FINISHED";
  const metrics = Object.entries(run.metrics ?? {}).slice(0, MAX_METRICS);

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="truncate">{run.experiment_name}</CardTitle>
        <CardDescription>
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
              {metrics.map(([key, value]) => (
                <div key={key} className="flex min-w-0 justify-between gap-2">
                  <dt className="truncate text-muted-foreground">{key}:</dt>
                  <dd className="font-mono tabular-nums">{typeof value === "number" ? value.toFixed(3) : String(value)}</dd>
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
            MLflow digunakan untuk track metrik eksperimen, parameter model, dan artifacts. Setiap audit yang dijalankan akan
            dicatat sebagai run eksperimen dengan metrics:
          </p>
          <ul className="list-inside list-disc space-y-1">
            <li>Latency waktu proses</li>
            <li>Confidence score</li>
            <li>Tokens yang digunakan</li>
            <li>Model yang dipakai</li>
          </ul>
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
