"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon" className="bg-destructive/10 text-destructive">
            <AlertTriangle />
          </EmptyMedia>
          <EmptyTitle>Terjadi Kesalahan</EmptyTitle>
          <EmptyDescription>
            Maaf, terjadi kesalahan yang tidak terduga. Silakan coba lagi atau hubungi Administrator jika masalah berlanjut.
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          {error.message && (
            <pre className="max-h-40 w-full overflow-auto rounded-lg bg-muted p-3 text-left text-xs">
              <code className="text-destructive">{error.message}</code>
            </pre>
          )}
          <Button onClick={reset}>
            <RefreshCw data-icon="inline-start" />
            Coba Lagi
          </Button>
        </EmptyContent>
      </Empty>
    </div>
  );
}
