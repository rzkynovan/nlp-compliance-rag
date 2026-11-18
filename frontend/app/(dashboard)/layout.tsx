import { Suspense } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AppHeader } from "@/components/layout/AppHeader";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { SessionProvider } from "@/components/SessionProvider";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";
import { getSession } from "@/lib/auth/server";
import { LOGIN_PATH } from "@/lib/auth/session";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  // Cookie hanya ada saat request, jadi dibaca di dalam Suspense; kerangka
  // di bawah ini yang masuk ke shell statis.
  return (
    <Suspense fallback={<ShellSkeleton />}>
      <AuthenticatedShell>{children}</AuthenticatedShell>
    </Suspense>
  );
}

async function AuthenticatedShell({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  // proxy.ts sudah menyaring request tanpa sesi; ini lapis kedua bila proxy terlewati.
  if (!session) redirect(LOGIN_PATH);

  const sidebarOpen = (await cookies()).get("sidebar_state")?.value !== "false";

  return (
    <SessionProvider session={session}>
      <SidebarProvider defaultOpen={sidebarOpen}>
        <AppSidebar />
        <SidebarInset>
          <AppHeader />
          <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-4 md:p-6">{children}</div>
        </SidebarInset>
      </SidebarProvider>
    </SessionProvider>
  );
}

function ShellSkeleton() {
  return (
    <div className="flex min-h-svh w-full">
      <div className="hidden w-64 shrink-0 flex-col gap-2 border-r bg-sidebar p-3 md:flex">
        <Skeleton className="h-10" />
        <Skeleton className="mt-4 h-8" />
        <Skeleton className="h-8" />
        <Skeleton className="h-8" />
      </div>
      <div className="flex flex-1 flex-col">
        <div className="h-14 border-b" />
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-4 md:p-6">
          <Skeleton className="h-9 w-56" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="h-64" />
        </div>
      </div>
    </div>
  );
}
