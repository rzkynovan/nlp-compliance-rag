import { Suspense } from "react";
import { ShieldCheck } from "lucide-react";
import { LoginForm } from "@/components/auth/LoginForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function LoginPage() {
  return (
    <div className="flex flex-col gap-6">
      <Card className="py-6 [--card-spacing:--spacing(6)]">
        <CardHeader className="justify-items-center text-center">
          <div className="mb-2 flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <ShieldCheck className="size-5" />
          </div>
          <CardTitle className="text-xl">Compliance Audit</CardTitle>
          <CardDescription>Sistem Audit Kepatuhan Regulasi BI &amp; OJK</CardDescription>
        </CardHeader>
        <CardContent>
          {/* useSearchParams (?from=) butuh batas Suspense agar shell halaman tetap statis */}
          <Suspense fallback={<LoginFormSkeleton />}>
            <LoginForm />
          </Suspense>
        </CardContent>
      </Card>
      <p className="text-center text-xs text-muted-foreground">
        Institut Teknologi Sepuluh Nopember · Sains Data
      </p>
    </div>
  );
}

function LoginFormSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-14" />
      <Skeleton className="h-14" />
      <Skeleton className="h-9" />
    </div>
  );
}
