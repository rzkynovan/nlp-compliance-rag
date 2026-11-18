"use client";

import { AlertTriangle, ArrowRight, BookOpen, Clock, Coins, Database, Lightbulb, ShieldAlert } from "lucide-react";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import type { AgentVerdict, AuditResponse } from "@/lib/api";
import {
  queryTypeMeta,
  retrievalModeLabel,
  riskTone,
  skippedModeMeta,
  statusMeta,
  toneClasses,
  verdictMeta,
} from "@/lib/compliance";
import { cn, formatLatency, formatPercent } from "@/lib/utils";

type Regulator = "BI" | "OJK";

interface EvidenceRow {
  regulator: string;
  title: string;
  text?: string;
  score?: number;
}

const regulatorBadgeClass: Record<string, string> = {
  BI: "bg-sky-500/10 text-sky-700 dark:text-sky-400",
  OJK: "bg-violet-500/10 text-violet-700 dark:text-violet-400",
};

function RegulatorBadge({ regulator }: { regulator: string }) {
  return (
    <Badge variant="outline" className={cn("border-transparent", regulatorBadgeClass[regulator])}>
      {regulator || "—"}
    </Badge>
  );
}

function SectionTitle({
  icon: Icon,
  children,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h4 className={cn("flex items-center gap-2 text-sm font-medium", className)}>
      <Icon className="size-4" />
      {children}
    </h4>
  );
}

function ClauseBox({ clause, clauseId }: { clause: string; clauseId?: string | null }) {
  return (
    <div className="rounded-lg border bg-muted/40 p-3">
      <p className="mb-1 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        Klausa yang diaudit
        {clauseId && <Badge variant="outline">{clauseId}</Badge>}
      </p>
      <p className="text-sm leading-relaxed whitespace-pre-wrap">{clause}</p>
    </div>
  );
}

function Metric({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("text-sm font-semibold tabular-nums", className)}>{value}</p>
    </div>
  );
}

function EvidenceList({ rows, clamp }: { rows: EvidenceRow[]; clamp?: boolean }) {
  return (
    <ul className="flex flex-col gap-2">
      {rows.map((row, index) => (
        <li key={index} className="rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <RegulatorBadge regulator={row.regulator} />
            <span className="min-w-0 flex-1 truncate text-sm font-medium">{row.title}</span>
            {row.score !== undefined && (
              <span className="text-xs text-muted-foreground tabular-nums">
                Relevansi: {formatPercent(row.score)}
              </span>
            )}
          </div>
          {row.text && (
            <p className={cn("mt-1.5 text-xs leading-relaxed text-muted-foreground", clamp && "line-clamp-2")}>
              {row.text}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

function verdictEvidence(verdict: AgentVerdict | null, regulator: Regulator): EvidenceRow[] {
  return (verdict?.evidence ?? []).map((item) => ({
    regulator,
    title: [item.regulation, item.article].filter(Boolean).join(" · "),
    text: item.article_text,
    score: item.relevance_score,
  }));
}

/** Evidence dari verdik agen (membawa teks pasal); bila kosong pakai evidence_trail. */
function collectEvidence(result: AuditResponse): EvidenceRow[] {
  const rows = [...verdictEvidence(result.bi_verdict, "BI"), ...verdictEvidence(result.ojk_verdict, "OJK")];
  if (rows.length > 0) return rows;
  return (result.evidence_trail ?? []).map((item) => ({
    regulator: item.regulator ?? "",
    title: [item.document, item.bab, item.pasal].filter(Boolean).join(" · "),
    score: item.relevance_score,
  }));
}

function hasDetail(verdict: AgentVerdict): boolean {
  return (
    verdict.violations.length > 0 ||
    verdict.evidence.length > 0 ||
    (verdict.checklist_covered?.length ?? 0) > 0 ||
    (verdict.missing_elements?.length ?? 0) > 0 ||
    (!!verdict.reasoning && verdict.reasoning !== "No verdict available")
  );
}

function AgentDetailDialog({
  verdict,
  regulator,
  children,
}: {
  verdict: AgentVerdict;
  regulator: Regulator;
  children: React.ReactNode;
}) {
  const meta = verdictMeta(verdict.status);
  const covered = verdict.checklist_covered ?? [];
  const missing = verdict.missing_elements ?? [];
  const empty =
    !verdict.reasoning && verdict.violations.length === 0 && verdict.evidence.length === 0 && covered.length === 0 && missing.length === 0;

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="flex max-h-[85svh] flex-col gap-0 p-0 sm:max-w-2xl">
        <DialogHeader className="border-b p-4 pr-12">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-lg text-xs font-semibold",
                regulatorBadgeClass[regulator],
              )}
            >
              {regulator}
            </div>
            <div className="min-w-0 text-left">
              <DialogTitle>{regulator} Specialist</DialogTitle>
              <DialogDescription asChild>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <StatusBadge meta={meta} />
                  <span className="text-xs">Confidence {formatPercent(verdict.confidence)}</span>
                </div>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto p-4">
          {empty && <p className="py-6 text-center text-sm text-muted-foreground">Tidak ada detail tambahan tersedia</p>}

          {verdict.reasoning && (
            <section className="flex flex-col gap-2">
              <SectionTitle icon={Lightbulb}>Penalaran Agent</SectionTitle>
              <p className="rounded-lg bg-muted/50 p-3 text-sm leading-relaxed whitespace-pre-wrap">
                {verdict.reasoning}
              </p>
            </section>
          )}

          {(verdict.checklist_topic || covered.length > 0 || missing.length > 0) && (
            <section className="flex flex-col gap-2">
              <SectionTitle icon={BookOpen}>
                Checklist Regulasi{verdict.checklist_topic ? `: ${verdict.checklist_topic}` : ""}
              </SectionTitle>
              <div className="grid gap-3 sm:grid-cols-2">
                {covered.length > 0 && (
                  <div className="rounded-lg border p-3">
                    <p className={cn("mb-1.5 text-xs font-medium", toneClasses.success.text)}>
                      Tercakup ({covered.length})
                    </p>
                    <ul className="flex list-disc flex-col gap-1 pl-4 text-xs leading-relaxed">
                      {covered.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {missing.length > 0 && (
                  <div className="rounded-lg border p-3">
                    <p className={cn("mb-1.5 text-xs font-medium", toneClasses.danger.text)}>
                      Belum tercakup ({missing.length})
                    </p>
                    <ul className="flex list-disc flex-col gap-1 pl-4 text-xs leading-relaxed">
                      {missing.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {verdict.violations.length > 0 && (
            <section className="flex flex-col gap-2">
              <SectionTitle icon={ShieldAlert} className={toneClasses.danger.text}>
                Pelanggaran ({verdict.violations.length})
              </SectionTitle>
              <ul className="flex flex-col gap-2">
                {verdict.violations.map((violation, index) => {
                  // Format backend: "<regulasi pasal>: <uraian>"
                  const separator = violation.indexOf(":");
                  const heading = separator > 0 ? violation.slice(0, separator).trim() : "";
                  const detail = separator > 0 ? violation.slice(separator + 1).trim() : violation;
                  return (
                    <li key={index} className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                      {heading && <p className={cn("text-xs font-semibold", toneClasses.danger.text)}>{heading}</p>}
                      <p className="text-sm leading-relaxed">{detail}</p>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {verdict.evidence.length > 0 && (
            <section className="flex flex-col gap-2">
              <SectionTitle icon={Database}>Evidence ({verdict.evidence.length} pasal)</SectionTitle>
              <EvidenceList rows={verdictEvidence(verdict, regulator)} />
            </section>
          )}
        </div>

        <DialogFooter className="border-t p-3">
          <DialogClose asChild>
            <Button variant="outline">Tutup</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AgentVerdictCard({ verdict, regulator }: { verdict: AgentVerdict | null; regulator: Regulator }) {
  if (!verdict) {
    return (
      <div className="rounded-lg border border-dashed p-3">
        <p className="text-sm font-medium">{regulator} Specialist</p>
        <p className="mt-1 text-xs text-muted-foreground">Agen tidak dijalankan</p>
      </div>
    );
  }

  const meta = verdictMeta(verdict.status);
  const clickable = hasDetail(verdict);

  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <RegulatorBadge regulator={regulator} />
          <span className="text-sm font-medium">{regulator} Specialist</span>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">{formatPercent(verdict.confidence)}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <StatusBadge meta={meta} />
        {verdict.violations.length > 0 && (
          <span className={cn("text-xs font-medium", toneClasses.danger.text)}>
            {verdict.violations.length} pelanggaran
          </span>
        )}
      </div>
      {verdict.reasoning && (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground italic">{verdict.reasoning}</p>
      )}
      {clickable && (
        <p className="mt-2 flex items-center gap-1 text-xs font-medium text-primary">
          Klik untuk detail lengkap
          <ArrowRight className="size-3 transition-transform group-hover/agent:translate-x-0.5" />
        </p>
      )}
    </>
  );

  if (!clickable) return <div className="rounded-lg border p-3">{body}</div>;

  return (
    <AgentDetailDialog verdict={verdict} regulator={regulator}>
      <button
        type="button"
        className="group/agent rounded-lg border p-3 text-left transition-colors outline-none hover:border-primary/40 hover:bg-muted/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {body}
      </button>
    </AgentDetailDialog>
  );
}

function SkippedCard({ result }: { result: AuditResponse }) {
  const meta = skippedModeMeta[result.analysis_mode!]!;
  const Icon = meta.icon;
  const tone = toneClasses[meta.tone];
  const showClause = result.analysis_mode !== "greeting";

  return (
    <Card>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-full", tone.soft)}>
            <Icon className="size-5" />
          </div>
          <div className="min-w-0">
            <p className="font-medium">{meta.title}</p>
            <p className="mt-0.5 text-sm text-muted-foreground">{result.summary || meta.description}</p>
          </div>
        </div>
        {showClause && result.clause && <ClauseBox clause={result.clause} clauseId={result.clause_id} />}
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {result.analysis_mode === "gate_rejected" && result.gate_model && (
            <Badge variant="secondary">
              Gate: {result.gate_model}
              {result.gate_confidence !== undefined && ` · ${formatPercent(result.gate_confidence)}`}
            </Badge>
          )}
          {result.latency_ms > 0 && (
            <span className="flex items-center gap-1">
              <Clock className="size-3" />
              {formatLatency(result.latency_ms)}
            </span>
          )}
          {result.from_cache && <Badge variant="secondary">cache</Badge>}
        </div>
      </CardContent>
    </Card>
  );
}

export function ResultCard({ result }: { result: AuditResponse }) {
  if (result.analysis_mode && skippedModeMeta[result.analysis_mode]) {
    return <SkippedCard result={result} />;
  }

  const meta = statusMeta[result.final_status] ?? statusMeta.UNCLEAR;
  const tone = toneClasses[meta.tone];
  const StatusIcon = meta.icon;
  const queryType = result.query_type ? queryTypeMeta[result.query_type] : undefined;
  const QueryIcon = queryType?.icon;
  const retrieval = result.retrieval_mode && result.retrieval_mode !== "none" ? retrievalModeLabel[result.retrieval_mode] : null;
  const evidence = collectEvidence(result);

  return (
    <Card>
      <CardHeader className="gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={cn("flex size-11 shrink-0 items-center justify-center rounded-full", tone.soft)}>
              <StatusIcon className="size-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status akhir</p>
              <p className={cn("text-lg leading-tight font-semibold", tone.text)}>{meta.label}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Metric label="Confidence" value={formatPercent(result.overall_confidence)} />
            {result.risk_score > 0 && (
              <Metric
                label="Risk"
                value={formatPercent(result.risk_score)}
                className={toneClasses[riskTone(result.risk_score)].text}
              />
            )}
            <Metric label="Latency" value={formatLatency(result.latency_ms)} />
            {(result.tokens_used ?? 0) > 0 && (
              <Metric label="Tokens" value={result.tokens_used!.toLocaleString("id-ID")} />
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {result.from_cache && <Badge variant="secondary">cache</Badge>}
          {queryType && QueryIcon && (
            <Badge variant="outline">
              <QueryIcon data-icon="inline-start" />
              Query: {queryType.label}
            </Badge>
          )}
          {retrieval && <Badge variant="outline">Retrieval: {retrieval}</Badge>}
          {result.analysis_mode === "llm_only" && (
            <Badge variant="outline" className={cn("border-transparent", toneClasses.warning.soft)}>
              <AlertTriangle data-icon="inline-start" />
              LLM Only (no ChromaDB)
            </Badge>
          )}
          {result.gate_model && (
            <Badge variant="outline">
              Gate: {result.gate_model}
              {result.gate_confidence !== undefined && ` · ${formatPercent(result.gate_confidence)}`}
            </Badge>
          )}
          {result.model_used && (
            <Badge variant="outline">
              <Coins data-icon="inline-start" />
              {result.model_used}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        <ClauseBox clause={result.clause} clauseId={result.clause_id} />

        <div className="grid gap-3 md:grid-cols-2">
          <AgentVerdictCard verdict={result.bi_verdict} regulator="BI" />
          <AgentVerdictCard verdict={result.ojk_verdict} regulator="OJK" />
        </div>

        {result.violations.length > 0 && (
          <>
            <Separator />
            <section className="flex flex-col gap-2">
              <SectionTitle icon={ShieldAlert} className={toneClasses.danger.text}>
                Pelanggaran Ditemukan ({result.violations.length})
              </SectionTitle>
              <ul className="flex flex-col gap-1.5">
                {result.violations.map((violation, index) => (
                  <li key={index} className="flex gap-2 text-sm leading-relaxed">
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-red-500" />
                    <span>{violation}</span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}

        {result.recommendations.length > 0 && (
          <>
            <Separator />
            <section className="flex flex-col gap-2">
              <SectionTitle icon={Lightbulb}>Rekomendasi ({result.recommendations.length})</SectionTitle>
              <ul className="flex flex-col gap-1.5">
                {result.recommendations.map((recommendation, index) => (
                  <li key={index} className="flex gap-2 text-sm leading-relaxed">
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />
                    <span>{recommendation}</span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}

        {evidence.length > 0 && (
          <>
            <Separator />
            <section className="flex flex-col gap-2">
              <SectionTitle icon={Database}>Evidence Trail ({evidence.length})</SectionTitle>
              <EvidenceList rows={evidence} clamp />
            </section>
          </>
        )}
      </CardContent>
    </Card>
  );
}
