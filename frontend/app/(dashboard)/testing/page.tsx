"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, MinusCircle, Download, RefreshCw } from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth-store";
import { getGoldenDataset, type GoldenDatasetItem } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  NON_COMPLIANT:      "bg-red-100 text-red-700 border-red-200",
  PARTIALLY_COMPLIANT:"bg-yellow-100 text-yellow-700 border-yellow-200",
  NOT_ADDRESSED:      "bg-gray-100 text-gray-600 border-gray-200",
  COMPLIANT:          "bg-green-100 text-green-700 border-green-200",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn("inline-flex px-2 py-0.5 rounded text-xs font-medium border", STATUS_COLORS[status] ?? "bg-gray-100 text-gray-500")}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function ExpandableClause({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const short = text.length > 100 ? text.slice(0, 100) + "..." : text;
  return (
    <div className="text-sm text-gray-700">
      {expanded ? text : short}
      {text.length > 100 && (
        <button onClick={() => setExpanded(!expanded)} className="ml-1 text-blue-600 hover:underline text-xs">
          {expanded ? "Sembunyikan" : "Lihat lengkap"}
        </button>
      )}
    </div>
  );
}

function exportCSV(items: GoldenDatasetItem[]) {
  const headers = ["ID", "Kategori", "Klausa SOP", "Kesalahan yang Dirancang", "Label Benar", "Prediksi Sistem", "Benar?", "Latency (ms)"];
  const rows = items.map(item => [
    item.clause_id,
    item.category,
    `"${item.clause.replace(/"/g, '""')}"`,
    `"${item.error_description.replace(/"/g, '""')}"`,
    item.expected_status,
    item.predicted_status ?? "N/A",
    item.is_correct == null ? "N/A" : item.is_correct ? "Ya" : "Tidak",
    item.latency_ms ?? "N/A",
  ]);
  const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "golden_dataset_testing.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function TestingPage() {
  const router = useRouter();
  const { role, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) { router.push("/login"); return; }
    if (role !== "advanced") router.push("/audit");
  }, [isAuthenticated, role, router]);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["golden-dataset"],
    queryFn: getGoldenDataset,
    staleTime: 60_000,
  });

  if (!isAuthenticated || role !== "advanced") return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dokumen Testing</h1>
          <p className="text-sm text-gray-500 mt-1">
            Golden dataset SOP Dummy NusantaraPay — 12 klausul dengan ground truth dan prediksi sistem
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          {data && (
            <button
              onClick={() => exportCSV(data.items)}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-[hsl(var(--primary))] text-white rounded-lg hover:opacity-90 transition-opacity"
            >
              <Download size={14} /> Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Summary stats */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-gray-900">{data.total}</div>
            <div className="text-xs text-gray-500 mt-1">Total Klausul</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-green-600">{data.correct ?? "—"}</div>
            <div className="text-xs text-gray-500 mt-1">Prediksi Benar</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="text-2xl font-bold text-blue-600">
              {data.accuracy != null ? `${(data.accuracy * 100).toFixed(1)}%` : "—"}
            </div>
            <div className="text-xs text-gray-500 mt-1">Akurasi</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className={cn("text-2xl font-bold", data.has_predictions ? "text-green-600" : "text-gray-400")}>
              {data.has_predictions ? "Ada" : "Belum"}
            </div>
            <div className="text-xs text-gray-500 mt-1">Data Prediksi</div>
          </div>
        </div>
      )}

      {data?.evaluation_file && (
        <div className="text-xs text-gray-400 bg-gray-50 rounded-lg px-3 py-2">
          Sumber prediksi: <span className="font-mono">{data.evaluation_file}</span>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left">
                <th className="px-4 py-3 font-medium text-gray-600 w-20">ID</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-24">Kategori</th>
                <th className="px-4 py-3 font-medium text-gray-600">Klausa SOP</th>
                <th className="px-4 py-3 font-medium text-gray-600">Kesalahan yang Dirancang</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-36">Label Benar</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-36">Prediksi Sistem</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-20 text-center">Benar?</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">Memuat data...</td>
                </tr>
              )}
              {data?.items.map((item) => (
                <tr key={item.clause_id} className={cn("hover:bg-gray-50", item.is_correct === false && "bg-red-50/30")}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{item.clause_id}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{item.category}</span>
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <ExpandableClause text={item.clause} />
                    {item.violated_articles.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {item.violated_articles.map((a) => (
                          <span key={a} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded border border-blue-100">{a}</span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <p className="text-xs text-gray-600 leading-relaxed">{item.error_description}</p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.expected_status} />
                  </td>
                  <td className="px-4 py-3">
                    {item.predicted_status
                      ? <StatusBadge status={item.predicted_status} />
                      : <span className="text-xs text-gray-400">Belum ada</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.is_correct == null ? (
                      <MinusCircle size={18} className="text-gray-300 mx-auto" />
                    ) : item.is_correct ? (
                      <CheckCircle2 size={18} className="text-green-500 mx-auto" />
                    ) : (
                      <XCircle size={18} className="text-red-500 mx-auto" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        Prediksi diambil dari file evaluasi terbaru GPT-5.4-mini.
        Jalankan <code className="bg-gray-100 px-1 rounded">run_ablation.sh</code> untuk memperbarui.
      </p>
    </div>
  );
}
