import Link from "next/link";
import { Home } from "lucide-react";
import { BackButton } from "@/components/common/BackButton";
import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

export default function NotFound() {
  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <Empty>
        <EmptyHeader>
          <p className="text-6xl font-semibold tracking-tight">404</p>
          <EmptyTitle>Halaman tidak ditemukan</EmptyTitle>
          <EmptyDescription>
            Halaman yang Anda cari tidak dapat ditemukan. Mungkin halaman telah dipindahkan atau alamat URL salah.
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent className="flex-row justify-center">
          <Button asChild>
            <Link href="/">
              <Home data-icon="inline-start" />
              Ke Dashboard
            </Link>
          </Button>
          <BackButton />
        </EmptyContent>
      </Empty>
    </div>
  );
}
