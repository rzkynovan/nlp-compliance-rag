"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { analyzeSop, type AuditResponse } from "@/lib/api";
import { AuditForm } from "@/components/audit/AuditForm";
import { ResultCard } from "@/components/audit/ResultCard";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { FileSearch, History, FlaskConical, TrendingUp } from "lucide-react";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function HomePage() {
  const [results, setResults] = useState<AuditResponse | null>(null);

  const mutation = useMutation({
    mutationFn: analyzeSop,
    onSuccess: (data) => setResults(data),
  });

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-8"
    >
      <motion.header variants={item}>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Multi-Agent RAG system for BI/OJK regulatory compliance auditing
        </p>
      </motion.header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          variants={item}
          className="bg-white rounded-xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            SOP Audit
          </h2>
          <AuditForm onSubmit={(data) => mutation.mutate(data)} />
        </motion.div>

        <motion.div variants={item}>
          {mutation.isPending && (
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner />
            </div>
          )}

          {results && !mutation.isPending && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Results
              </h2>
              <ResultCard data={results} />
            </motion.div>
          )}

          {!results && !mutation.isPending && (
            <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 p-8 flex flex-col items-center justify-center h-64 text-gray-500">
              <FileSearch size={40} className="mb-3 text-gray-300" />
              <p>Audit results will appear here</p>
            </div>
          )}
        </motion.div>
      </div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Audits"
          value="1,234"
          description="All time"
          icon={<FileSearch className="text-blue-500" />}
          trend="+12%"
        />
        <StatCard
          title="Compliance Rate"
          value="78%"
          description="Last 30 days"
          icon={<History className="text-green-500" />}
          trend="+5%"
        />
        <StatCard
          title="Avg. Latency"
          value="2.5s"
          description="Per audit"
          icon={<TrendingUp className="text-orange-500" />}
          trend="-8%"
        />
        <StatCard
          title="Experiments"
          value="24"
          description="MLflow runs"
          icon={<FlaskConical className="text-purple-500" />}
          trend="+3"
        />
      </motion.div>
    </motion.div>
  );
}

function StatCard({
  title,
  value,
  description,
  icon,
  trend,
}: {
  title: string;
  value: string;
  description: string;
  icon: React.ReactNode;
  trend: string;
}) {
  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
      className="bg-white rounded-xl shadow-sm border border-gray-100 p-5"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50">{icon}</div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-gray-400">{description}</p>
        <span className="text-xs font-medium text-green-600">{trend}</span>
      </div>
    </motion.div>
  );
}