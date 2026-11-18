import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Regulator = "all" | "BI" | "OJK";

export const TOP_K_MIN = 1;
// Batas atas mengikuti validasi backend (AuditRequest.top_k le=10).
export const TOP_K_MAX = 10;
export const API_TIMEOUT_MIN = 5_000;

export interface Settings {
  enableCache: boolean;
  autoSaveResults: boolean;
  enableNotifications: boolean;
  defaultRegulator: Regulator;
  defaultTopK: number;
  apiTimeout: number;
}

export const DEFAULT_SETTINGS: Settings = {
  enableCache: true,
  autoSaveResults: true,
  enableNotifications: true,
  defaultRegulator: "all",
  defaultTopK: 5,
  // Audit multi-agent bisa memakan puluhan detik; batas pendek memutus audit yang sah.
  apiTimeout: 120_000,
};

export function clampTopK(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_SETTINGS.defaultTopK;
  return Math.min(TOP_K_MAX, Math.max(TOP_K_MIN, Math.round(value)));
}

interface SettingsState extends Settings {
  update: (settings: Settings) => void;
  reset: () => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,
      update: (settings) =>
        set({
          ...settings,
          defaultTopK: clampTopK(settings.defaultTopK),
          apiTimeout: Math.max(API_TIMEOUT_MIN, Math.round(settings.apiTimeout) || DEFAULT_SETTINGS.apiTimeout),
        }),
      reset: () => set(DEFAULT_SETTINGS),
    }),
    { name: "settings-storage", version: 1 },
  ),
);
