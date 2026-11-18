export const queryKeys = {
  audits: {
    all: ["audits"] as const,
    list: (filters: Record<string, unknown>) => [...queryKeys.audits.all, "list", filters] as const,
    stats: () => [...queryKeys.audits.all, "stats"] as const,
  },
  usage: ["usage"] as const,
  health: ["health"] as const,
  experiments: {
    all: ["experiments"] as const,
    list: () => [...queryKeys.experiments.all, "list"] as const,
  },
  evaluation: {
    goldenDataset: ["evaluation", "golden-dataset"] as const,
  },
} as const;
