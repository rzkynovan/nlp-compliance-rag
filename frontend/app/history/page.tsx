"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock, FileText, CheckCircle2, XCircle } from "lucide-react";
import { format } from "date-fns";
import { id } from "date-fns/locale";

interface AuditHistory {
  request_id: string;
  timestamp: string;
  clause: string;
  final_status: string;
  overall_confidence: number;
  latency_ms: number;
}

export default function HistoryPage() {
  const { data: history, isLoading, error } = useQuery<AuditHistory[]>({
    queryKey: ["audit-history"],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/audit/history`);
      if (!res.ok) throw new Error("Failed to fetch history");
      return res.json();
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Riwayat Audit</h1>
        <p className="text-gray-600 mt-1">
          Daftar semua audit yang telah dilakukan
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-4" />
                <div className="h-3 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-6 text-center text-gray-500">
            <XCircle className="h-8 w-8 mx-auto mb-2" />
            <p>Gagal memuat riwayat audit</p>
          </CardContent>
        </Card>
      ) : history && history.length > 0 ? (
        <div className="grid gap-4">
          {history.map((item) => (
            <Card key={item.request_id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {item.final_status === "COMPLIANT" ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                      <span className="font-medium">{item.final_status}</span>
                      <span className="text-sm text-gray-500">
                        ({(item.overall_confidence * 100).toFixed(0)}% confidence)
                      </span>
                    </div>
                    <p className="text-gray-700 line-clamp-2">{item.clause}</p>
                    <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        <span>{item.latency_ms}ms</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <FileText className="h-4 w-4" />
                        <span>{item.request_id.slice(0, 8)}...</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-500">
                    {format(new Date(item.timestamp), "d MMM yyyy, HH:mm", { locale: id })}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-12 text-center text-gray-500">
            <FileText className="h-12 w-12 mx-auto mb-3 text-gray-400" />
            <p>Belum ada riwayat audit</p>
            <p className="text-sm mt-1">Audit pertama Anda akan muncul di sini</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}