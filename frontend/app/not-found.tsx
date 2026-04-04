"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle, Home, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center px-4">
        <div className="flex justify-center mb-6">
          <div className="h-24 w-24 rounded-full bg-gray-100 flex items-center justify-center">
            <AlertCircle className="h-12 w-12 text-gray-400" />
          </div>
        </div>
        <h1 className="text-6xl font-bold text-gray-900 mb-2">404</h1>
        <h2 className="text-xl font-medium text-gray-700 mb-4">
          Halaman tidak ditemukan
        </h2>
        <p className="text-gray-500 mb-8 max-w-md">
          Halaman yang Anda cari tidak dapat ditemukan. Mungkin halaman telah dipindahkan atau alamat URL salah.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link href="/">
            <Button variant="primary">
              <Home className="h-4 w-4 mr-2" />
              Ke Dashboard
            </Button>
          </Link>
          <Button variant="outline" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Kembali
          </Button>
        </div>
      </div>
    </div>
  );
}