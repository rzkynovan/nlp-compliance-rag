"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import { Bell, Palette, RotateCcw, Save, Settings as SettingsIcon, Shield, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useMounted } from "@/hooks/use-mounted";
import { regulatorOptions } from "@/lib/compliance";
import { API_URL, MLFLOW_URL } from "@/lib/config";
import {
  API_TIMEOUT_MIN,
  DEFAULT_SETTINGS,
  type Regulator,
  type Settings,
  TOP_K_MAX,
  TOP_K_MIN,
  useSettingsStore,
} from "@/lib/stores/settings-store";

const SETTING_KEYS = Object.keys(DEFAULT_SETTINGS) as (keyof Settings)[];

function currentSettings(): Settings {
  const state = useSettingsStore.getState();
  return Object.fromEntries(SETTING_KEYS.map((key) => [key, state[key]])) as unknown as Settings;
}

function SectionTitle({ icon: Icon, children }: { icon: typeof SettingsIcon; children: React.ReactNode }) {
  return (
    <CardTitle className="flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" />
      {children}
    </CardTitle>
  );
}

function SwitchField({
  id,
  label,
  description,
  checked,
  onCheckedChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <Field orientation="horizontal">
      <FieldContent>
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
        <FieldDescription>{description}</FieldDescription>
      </FieldContent>
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
    </Field>
  );
}

function SettingsForm() {
  const { resolvedTheme, setTheme } = useTheme();
  // Draf lokal: perubahan baru berlaku setelah "Simpan Pengaturan".
  const [saved, setSaved] = useState<Settings>(currentSettings);
  const [draft, setDraft] = useState<Settings>(saved);

  const set = <K extends keyof Settings>(key: K, value: Settings[K]) => setDraft((prev) => ({ ...prev, [key]: value }));
  const isDirty = SETTING_KEYS.some((key) => draft[key] !== saved[key]);

  const handleSave = () => {
    useSettingsStore.getState().update(draft);
    const next = currentSettings();
    setSaved(next);
    setDraft(next);
    toast.success("Pengaturan disimpan!");
  };

  const handleReset = () => {
    useSettingsStore.getState().reset();
    setSaved(DEFAULT_SETTINGS);
    setDraft(DEFAULT_SETTINGS);
    toast.success("Pengaturan dikembalikan ke default");
  };

  return (
    <>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <SectionTitle icon={SettingsIcon}>General</SectionTitle>
            <CardDescription>Pengaturan umum aplikasi</CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <SwitchField
                id="cache"
                label="Enable Cache"
                description="Cache hasil audit untuk performa lebih cepat"
                checked={draft.enableCache}
                onCheckedChange={(checked) => set("enableCache", checked)}
              />
              <SwitchField
                id="autoSave"
                label="Auto Save Results"
                description="Simpan hasil audit secara otomatis. Catatan: backend selalu menyimpan setiap audit ke riwayat, jadi opsi ini belum mengubah perilaku."
                checked={draft.autoSaveResults}
                onCheckedChange={(checked) => set("autoSaveResults", checked)}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionTitle icon={SlidersHorizontal}>Audit Defaults</SectionTitle>
            <CardDescription>Default nilai untuk form audit</CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="defaultRegulator">Default Regulator</FieldLabel>
                <Select value={draft.defaultRegulator} onValueChange={(value) => set("defaultRegulator", value as Regulator)}>
                  <SelectTrigger id="defaultRegulator" className="w-full">
                    <SelectValue placeholder="Pilih regulator" />
                  </SelectTrigger>
                  <SelectContent>
                    {regulatorOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="defaultTopK">Default Top-K</FieldLabel>
                <Input
                  id="defaultTopK"
                  type="number"
                  min={TOP_K_MIN}
                  max={TOP_K_MAX}
                  value={Number.isNaN(draft.defaultTopK) ? "" : draft.defaultTopK}
                  onChange={(event) => set("defaultTopK", event.target.valueAsNumber)}
                />
                <FieldDescription>
                  Jumlah pasal yang diambil per agen ({TOP_K_MIN}–{TOP_K_MAX}).
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="apiTimeout">API Timeout (ms)</FieldLabel>
                <Input
                  id="apiTimeout"
                  type="number"
                  min={API_TIMEOUT_MIN}
                  step={1000}
                  value={Number.isNaN(draft.apiTimeout) ? "" : draft.apiTimeout}
                  onChange={(event) => set("apiTimeout", event.target.valueAsNumber)}
                />
                <FieldDescription>
                  Batas waktu setiap permintaan ke backend (minimal {API_TIMEOUT_MIN.toLocaleString("id-ID")} ms).
                </FieldDescription>
              </Field>
            </FieldGroup>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionTitle icon={Palette}>Appearance</SectionTitle>
            <CardDescription>Tampilan dan tema aplikasi</CardDescription>
          </CardHeader>
          <CardContent>
            <SwitchField
              id="darkMode"
              label="Dark Mode"
              description="Gunakan tema gelap"
              checked={resolvedTheme === "dark"}
              onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <SectionTitle icon={Bell}>Notifications</SectionTitle>
            <CardDescription>Pengaturan notifikasi</CardDescription>
          </CardHeader>
          <CardContent>
            <SwitchField
              id="notifications"
              label="Enable Notifications"
              description="Tampilkan notifikasi untuk audit selesai"
              checked={draft.enableNotifications}
              onCheckedChange={(checked) => set("enableNotifications", checked)}
            />
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <SectionTitle icon={Shield}>API Configuration</SectionTitle>
            <CardDescription>Konfigurasi koneksi API backend</CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup className="md:grid md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="apiUrl">Backend URL</FieldLabel>
                <Input id="apiUrl" value={API_URL} disabled readOnly className="font-mono text-xs" />
                <FieldDescription>Set via NEXT_PUBLIC_API_URL environment variable</FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="mlflowUrl">MLflow URL</FieldLabel>
                <Input id="mlflowUrl" value={MLFLOW_URL} disabled readOnly className="font-mono text-xs" />
                <FieldDescription>Set via NEXT_PUBLIC_MLFLOW_URL environment variable</FieldDescription>
              </Field>
            </FieldGroup>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2">
        {isDirty && <p className="mr-auto text-sm text-muted-foreground">Ada perubahan yang belum disimpan.</p>}
        <Button variant="outline" onClick={handleReset}>
          <RotateCcw data-icon="inline-start" />
          Reset ke Default
        </Button>
        <Button onClick={handleSave}>
          <Save data-icon="inline-start" />
          Simpan Pengaturan
        </Button>
      </div>
    </>
  );
}

export default function SettingsPage() {
  // Pengaturan tersimpan di localStorage, jadi form baru dirender setelah hidrasi.
  const mounted = useMounted();

  return (
    <>
      <PageHeader title="Pengaturan" description="Konfigurasi aplikasi dan preferensi pengguna" />
      {mounted ? (
        <SettingsForm />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      )}
    </>
  );
}
