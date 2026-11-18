import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { type StatusMeta, toneClasses } from "@/lib/compliance";

export function StatusBadge({ meta, className }: { meta: StatusMeta; className?: string }) {
  const Icon = meta.icon;
  return (
    <Badge variant="outline" className={cn("border-transparent", toneClasses[meta.tone].soft, className)}>
      <Icon data-icon="inline-start" />
      {meta.label}
    </Badge>
  );
}
