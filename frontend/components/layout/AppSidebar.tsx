"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronsUpDown, LogOut, ShieldCheck } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { Spinner } from "@/components/ui/spinner";
import { useSession } from "@/components/SessionProvider";
import { healthCheck, logoutApi, queryKeys } from "@/lib/api";
import { clearSession, LOGIN_PATH } from "@/lib/auth/session";
import { cn } from "@/lib/utils";
import { isActivePath, NAV_ITEMS, type NavItem } from "./nav";

function NavGroup({ label, items }: { label: string; items: NavItem[] }) {
  const pathname = usePathname();
  const { isMobile, setOpenMobile } = useSidebar();

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map(({ href, label: itemLabel, icon: Icon }) => (
            <SidebarMenuItem key={href}>
              <SidebarMenuButton asChild isActive={isActivePath(pathname, href)} tooltip={itemLabel}>
                <Link href={href} onClick={() => isMobile && setOpenMobile(false)}>
                  <Icon />
                  <span>{itemLabel}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

function SystemStatus() {
  const { data, isError, isPending } = useQuery({
    queryKey: queryKeys.health,
    queryFn: healthCheck,
    refetchInterval: 30_000,
    retry: false,
  });
  const online = !isError && data?.status === "healthy";
  const label = isPending ? "Memeriksa sistem…" : online ? "Sistem Online" : "Sistem Offline";

  return (
    <div className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
      <span
        title={label}
        className={cn(
          "size-2 shrink-0 rounded-full",
          isPending ? "bg-muted-foreground/40" : online ? "bg-emerald-500" : "bg-red-500",
        )}
      />
      <span className="truncate group-data-[collapsible=icon]:hidden">{label}</span>
    </div>
  );
}

function UserMenu() {
  const session = useSession();
  const { isMobile } = useSidebar();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    // Token tidak disimpan di server; kegagalan panggilan ini tidak boleh menahan logout.
    await logoutApi().catch(() => undefined);
    clearSession();
    window.location.assign(LOGIN_PATH);
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" className="data-[state=open]:bg-sidebar-accent">
              <Avatar className="size-8 rounded-lg">
                <AvatarFallback className="rounded-lg bg-primary/10 font-medium text-primary">
                  {session.username.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{session.username}</span>
                <span className="truncate text-xs text-muted-foreground capitalize">{session.role} user</span>
              </div>
              <ChevronsUpDown className="ml-auto" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            side={isMobile ? "bottom" : "right"}
            align="end"
            sideOffset={4}
            className="min-w-52"
          >
            <DropdownMenuLabel className="font-normal">
              <p className="truncate text-sm font-medium text-foreground">{session.username}</p>
              <p className="text-xs text-muted-foreground capitalize">{session.role} user</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              disabled={loggingOut}
              onSelect={(event) => {
                event.preventDefault();
                void handleLogout();
              }}
            >
              {loggingOut ? <Spinner /> : <LogOut />}
              Keluar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

export function AppSidebar() {
  const session = useSession();
  const mainItems = NAV_ITEMS.filter((item) => !item.advanced);
  const advancedItems = session.role === "advanced" ? NAV_ITEMS.filter((item) => item.advanced) : [];

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <ShieldCheck className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Compliance RAG</span>
                  <span className="truncate text-xs text-muted-foreground">Audit Regulasi BI &amp; OJK</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavGroup label="Menu" items={mainItems} />
        {advancedItems.length > 0 && <NavGroup label="Lanjutan" items={advancedItems} />}
      </SidebarContent>

      <SidebarFooter>
        <SystemStatus />
        <UserMenu />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
