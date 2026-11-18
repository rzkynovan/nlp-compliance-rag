"use client";

import { usePathname } from "next/navigation";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { isActivePath, NAV_ITEMS } from "./nav";
import { ThemeToggle } from "./ThemeToggle";

export function AppHeader() {
  const pathname = usePathname();
  const current = NAV_ITEMS.find((item) => isActivePath(pathname, item.href));

  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-1 data-vertical:h-4 data-vertical:self-center" />
      <span className="truncate text-sm font-medium">{current?.label ?? "Compliance RAG"}</span>
      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
      </div>
    </header>
  );
}
