import { toast } from "sonner";
import { useSettingsStore } from "@/lib/stores/settings-store";

/** Toast "audit selesai" — mengikuti Pengaturan → Notifikasi. Error selalu ditampilkan lewat toast.error. */
export function notifyAuditDone(title: string, description?: string) {
  if (useSettingsStore.getState().enableNotifications) {
    toast.success(title, { description });
  }
}
