import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider, LenisProvider } from "@/components/providers";
import { DashboardLayout } from "@/components/layout";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Compliance Audit RAG - Dashboard",
  description: "MLOps-ready RAG system for regulatory compliance auditing",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <LenisProvider>
          <QueryProvider>
            <DashboardLayout>{children}</DashboardLayout>
            <Toaster position="bottom-right" richColors />
          </QueryProvider>
        </LenisProvider>
      </body>
    </html>
  );
}