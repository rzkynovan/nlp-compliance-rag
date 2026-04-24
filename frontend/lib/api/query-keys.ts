export const queryKeys = {
  audits: {
    all: ["audits"] as const,
    lists: () => [...queryKeys.audits.all, "list"] as const,
    list: (filters: Record<string, unknown>) => [...queryKeys.audits.lists(), filters] as const,
    detail: (id: string) => [...queryKeys.audits.all, "detail", id] as const,
  },
  regulations: {
    all: ["regulations"] as const,
    lists: () => [...queryKeys.regulations.all, "list"] as const,
    search: (query: string, regulator?: string) => [...queryKeys.regulations.all, "search", query, regulator] as const,
    detail: (id: string) => [...queryKeys.regulations.all, "detail", id] as const,
  },
  experiments: {
    all: ["experiments"] as const,
    lists: () => [...queryKeys.experiments.all, "list"] as const,
    detail: (id: string) => [...queryKeys.experiments.all, "detail", id] as const,
    runs: (experimentId: string) => [...queryKeys.experiments.all, "runs", experimentId] as const,
  },
} as const;