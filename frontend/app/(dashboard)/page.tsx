"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Coins, FileSearch, ShieldCheck, Timer, TrendingDown, TrendingUp, XCircle } from "lucide-react";
import { toast } from "sonner";
import { AuditForm } from "@/components/audit/AuditForm";
import { ResultCard } from "@/components/audit/ResultCard";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { useSession } from "@/components/SessionProvider";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import {
  analyzeSop,
  type AuditHistoryStats,
  type AuditResponse,
  errorMessage,
  getAuditHistoryStats,
  getUsageStats,
  queryKeys,
} from "@/lib/api";
import { resultMeta, statusMeta, toneClasses } from "@/lib/compliance";
import { notifyAuditDone } from "@/lib/notify";
import { cn, formatLatency } from "@/lib/utils";

const REFETCH_INTERVAL = 30_000;

function StatusDistribution({ stats }: { stats: AuditHistoryStats }) {
  const counted = stats.compliant + stats.non_compliant + stats.partially_compliant + stats.not_addressed + stats.unclear;
  const rows = [
    { meta: statusMeta.COMPLIANT, count: stats.compliant },
    { meta: statusMeta.PARTIALLY_COMPLIANT, count: stats.partially_compliant },
    { meta: statusMeta.NON_COMPLIANT, count: stats.non_compliant },
    { meta: statusMeta.NOT_ADDRESSED, count: stats.not_addressed },
    { meta: statusMeta.UNCLEAR, count: stats.unclear },
    // Statistik backend tidak memecah NEEDS_REVIEW; sisanya ditampilkan di sini.
    { meta: statusMeta.NEEDS_REVIEW, count: Math.max(0, stats.total - counted) },
  ].filter((row) => row.count > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribusi Status</CardTitle>
        <CardDescription>Seluruh riwayat audit ({stats.total})</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {rows.map(({ meta, count }) => {
          const share = stats.total > 0 ? (count / stats.total) * 100 : 0;
          return (
            <div key={meta.label} className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-sm">
                <span>{meta.label}</span>
                <span className="text-muted-foreground tabular-nums">
                  {count} · {share.toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div className={cn("h-full rounded-full", toneClasses[meta.tone].dot)} style={{ width: `${share}%` }} />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const session = useSession();
  const queryClient = useQueryClient();
  const [result, setResult] = useState<AuditResponse | null>(null);
  const isAdvanced = session.role === "advanced";

  const mutation = useMutation({
    mutationFn: analyzeSop,
    onSuccess: (data) => {
      setResult(data);
      notifyAuditDone("Audit selesai", `Status: ${resultMeta(data).label} · ${formatLatency(data.latency_ms)}`);
      void queryClient.invalidateQueries({ queryKey: queryKeys.audits.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.usage });
    },
    onError: (error) => {
      toast.error("Audit gagal", { description: errorMessage(error) });
    },
  });

  const { data: stats, isPending: statsPending } = useQuery({
    queryKey: queryKeys.audits.stats(),
    queryFn: getAuditHistoryStats,
    refetchInterval: REFETCH_INTERVAL,
  });

  // Endpoint usage khusus role advanced; untuk basic tidak dipanggil sama sekali.
  const { data: usage, isPending: usagePending } = useQuery({
    queryKey: queryKeys.usage,
    queryFn: getUsageStats,
    refetchInterval: REFETCH_INTERVAL,
    enabled: isAdvanced,
  });

  const total = stats?.total ?? 0;
  const complianceRate = stats && total > 0 ? Math.round((stats.compliant / total) * 100) : null;

  return (
    <>
      <PageHeader title="Dashboard" description="Multi-Agent RAG untuk audit kepatuhan regulasi BI & OJK" />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total Audit"
          value={total > 0 ? total.toLocaleString("id-ID") : "—"}
          hint="Seluruh riwayat"
          icon={FileSearch}
          iconClassName={toneClasses.info.soft}
          loading={statsPending}
        />
        <StatCard
          label="Compliance Rate"
          value={
            complianceRate !== null ? (
              <span className="inline-flex items-center gap-1.5">
                {complianceRate}%
                {complianceRate >= 70 ? (
                  <TrendingUp className={cn("size-4", toneClasses.success.text)} />
                ) : complianceRate < 40 ? (
                  <TrendingDown className={cn("size-4", toneClasses.danger.text)} />
                ) : null}
              </span>
            ) : (
              "—"
            )
          }
          hint={`${stats?.compliant ?? 0} patuh dari ${total}`}
          icon={ShieldCheck}
          iconClassName={toneClasses.success.soft}
          loading={statsPending}
        />
        <StatCard
          label="Avg. Latency"
          value={stats && total > 0 ? `${(stats.avg_latency_ms / 1000).toFixed(1)}s` : "—"}
          hint="Per audit"
          icon={Timer}
          iconClassName={toneClasses.warning.soft}
          loading={statsPending}
        />
        {isAdvanced ? (
          <StatCard
            label="Biaya Hari Ini"
            value={usage ? `$${usage.today.total_cost_usd.toFixed(4)}` : "—"}
            hint={
              usage
                ? `${usage.today.api_calls} API calls · ${usage.today.budget_percentage.toFixed(0)}% budget`
                : usagePending
                  ? "Memuat..."
                  : "Tidak tersedia"
            }
            icon={Coins}
            iconClassName="bg-violet-500/10 text-violet-700 dark:text-violet-400"
            loading={usagePending}
          />
        ) : (
          <StatCard
            label="Tidak Patuh"
            value={stats ? stats.non_compliant.toLocaleString("id-ID") : "—"}
            hint="Klausa melanggar regulasi"
            icon={XCircle}
            iconClassName={toneClasses.danger.soft}
            loading={statsPending}
          />
        )}
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Quick Audit</CardTitle>
            <CardDescription>Analisis cepat satu klausa</CardDescription>
            <CardAction>
              <Button asChild variant="ghost" size="sm">
                <Link href="/audit">
                  Audit lengkap
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent>
            <AuditForm onSubmit={(data) => mutation.mutate(data)} isPending={mutation.isPending} />
          </CardContent>
        </Card>

        <div className="flex min-w-0 flex-col gap-4" aria-live="polite">
          {mutation.isPending ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
                <Spinner className="size-8 text-primary" />
                <div>
                  <p className="text-sm font-medium">Menganalisis klausa...</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">Multi-agent RAG sedang bekerja</p>
                </div>
              </CardContent>
            </Card>
          ) : result ? (
            <ResultCard result={result} />
          ) : (
            <>
              {stats && total > 0 && <StatusDistribution stats={stats} />}
              <Empty className="border border-dashed">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <FileSearch />
                  </EmptyMedia>
                  <EmptyTitle>Hasil audit akan muncul di sini</EmptyTitle>
                  <EmptyDescription>
                    Untuk upload dokumen dan batch audit, buka <Link href="/audit">halaman Audit</Link>.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            </>
          )}
        </div>
      </div>
    </>
  );
}
