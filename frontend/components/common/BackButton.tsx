"use client";

import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export function BackButton() {
  return (
    <Button variant="outline" onClick={() => window.history.back()}>
      <ArrowLeft data-icon="inline-start" />
      Kembali
    </Button>
  );
}
