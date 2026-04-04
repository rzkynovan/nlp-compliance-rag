"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { analyzeSop } from "@/lib/api";
import { AlertCircle, CheckCircle2, Clock, Loader2 } from "lucide-react";

const auditSchema = z.object({
  clause: z.string().min(10, "Klausa minimal 10 karakter"),
  regulator: z.enum(["all", "BI", "OJK"]),
  top_k: z.number().min(1).max(20),
  clause_id: z.string().optional(),
  context: z.string().optional(),
});

type AuditFormValues = z.infer<typeof auditSchema>;

export default function AuditPage() {
  const [result, setResult] = useState<Awaited<ReturnType<typeof analyzeSop>> | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AuditFormValues>({
    resolver: zodResolver(auditSchema),
    defaultValues: {
      clause: "",
      regulator: "all",
      top_k: 5,
    },
  });

  const mutation = useMutation({
    mutationFn: analyzeSop,
    onSuccess: (data) => {
      setResult(data);
    },
  });

  const onSubmit = (data: AuditFormValues) => {
    mutation.mutate(data);
  };

  const regulator = watch("regulator");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Audit Kepatuhan</h1>
        <p className="text-gray-600 mt-1">
          Analisis klausa SOP untuk kepatuhan regulasi BI dan OJK
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Form Audit</CardTitle>
            <CardDescription>
              Masukkan klausa SOP yang ingin diaudit
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="clause">Klausa SOP</Label>
                <Textarea
                  id="clause"
                  placeholder="Contoh: Saldo maksimal untuk akun unverified adalah Rp 10.000.000"
                  rows={4}
                  {...register("clause")}
                />
                {errors.clause && (
                  <p className="text-sm text-red-500">{errors.clause.message}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="regulator">Regulator</Label>
                  <Select
                    value={regulator}
                    onValueChange={(value) => setValue("regulator", value as "all" | "BI" | "OJK")}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih regulator" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Semua Regulator</SelectItem>
                      <SelectItem value="BI">Bank Indonesia</SelectItem>
                      <SelectItem value="OJK">OJK</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="top_k">Jumlah Pasal (Top-K)</Label>
                  <Input
                    id="top_k"
                    type="number"
                    min={1}
                    max={20}
                    {...register("top_k", { valueAsNumber: true })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="clause_id">ID Klausa (Opsional)</Label>
                <Input
                  id="clause_id"
                  placeholder="SOP-001"
                  {...register("clause_id")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="context">Konteks Tambahan (Opsional)</Label>
                <Textarea
                  id="context"
                  placeholder="Informasi tambahan untuk membantu analisis"
                  rows={2}
                  {...register("context")}
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={mutation.isPending}
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Memproses...
                  </>
                ) : (
                  "Jalankan Audit"
                )}
              </Button>

              {mutation.isError && (
                <div className="flex items-center gap-2 text-red-500 text-sm">
                  <AlertCircle className="h-4 w-4" />
                  <span>
                    {mutation.error instanceof Error
                      ? mutation.error.message
                      : "Terjadi kesalahan saat memproses audit"}
                  </span>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Hasil Audit</CardTitle>
            <CardDescription>
              Status kepatuhan berdasarkan analisis multi-agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            {mutation.isPending ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                <Loader2 className="h-8 w-8 animate-spin mb-3" />
                <p>Memproses audit...</p>
              </div>
            ) : result ? (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  {result.final_status === "COMPLIANT" ? (
                    <CheckCircle2 className="h-6 w-6 text-green-500" />
                  ) : result.final_status === "NON_COMPLIANT" ? (
                    <AlertCircle className="h-6 w-6 text-red-500" />
                  ) : (
                    <Clock className="h-6 w-6 text-yellow-500" />
                  )}
                  <div>
                    <div className="font-semibold text-lg">
                      {result.final_status}
                    </div>
                    <div className="text-sm text-gray-500">
                      Confidence: {(result.overall_confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <h3 className="font-medium mb-2">BI Verdict</h3>
                    <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                      <div className="flex justify-between mb-1">
                        <span>Status:</span>
                        <span className="font-medium">{result.bi_verdict?.status || "N/A"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Confidence:</span>
                        <span className="font-medium">
                          {result.bi_verdict ? (result.bi_verdict.confidence * 100).toFixed(0) + "%" : "N/A"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-medium mb-2">OJK Verdict</h3>
                    <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                      <div className="flex justify-between mb-1">
                        <span>Status:</span>
                        <span className="font-medium">{result.ojk_verdict?.status || "N/A"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Confidence:</span>
                        <span className="font-medium">
                          {result.ojk_verdict ? (result.ojk_verdict.confidence * 100).toFixed(0) + "%" : "N/A"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {result.recommendations && result.recommendations.length > 0 && (
                    <div>
                      <h3 className="font-medium mb-2">Rekomendasi</h3>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                        {result.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="text-xs text-gray-400 pt-4 border-t">
                    <div>Model: {result.model_used || "gpt-4o-mini"}</div>
                    <div>Latency: {result.latency_ms || 0}ms</div>
                    <div>Request ID: {result.request_id?.slice(0, 8)}...</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <AlertCircle className="h-10 w-10 mb-3" />
                <p>Hasil audit akan muncul di sini</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}