"use client";

import { motion } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { useUIStore } from "@/lib/stores/ui-store";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const collapsed = useUIStore((s) => s.isSidebarCollapsed);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8 min-w-0">
        {children}
      </main>
    </div>
  );
}