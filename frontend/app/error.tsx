"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center px-4">
        <div className="flex justify-center mb-6">
          <div className="h-24 w-24 rounded-full bg-red-100 flex items-center justify-center">
            <AlertTriangle className="h-12 w-12 text-red-500" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Terjadi Kesalahan
        </h1>
        <p className="text-gray-500 mb-6 max-w-md">
          Maaf, terjadi kesalahan yang tidak terduga. Silakan coba lagi atau hubungi Administrator jika masalah berlanjut.
        </p>
        {error.message && (
          <pre className="text-left bg-gray-100 p-4 rounded-lg mb-6 text-sm overflow-auto max-w-md mx-auto">
            <code className="text-red-600">{error.message}</code>
          </pre>
        )}
        <Button onClick={reset}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Coba Lagi
        </Button>
      </div>
    </div>
  );
}