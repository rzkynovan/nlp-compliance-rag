import { ClipboardList, FileSearch, FlaskConical, History, Home, type LucideIcon, Settings } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  advanced?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/audit", label: "Audit", icon: FileSearch },
  { href: "/history", label: "Riwayat", icon: History },
  { href: "/experiments", label: "Eksperimen", icon: FlaskConical, advanced: true },
  { href: "/testing", label: "Dokumen Testing", icon: ClipboardList, advanced: true },
  { href: "/settings", label: "Pengaturan", icon: Settings, advanced: true },
];

export function isActivePath(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
