import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface UIState {
  isSidebarCollapsed: boolean;
  isCommandOpen: boolean;
  activeModal: string | null;
  theme: "light" | "dark" | "system";
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  openCommand: () => void;
  closeCommand: () => void;
  openModal: (id: string) => void;
  closeModal: () => void;
  setTheme: (theme: UIState["theme"]) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      isSidebarCollapsed: false,
      isCommandOpen: false,
      activeModal: null,
      theme: "system",

      toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ isSidebarCollapsed: collapsed }),
      openCommand: () => set({ isCommandOpen: true }),
      closeCommand: () => set({ isCommandOpen: false }),
      openModal: (id) => set({ activeModal: id }),
      closeModal: () => set({ activeModal: null }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "ui-storage",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        isSidebarCollapsed: state.isSidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
);

export const useSidebarCollapsed = () => useUIStore((s) => s.isSidebarCollapsed);
export const useCommandOpen = () => useUIStore((s) => s.isCommandOpen);
export const useActiveModal = () => useUIStore((s) => s.activeModal);
export const useTheme = () => useUIStore((s) => s.theme);