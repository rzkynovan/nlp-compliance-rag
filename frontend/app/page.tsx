"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  FileSearch,
  ShieldCheck,
  Timer,
  Coins,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { analyzeSop, getAuditHistory, getUsageStats, type AuditResponse } from "@/lib/api";
import { AuditForm } from "@/components/audit/AuditForm";
import { ResultCard } from "@/components/audit/ResultCard";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export default function HomePage() {
  const [result, setResult] = useState<AuditResponse | null>(null);

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

  // Live stats
  const { data: usageStats } = useQuery({
    queryKey: ["usage-stats"],
    queryFn: getUsageStats,
    refetchInterval: 30_000,
  });

  const { data: history } = useQuery({
    queryKey: ["audit-history-summary"],
    queryFn: () => getAuditHistory(0, 100) as Promise<
      { final_status: string; latency_ms: number }[]
    >,
    refetchInterval: 30_000,
  });

  const historyList = Array.isArray(history) ? history : [];
  const totalAudits = historyList.length;
  const compliantCount = historyList.filter(
    (h) => h.final_status === "COMPLIANT",
  ).length;
  const complianceRate =
    totalAudits > 0 ? Math.round((compliantCount / totalAudits) * 100) : null;
  const avgLatency =
    totalAudits > 0
      ? (historyList.reduce((s, h) => s + (h.latency_ms || 0), 0) / totalAudits / 1000).toFixed(1)
      : null;

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
      {/* Header */}
      <motion.header variants={item}>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Multi-Agent RAG untuk audit kepatuhan regulasi BI & OJK
        </p>
      </motion.header>

      {/* Stat cards */}
      <motion.div variants={item} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Audit"
          value={totalAudits > 0 ? String(totalAudits) : "—"}
          description="Sesi ini"
          icon={<FileSearch className="h-5 w-5 text-blue-500" />}
          iconBg="bg-blue-50"
        />
        <StatCard
          title="Compliance Rate"
          value={complianceRate !== null ? `${complianceRate}%` : "—"}
          description={`${compliantCount} patuh dari ${totalAudits}`}
          icon={<ShieldCheck className="h-5 w-5 text-emerald-500" />}
          iconBg="bg-emerald-50"
          trend={complianceRate !== null ? (complianceRate >= 70 ? "up" : complianceRate >= 40 ? "flat" : "down") : undefined}
        />
        <StatCard
          title="Avg. Latency"
          value={avgLatency !== null ? `${avgLatency}s` : "—"}
          description="Per audit"
          icon={<Timer className="h-5 w-5 text-orange-500" />}
          iconBg="bg-orange-50"
        />
        <StatCard
          title="Biaya Hari Ini"
          value={usageStats ? `$${usageStats.today.total_cost_usd.toFixed(4)}` : "—"}
          description={usageStats ? `${usageStats.today.api_calls} API calls` : "Memuat..."}
          icon={<Coins className="h-5 w-5 text-violet-500" />}
          iconBg="bg-violet-50"
        />
      </motion.div>

      {/* Main: form + results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <motion.div
          variants={item}
          className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
        >
          <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Quick Audit</h2>
              <p className="text-xs text-gray-400 mt-0.5">Analisis cepat satu klausa</p>
            </div>
            <Link
              href="/audit"
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              Audit lengkap
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="p-6">
            <AuditForm
              onSubmit={(data) => mutation.mutate(data)}
              isPending={mutation.isPending}
            />
          </div>
        </motion.div>

        <motion.div variants={item}>
          {mutation.isPending && (
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-10 flex flex-col items-center gap-3 text-center">
              <div className="relative h-12 w-12">
                <div className="absolute inset-0 rounded-full border-4 border-slate-200" />
                <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-blue-600" />
              </div>
              <p className="text-sm font-medium text-slate-600">Menganalisis klausa...</p>
            </div>
          )}

          {result && !mutation.isPending && (
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <ResultCard data={result} />
            </motion.div>
          )}

          {!result && !mutation.isPending && (
            <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-12 flex flex-col items-center justify-center gap-3 text-center h-full min-h-[200px]">
              <FileSearch className="h-10 w-10 text-slate-300" />
              <div>
                <p className="text-sm font-medium text-slate-500">Hasil audit akan muncul di sini</p>
                <p className="text-xs text-slate-400 mt-1">
                  Atau gunakan{" "}
                  <Link href="/audit" className="text-blue-500 hover:underline">
                    halaman Audit
                  </Link>{" "}
                  untuk upload dokumen
                </p>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}

type TrendDir = "up" | "down" | "flat";

function StatCard({
  title,
  value,
  description,
  icon,
  iconBg,
  trend,
}: {
  title: string;
  value: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  trend?: TrendDir;
}) {
  const TrendIcon =
    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor =
    trend === "up"
      ? "text-emerald-600"
      : trend === "down"
        ? "text-red-500"
        : "text-slate-400";

  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: "0 6px 20px rgba(0,0,0,0.07)" }}
      transition={{ duration: 0.15 }}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{title}</p>
        <div className={`p-1.5 rounded-lg ${iconBg}`}>{icon}</div>
      </div>
      <p className="text-2xl font-bold text-slate-900 tabular-nums">{value}</p>
      <div className="mt-2 flex items-center gap-1.5">
        {trend && <TrendIcon className={`h-3.5 w-3.5 ${trendColor}`} />}
        <p className="text-xs text-slate-400">{description}</p>
      </div>
    </motion.div>
  );
}
