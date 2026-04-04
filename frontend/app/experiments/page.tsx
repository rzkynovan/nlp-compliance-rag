"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FlaskConical, ArrowUpDown, Calendar, CheckCircle2, XCircle } from "lucide-react";
import { format } from "date-fns";

interface Experiment {
  run_id: string;
  experiment_name: string;
  status: string;
  start_time: string;
  end_time?: string;
  metrics?: Record<string, number>;
}

export default function ExperimentsPage() {
  const { data: experiments, isLoading, error } = useQuery<Experiment[]>({
    queryKey: ["experiments"],
    queryFn: async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/experiments/list`);
      if (!res.ok) return [];
      return res.json();
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Eksperimen MLflow</h1>
        <p className="text-gray-600 mt-1">
          Track dan bandingkan hasil eksperimen model
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="h-3 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-1/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-6 text-center text-gray-500">
            <XCircle className="h-8 w-8 mx-auto mb-2" />
            <p>Gagal memuat eksperimen</p>
          </CardContent>
        </Card>
      ) : experiments && experiments.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {experiments.map((exp) => (
            <Card key={exp.run_id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <CardTitle className="text-base">{exp.experiment_name}</CardTitle>
                <CardDescription>
                  <div className="flex items-center gap-2 mt-1">
                    {exp.status === "FINISHED" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <FlaskConical className="h-4 w-4 text-yellow-500" />
                    )}
                    <span>{exp.status}</span>
                  </div>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-gray-500">
                    <Calendar className="h-4 w-4" />
                    <span>{format(new Date(exp.start_time), "d MMM yyyy, HH:mm")}</span>
                  </div>
                  {exp.metrics && Object.keys(exp.metrics).length > 0 && (
                    <div className="pt-2 border-t mt-2">
                      <div className="flex items-center gap-1 mb-2">
                        <ArrowUpDown className="h-3 w-3" />
                        <span className="text-xs font-medium">Metrics</span>
                      </div>
                      <div className="grid grid-cols-2 gap-1">
                        {Object.entries(exp.metrics).slice(0, 4).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-gray-500">{key}:</span>
                            <span className="font-mono">{typeof value === "number" ? value.toFixed(3) : value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-12 text-center text-gray-500">
            <FlaskConical className="h-12 w-12 mx-auto mb-3 text-gray-400" />
            <p>Belum ada eksperimen</p>
            <p className="text-sm mt-1">Eksperimen MLflow akan muncul di sini</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Tentang MLflow Tracking</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            MLflow digunakan untuk track metrik eksperimen, parameter model, dan artifacts.
            Setiap audit yang dijalankan akan dicatat sebagai run eksperimen dengan metrics:
          </p>
          <ul className="mt-3 text-sm text-gray-600 list-disc list-inside space-y-1">
            <li>Latency waktu proses</li>
            <li>Confidence score</li>
            <li>Tokens yang digunakan</li>
            <li>Model yang dipakai</li>
          </ul>
          <p className="mt-3 text-sm">
            <a
              href="http://localhost:5001"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Buka MLflow UI →
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}