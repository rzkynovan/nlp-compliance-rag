import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";

const auditFormSchema = z.object({
  clause: z.string().min(10, "Klausa minimal 10 karakter"),
  clause_id: z.string().optional(),
  context: z.string().optional(),
  top_k: z.number().min(1).max(20).default(5),
  regulator: z.enum(["all", "BI", "OJK"]).default("all"),
});

type AuditFormValues = z.infer<typeof auditFormSchema>;

interface AuditFormProps {
  onSubmit: (data: AuditFormValues) => void;
  isPending?: boolean;
  defaultValues?: Partial<AuditFormValues>;
}

export function AuditForm({ onSubmit, isPending = false, defaultValues }: AuditFormProps) {
  const form = useForm<AuditFormValues>({
    resolver: zodResolver(auditFormSchema),
    defaultValues: {
      clause: defaultValues?.clause || "",
      clause_id: defaultValues?.clause_id || "",
      context: defaultValues?.context || "",
      top_k: defaultValues?.top_k ||5,
      regulator: defaultValues?.regulator || "all",
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="clause"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Klausa SOP</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Masukkan klausa SOP yang ingin diaudit..."
                  className="min-h-[120px] resize-y"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="regulator"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Regulator</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Pilih regulator" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="all">Semua Regulator</SelectItem>
                    <SelectItem value="BI">Bank Indonesia</SelectItem>
                    <SelectItem value="OJK">OJK</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="top_k"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Jumlah Pasal (Top-K)</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    {...field}
                    onChange={(e) => field.onChange(parseInt(e.target.value) || 5)}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="clause_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>ID Klausa (Opsional)</FormLabel>
              <FormControl>
                <Input placeholder="e.g., SOP-001" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="context"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Konteks Tambahan (Opsional)</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Informasi tambahan yang membantu analisis..."
                  className="min-h-[60px]"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={isPending} className="w-full">
          {isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Menganalisis...
            </>
          ) : (
            "Jalankan Audit"
          )}
        </Button>
      </form>
    </Form>
  );
}