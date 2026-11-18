import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  FileText,
  FileWarning,
  GitMerge,
  HelpCircle,
  Layers,
  type LucideIcon,
  MessageSquare,
  Search,
  ShieldOff,
  XCircle,
} from "lucide-react";
import type { AnalysisMode, AuditResponse, ComplianceStatus, QueryType, RetrievalMode } from "@/lib/api/types";

type Tone = "success" | "danger" | "warning" | "neutral" | "info";

export interface StatusMeta {
  label: string;
  short: string;
  icon: LucideIcon;
  tone: Tone;
}

/** Kelas warna per nada, dipakai badge, ikon, dan aksen kartu. */
export const toneClasses: Record<Tone, { text: string; soft: string; border: string; dot: string }> = {
  success: {
    text: "text-emerald-700 dark:text-emerald-400",
    soft: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    border: "border-emerald-500/30",
    dot: "bg-emerald-500",
  },
  danger: {
    text: "text-red-700 dark:text-red-400",
    soft: "bg-red-500/10 text-red-700 dark:text-red-400",
    border: "border-red-500/30",
    dot: "bg-red-500",
  },
  warning: {
    text: "text-amber-700 dark:text-amber-400",
    soft: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    border: "border-amber-500/30",
    dot: "bg-amber-500",
  },
  neutral: {
    text: "text-muted-foreground",
    soft: "bg-muted text-muted-foreground",
    border: "border-border",
    dot: "bg-muted-foreground/60",
  },
  info: {
    text: "text-sky-700 dark:text-sky-400",
    soft: "bg-sky-500/10 text-sky-700 dark:text-sky-400",
    border: "border-sky-500/30",
    dot: "bg-sky-500",
  },
};

export const COMPLIANCE_STATUSES: ComplianceStatus[] = [
  "COMPLIANT",
  "NON_COMPLIANT",
  "PARTIALLY_COMPLIANT",
  "NEEDS_REVIEW",
  "NOT_ADDRESSED",
  "UNCLEAR",
];

export const statusMeta: Record<ComplianceStatus, StatusMeta> = {
  COMPLIANT: { label: "Patuh", short: "Patuh", icon: CheckCircle2, tone: "success" },
  NON_COMPLIANT: { label: "Tidak Patuh", short: "Tidak Patuh", icon: XCircle, tone: "danger" },
  PARTIALLY_COMPLIANT: { label: "Sebagian Patuh", short: "Sebagian", icon: AlertTriangle, tone: "warning" },
  NEEDS_REVIEW: { label: "Perlu Review", short: "Review", icon: AlertTriangle, tone: "warning" },
  NOT_ADDRESSED: { label: "Tidak Diatur", short: "—", icon: HelpCircle, tone: "neutral" },
  UNCLEAR: { label: "Tidak Jelas", short: "—", icon: HelpCircle, tone: "neutral" },
};

/** Mode analisis yang tidak menghasilkan verdik kepatuhan (audit dilewati). */
export const skippedModeMeta: Partial<Record<AnalysisMode, StatusMeta & { title: string; description: string }>> = {
  greeting: {
    label: "Sapaan",
    short: "Sapaan",
    icon: MessageSquare,
    tone: "info",
    title: "Sapaan Diterima",
    description: "Sistem menerima sapaan — tidak ada retrieval yang dijalankan",
  },
  out_of_scope: {
    label: "Di Luar Scope",
    short: "Luar Scope",
    icon: Ban,
    tone: "neutral",
    title: "Pertanyaan Di Luar Cakupan",
    description: "Pertanyaan tidak berkaitan dengan kepatuhan regulasi BI/OJK",
  },
  noise_filtered: {
    label: "Header/Noise",
    short: "Noise",
    icon: FileText,
    tone: "neutral",
    title: "Header/Noise — Dilewati",
    description:
      "Teks dikenali sebagai header dokumen, disclaimer, atau halaman sampul — bukan klausa substantif. Audit dilewati otomatis.",
  },
  gate_rejected: {
    label: "Ditolak Gate",
    short: "Ditolak",
    icon: ShieldOff,
    tone: "warning",
    title: "Bukan Klausa Regulasi Perusahaan",
    description:
      "Gate classifier tidak mengenali input sebagai klausa kebijakan, prosedur, atau syarat & ketentuan layanan keuangan. Audit tidak dijalankan.",
  },
  unclear_text: {
    label: "Teks Rusak",
    short: "Rusak",
    icon: FileWarning,
    tone: "neutral",
    title: "Teks Tidak Terbaca",
    description:
      "Teks klausa rusak atau tidak dapat dibaca (misalnya karakter ter-spacing hasil ekstraksi PDF) sehingga tidak dapat diklasifikasikan.",
  },
};

export function isSkipped(result: Pick<AuditResponse, "analysis_mode">): boolean {
  return !!result.analysis_mode && result.analysis_mode in skippedModeMeta;
}

/** Tampilan status sebuah hasil: mode yang dilewati menimpa verdik akhir. */
export function resultMeta(result: Pick<AuditResponse, "analysis_mode" | "final_status">): StatusMeta {
  const skipped = result.analysis_mode ? skippedModeMeta[result.analysis_mode] : undefined;
  return skipped ?? statusMeta[result.final_status] ?? statusMeta.UNCLEAR;
}

export function verdictMeta(status: string | undefined): StatusMeta {
  return statusMeta[status as ComplianceStatus] ?? statusMeta.UNCLEAR;
}

export const queryTypeMeta: Record<QueryType, { label: string; icon: LucideIcon }> = {
  exact_regulation: { label: "Exact Match", icon: Search },
  hybrid_regulation: { label: "Hybrid Search", icon: GitMerge },
  semantic_compliance: { label: "Semantic", icon: Layers },
  greeting: { label: "Sapaan", icon: MessageSquare },
  out_of_scope: { label: "Di Luar Scope", icon: Ban },
  noise: { label: "Header/Noise", icon: FileText },
  unclear: { label: "Teks Rusak", icon: FileWarning },
};

export const retrievalModeLabel: Record<RetrievalMode, string> = {
  exact: "BM25 Exact",
  hybrid: "Hybrid (BM25+Dense)",
  dense: "Dense",
  dense_only: "Dense Only",
  none: "—",
};

export const regulatorOptions = [
  { value: "all", label: "Semua Regulator" },
  { value: "BI", label: "Bank Indonesia" },
  { value: "OJK", label: "OJK" },
] as const;

export function riskTone(score: number): Tone {
  if (score >= 0.7) return "danger";
  if (score >= 0.4) return "warning";
  return "success";
}

export function violationCount(result: Pick<AuditResponse, "bi_verdict" | "ojk_verdict">): number {
  return (result.bi_verdict?.violations?.length ?? 0) + (result.ojk_verdict?.violations?.length ?? 0);
}
