"use client";

import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Play } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldContent, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import type { AuditRequest } from "@/lib/api";
import { regulatorOptions } from "@/lib/compliance";
import { TOP_K_MAX, TOP_K_MIN, useSettingsStore } from "@/lib/stores/settings-store";

const auditSchema = z.object({
  clause: z.string().trim().min(10, "Klausa minimal 10 karakter"),
  regulator: z.enum(["all", "BI", "OJK"]),
  top_k: z
    .number({ error: "Top-K harus berupa angka" })
    .int("Top-K harus bilangan bulat")
    .min(TOP_K_MIN, `Minimal ${TOP_K_MIN}`)
    .max(TOP_K_MAX, `Maksimal ${TOP_K_MAX}`),
  clause_id: z.string().optional(),
  context: z.string().optional(),
  use_cache: z.boolean(),
});

type AuditFormValues = z.infer<typeof auditSchema>;

interface AuditFormProps {
  onSubmit: (data: AuditRequest) => void;
  isPending?: boolean;
  defaultValues?: Partial<AuditFormValues>;
}

export function AuditForm({ onSubmit, isPending, defaultValues }: AuditFormProps) {
  const defaultRegulator = useSettingsStore((s) => s.defaultRegulator);
  const defaultTopK = useSettingsStore((s) => s.defaultTopK);
  const enableCache = useSettingsStore((s) => s.enableCache);

  const {
    control,
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors, isDirty },
  } = useForm<AuditFormValues>({
    resolver: zodResolver(auditSchema),
    defaultValues: {
      clause: "",
      regulator: defaultRegulator,
      top_k: defaultTopK,
      clause_id: "",
      context: "",
      use_cache: enableCache,
      ...defaultValues,
    },
  });

  // Pengaturan tersimpan baru terbaca setelah hidrasi; samakan form yang belum disentuh.
  useEffect(() => {
    if (isDirty) return;
    reset({ ...getValues(), regulator: defaultRegulator, top_k: defaultTopK, use_cache: enableCache });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hanya saat nilai pengaturan berubah
  }, [defaultRegulator, defaultTopK, enableCache]);

  function submit(values: AuditFormValues) {
    onSubmit({
      clause: values.clause,
      regulator: values.regulator,
      top_k: values.top_k,
      clause_id: values.clause_id?.trim() || undefined,
      context: values.context?.trim() || undefined,
      use_cache: values.use_cache,
    });
  }

  return (
    <form onSubmit={handleSubmit(submit)} noValidate>
      <FieldGroup className="gap-5">
        <Field data-invalid={!!errors.clause}>
          <FieldLabel htmlFor="clause">Klausa</FieldLabel>
          <Textarea
            id="clause"
            rows={5}
            placeholder="Masukkan klausa yang ingin diaudit..."
            aria-invalid={!!errors.clause}
            className="min-h-28"
            {...register("clause")}
          />
          <FieldError errors={[errors.clause]} />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="regulator">Regulator</FieldLabel>
            <Controller
              control={control}
              name="regulator"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="regulator" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {regulatorOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </Field>

          <Field data-invalid={!!errors.top_k}>
            <FieldLabel htmlFor="top_k">Jumlah Pasal (Top-K)</FieldLabel>
            <Input
              id="top_k"
              type="number"
              inputMode="numeric"
              min={TOP_K_MIN}
              max={TOP_K_MAX}
              aria-invalid={!!errors.top_k}
              {...register("top_k", { valueAsNumber: true })}
            />
            <FieldError errors={[errors.top_k]} />
          </Field>
        </div>

        <Field>
          <FieldLabel htmlFor="clause_id">ID Klausa (Opsional)</FieldLabel>
          <Input id="clause_id" placeholder="mis. KLAUSA-001" {...register("clause_id")} />
        </Field>

        <Field>
          <FieldLabel htmlFor="context">Konteks Tambahan (Opsional)</FieldLabel>
          <Textarea
            id="context"
            rows={2}
            placeholder="Informasi tambahan yang membantu analisis..."
            {...register("context")}
          />
        </Field>

        <Field orientation="horizontal">
          <Controller
            control={control}
            name="use_cache"
            render={({ field }) => (
              <Checkbox
                id="use_cache"
                checked={field.value}
                onCheckedChange={(checked) => field.onChange(checked === true)}
              />
            )}
          />
          <FieldContent>
            <FieldLabel htmlFor="use_cache" className="font-normal">
              Gunakan cache
            </FieldLabel>
            <FieldDescription>Nonaktifkan untuk memaksa audit dijalankan ulang.</FieldDescription>
          </FieldContent>
        </Field>

        <Button type="submit" size="lg" className="w-full" disabled={isPending}>
          {isPending ? <Spinner data-icon="inline-start" /> : <Play data-icon="inline-start" />}
          {isPending ? "Menganalisis..." : "Jalankan Audit"}
        </Button>
      </FieldGroup>
    </form>
  );
}
