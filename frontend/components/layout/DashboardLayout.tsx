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
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      {/* ml matches sidebar width: 256px expanded, 80px collapsed */}
      <motion.main
        animate={{ marginLeft: collapsed ? 80 : 256 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="flex-1 p-8 min-w-0"
      >
        {children}
      </motion.main>
    </div>
  );
}