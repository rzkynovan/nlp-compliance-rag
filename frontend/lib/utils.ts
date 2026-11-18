import { format } from "date-fns";
import { id as localeId } from "date-fns/locale";

export { cn } from "cn";

export function formatDateTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  return format(date, "d MMM yyyy, HH:mm", { locale: localeId });
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatLatency(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} dtk` : `${ms.toFixed(0)} ms`;
}

export function downloadFile(content: string, filename: string, mimeType: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Satu sel CSV: selalu dikutip, tanda kutip di dalamnya digandakan. */
export function csvCell(value: string | number | boolean | null | undefined): string {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}
