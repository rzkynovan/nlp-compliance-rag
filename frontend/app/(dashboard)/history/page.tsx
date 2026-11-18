"use client";

import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  History,
  Search,
  SearchX,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { ResultCard } from "@/components/audit/ResultCard";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group";
import { Pagination, PaginationContent, PaginationItem } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type AgentVerdict,
  type AuditResponse,
  type ComplianceStatus,
  getAuditHistory,
  getAuditHistoryStats,
  queryKeys,
} from "@/lib/api";
import {
  COMPLIANCE_STATUSES,
  isSkipped,
  resultMeta,
  statusMeta,
  toneClasses,
  verdictMeta,
  violationCount,
} from "@/lib/compliance";
import { cn, csvCell, downloadFile, formatDateTime, formatLatency, formatPercent } from "@/lib/utils";

const PAGE_SIZE = 20;
const REFETCH_INTERVAL = 30_000;

type StatusFilter = "ALL" | ComplianceStatus;

// ── Export ───────────────────────────────────────────────────────────────────

function exportDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function exportJSON(items: AuditResponse[]) {
  const payload = {
    exported_at: new Date().toISOString(),
    total: items.length,
    results: items.map((r) => ({
      request_id: r.request_id,
      timestamp: r.timestamp,
      clause: r.clause,
      final_status: r.final_status,
      overall_confidence: r.overall_confidence,
      risk_score: r.risk_score,
      latency_ms: r.latency_ms,
      analysis_mode: r.analysis_mode,
      query_type: r.query_type,
      retrieval_mode: r.retrieval_mode,
      from_cache: r.from_cache,
      summary: r.summary,
      bi_verdict: r.bi_verdict,
      ojk_verdict: r.ojk_verdict,
      violations: r.violations,
      recommendations: r.recommendations,
    })),
  };
  downloadFile(JSON.stringify(payload, null, 2), `audit_results_${exportDate()}.json`, "application/json");
}

function exportCSV(items: AuditResponse[]) {
  const headers = [
    "request_id",
    "timestamp",
    "final_status",
    "overall_confidence",
    "risk_score",
    "latency_ms",
    "query_type",
    "retrieval_mode",
    "from_cache",
    "bi_status",
    "bi_confidence",
    "bi_violations_count",
    "ojk_status",
    "ojk_confidence",
    "ojk_violations_count",
    "total_violations",
    "clause_preview",
  ];
  const rows = items.map((r) => {
    const bi = r.bi_verdict;
    const ojk = r.ojk_verdict;
    return [
      r.request_id,
      r.timestamp,
      r.final_status,
      r.overall_confidence.toFixed(3),
      r.risk_score.toFixed(3),
      r.latency_ms.toFixed(0),
      r.query_type ?? "",
      r.retrieval_mode ?? "",
      r.from_cache ? "true" : "false",
      bi?.status ?? "",
      bi ? bi.confidence.toFixed(3) : "",
      bi?.violations.length ?? 0,
      ojk?.status ?? "",
      ojk ? ojk.confidence.toFixed(3) : "",
      ojk?.violations.length ?? 0,
      violationCount(r),
      csvCell(r.clause.slice(0, 200)),
    ].join(",");
  });
  // BOM agar Excel membaca UTF-8 dengan benar.
  downloadFile(`﻿${[headers.join(","), ...rows].join("\n")}`, `audit_results_${exportDate()}.csv`, "text/csv;charset=utf-8");
}

function ExportMenu({ items, label }: { items: AuditResponse[]; label: string }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Download data-icon="inline-start" />
          Export {label}
          <ChevronDown data-icon="inline-end" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-44">
        <DropdownMenuItem onSelect={() => exportJSON(items)}>
          <FileJson />
          JSON (lengkap)
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => exportCSV(items)}>
          <FileSpreadsheet />
          CSV (ringkasan)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ── Kartu riwayat ────────────────────────────────────────────────────────────

function AgentPill({ label, verdict }: { label: "BI" | "OJK"; verdict: AgentVerdict }) {
  const meta = verdictMeta(verdict.status);
  const Icon = meta.icon;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-xs">
      <span className="font-semibold">{label}</span>
      <Icon className={cn("size-3", toneClasses[meta.tone].text)} />
      <span className={toneClasses[meta.tone].text}>{meta.short}</span>
      <span className="text-muted-foreground tabular-nums">{formatPercent(verdict.confidence)}</span>
      {verdict.violations.length > 0 && (
        <span className={cn("font-medium tabular-nums", toneClasses.danger.text)}>{verdict.violations.length}⚠</span>
      )}
    </span>
  );
}

function HistoryCard({
  item,
  open,
  onOpenChange,
}: {
  item: AuditResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const meta = resultMeta(item);
  const Icon = meta.icon;
  const violations = violationCount(item);
  const skipped = isSkipped(item);

  return (
    <Collapsible open={open} onOpenChange={onOpenChange} className="overflow-hidden rounded-xl bg-card ring-1 ring-foreground/10">
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-start gap-3 p-4 text-left transition-colors outline-none hover:bg-muted/40 focus-visible:bg-muted/40"
        >
          <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-full", toneClasses[meta.tone].soft)}>
            <Icon className="size-4" />
          </span>
          <span className="flex min-w-0 flex-1 flex-col gap-1.5">
            <span className="flex flex-wrap items-center gap-2">
              <StatusBadge meta={meta} />
              <span className="text-xs text-muted-foreground">{formatDateTime(item.timestamp)}</span>
              {item.from_cache && <Badge variant="secondary">cache</Badge>}
            </span>
            <span className="line-clamp-2 text-sm leading-relaxed">{item.clause}</span>
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="size-3" />
                {formatLatency(item.latency_ms)}
              </span>
              {!skipped && <span>Confidence {formatPercent(item.overall_confidence)}</span>}
              {violations > 0 && (
                <span className={cn("font-medium", toneClasses.danger.text)}>{violations} pelanggaran</span>
              )}
              {!skipped && item.bi_verdict && <AgentPill label="BI" verdict={item.bi_verdict} />}
              {!skipped && item.ojk_verdict && <AgentPill label="OJK" verdict={item.ojk_verdict} />}
            </span>
          </span>
          <ChevronDown className={cn("mt-1 size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t bg-muted/20 p-3">
        <ResultCard result={item} />
      </CollapsibleContent>
    </Collapsible>
  );
}

function HistorySkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-start gap-3 rounded-xl p-4 ring-1 ring-foreground/10">
          <Skeleton className="size-9 rounded-full" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="flex gap-2">
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-28" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Halaman ──────────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(0);

  // Tunda pencarian agar tidak ada request di setiap ketikan.
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const statusParam = statusFilter === "ALL" ? "" : statusFilter;

  const { data: stats } = useQuery({
    queryKey: queryKeys.audits.stats(),
    queryFn: getAuditHistoryStats,
    refetchInterval: REFETCH_INTERVAL,
  });

  const {
    data: history,
    isPending,
    isError,
    isPlaceholderData,
    refetch,
  } = useQuery({
    queryKey: queryKeys.audits.list({ page, search: debouncedSearch, status: statusParam }),
    queryFn: () => getAuditHistory(page * PAGE_SIZE, PAGE_SIZE, debouncedSearch, statusParam),
    refetchInterval: REFETCH_INTERVAL,
    placeholderData: keepPreviousData,
  });

  const items = history ?? [];
  const isFiltering = !!debouncedSearch || !!statusParam;
  // Backend tidak mengembalikan total untuk hasil terfilter; perkirakan dari ukuran halaman.
  const totalPages = isFiltering
    ? items.length === PAGE_SIZE
      ? page + 2
      : page + 1
    : stats
      ? Math.max(1, Math.ceil(stats.total / PAGE_SIZE))
      : 1;
  const hasAnyAudit = (stats?.total ?? 0) > 0 || items.length > 0 || isFiltering;

  function changeFilter(filter: StatusFilter) {
    setStatusFilter(filter);
    setPage(0);
  }

  function changeSearch(value: string) {
    setSearch(value);
    setPage(0);
  }

  function toggleExpanded(id: string, open: boolean) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (open) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  return (
    <>
      <PageHeader
        title="Riwayat Audit"
        description="Daftar semua audit yang telah dilakukan · Klik kartu untuk melihat detail"
      >
        {stats && stats.total > 0 && <Badge variant="secondary">{stats.total} total</Badge>}
        {items.length > 0 && (
          <ExportMenu items={items} label={statusParam ? `(${items.length} filtered)` : "halaman ini"} />
        )}
      </PageHeader>

      {stats && stats.total > 0 && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Total Audit" value={stats.total} icon={FileText} />
          <StatCard
            label="Patuh"
            value={stats.compliant}
            icon={CheckCircle2}
            iconClassName={toneClasses.success.soft}
          />
          <StatCard
            label="Tidak Patuh"
            value={stats.non_compliant}
            icon={XCircle}
            iconClassName={toneClasses.danger.soft}
          />
          <StatCard label="Rata-rata Latency" value={formatLatency(stats.avg_latency_ms)} icon={Zap} />
        </div>
      )}

      {hasAnyAudit && (
        <div className="flex flex-col gap-3">
          <InputGroup className="max-w-md">
            <InputGroupAddon>
              <Search />
            </InputGroupAddon>
            <InputGroupInput
              type="search"
              placeholder="Cari klausa atau ID audit..."
              aria-label="Cari riwayat audit"
              value={search}
              onChange={(event) => changeSearch(event.target.value)}
              className="[&::-webkit-search-cancel-button]:hidden"
            />
            {search && (
              <InputGroupAddon align="inline-end">
                <InputGroupButton size="icon-xs" aria-label="Hapus pencarian" onClick={() => changeSearch("")}>
                  <X />
                </InputGroupButton>
              </InputGroupAddon>
            )}
          </InputGroup>

          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter status">
            {(["ALL", ...COMPLIANCE_STATUSES] as StatusFilter[]).map((filter) => {
              const active = statusFilter === filter;
              return (
                <Button
                  key={filter}
                  size="sm"
                  variant={active ? "default" : "outline"}
                  aria-pressed={active}
                  className="rounded-full"
                  onClick={() => changeFilter(filter)}
                >
                  {filter === "ALL" ? "Semua" : statusMeta[filter].label}
                </Button>
              );
            })}
          </div>

          {isFiltering && !isPending && items.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {items.length} hasil pada halaman ini
              {debouncedSearch && <> untuk &ldquo;{debouncedSearch}&rdquo;</>}
              {items.length === PAGE_SIZE && " (mungkin ada lebih)"}
            </p>
          )}
        </div>
      )}

      {isPending ? (
        <HistorySkeleton />
      ) : isError ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <AlertCircle />
            </EmptyMedia>
            <EmptyTitle>Gagal memuat riwayat</EmptyTitle>
            <EmptyDescription>Pastikan backend berjalan dan coba lagi</EmptyDescription>
          </EmptyHeader>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Coba lagi
          </Button>
        </Empty>
      ) : items.length === 0 ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">{isFiltering ? <SearchX /> : <History />}</EmptyMedia>
            <EmptyTitle>{isFiltering ? "Tidak ada hasil" : "Belum ada riwayat audit"}</EmptyTitle>
            <EmptyDescription>
              {isFiltering ? "Coba ubah filter atau kata kunci pencarian" : "Audit pertama Anda akan muncul di sini"}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <div className={cn("flex flex-col gap-3 transition-opacity", isPlaceholderData && "opacity-60")}>
          {items.map((item) => (
            <HistoryCard
              key={item.request_id}
              item={item}
              open={expandedIds.has(item.request_id)}
              onOpenChange={(open) => toggleExpanded(item.request_id, open)}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <Pagination>
          <PaginationContent className="gap-3">
            <PaginationItem>
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
                <ChevronLeft data-icon="inline-start" />
                Sebelumnya
              </Button>
            </PaginationItem>
            <PaginationItem className="text-sm text-muted-foreground tabular-nums">
              Halaman <span className="font-medium text-foreground">{page + 1}</span> dari{" "}
              <span className="font-medium text-foreground">{totalPages}</span>
            </PaginationItem>
            <PaginationItem>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              >
                Selanjutnya
                <ChevronRight data-icon="inline-end" />
              </Button>
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </>
  );
}
