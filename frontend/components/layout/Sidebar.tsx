"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  FileSearch,
  History,
  FlaskConical,
  Settings,
  Home,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores/ui-store";
import { useAuthStore } from "@/lib/stores/auth-store";
import { logoutApi } from "@/lib/api/client";

const basicNavItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/audit", label: "Audit", icon: FileSearch },
  { href: "/history", label: "History", icon: History },
];

const advancedOnlyItems = [
  { href: "/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/testing", label: "Testing Doc", icon: ClipboardList },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const collapsed = useUIStore((s) => s.isSidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const { role, username, logout } = useAuthStore();

  const navItems = role === "advanced"
    ? [...basicNavItems, ...advancedOnlyItems]
    : basicNavItems;

  const handleLogout = async () => {
    try { await logoutApi(); } catch { /* ignore */ }
    logout();
    router.push("/login");
  };

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 80 : 256 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="shrink-0 h-full bg-slate-900 text-white flex flex-col z-50 overflow-hidden"
    >
      <div className="flex items-center justify-between p-4 border-b border-slate-700 shrink-0">
        <motion.span
          animate={{ opacity: collapsed ? 0 : 1, width: collapsed ? 0 : "auto" }}
          transition={{ duration: 0.2 }}
          className="font-bold text-lg whitespace-nowrap overflow-hidden"
        >
          Compliance RAG
        </motion.span>
        <button
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="p-2 rounded-lg hover:bg-slate-700 transition-colors shrink-0"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link key={item.href} href={item.href}>
              <motion.div
                whileHover={{ x: collapsed ? 0 : 4 }}
                whileTap={{ scale: 0.98 }}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all",
                  collapsed && "justify-center",
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                )}
              >
                <Icon size={20} className="shrink-0" />
                {!collapsed && (
                  <span className="font-medium whitespace-nowrap">{item.label}</span>
                )}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-700 shrink-0 space-y-3">
        {!collapsed && username && (
          <div className="text-xs text-slate-400">
            <div className="font-medium text-slate-300">{username}</div>
            <div className="capitalize text-slate-500">{role} user</div>
          </div>
        )}
        <button
          onClick={handleLogout}
          title={collapsed ? "Logout" : undefined}
          className={cn(
            "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm",
            collapsed && "justify-center"
          )}
        >
          <LogOut size={16} className="shrink-0" />
          {!collapsed && <span>Logout</span>}
        </button>
        {!collapsed && (
          <div className="text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span>System Online</span>
            </div>
          </div>
        )}
      </div>
    </motion.aside>
  );
}