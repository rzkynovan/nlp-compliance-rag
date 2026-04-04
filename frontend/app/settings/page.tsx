"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings, Database, Bell, Shield, Palette, Save } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    enableCache: true,
    enableNotifications: false,
    darkMode: false,
    autoSaveResults: true,
    defaultRegulator: "all",
    defaultTopK: 5,
    apiTimeout: 30000,
  });

  const handleSave = () => {
    localStorage.setItem("auditSettings", JSON.stringify(settings));
    toast.success("Pengaturan disimpan!");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Pengaturan</h1>
        <p className="text-gray-600 mt-1">
          Konfigurasi aplikasi dan preferensi pengguna
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              <CardTitle>General</CardTitle>
            </div>
            <CardDescription>Pengaturan umum aplikasi</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="cache" className="flex-1">
                <div className="font-medium">Enable Cache</div>
                <div className="text-sm text-gray-500">
                  Cache hasil audit untuk performa lebih cepat
                </div>
              </Label>
              <Switch
                id="cache"
                checked={settings.enableCache}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, enableCache: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="autoSave" className="flex-1">
                <div className="font-medium">Auto Save Results</div>
                <div className="text-sm text-gray-500">
                  Simpan hasil audit secara otomatis
                </div>
              </Label>
              <Switch
                id="autoSave"
                checked={settings.autoSaveResults}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, autoSaveResults: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              <CardTitle>Audit Defaults</CardTitle>
            </div>
            <CardDescription>Default nilai untuk form audit</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="defaultRegulator">Default Regulator</Label>
              <Select
                value={settings.defaultRegulator}
                onValueChange={(value) =>
                  setSettings({ ...settings, defaultRegulator: value })
                }
              >
                <SelectTrigger id="defaultRegulator">
                  <SelectValue placeholder="Pilih regulator" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Semua Regulator</SelectItem>
                  <SelectItem value="BI">Bank Indonesia</SelectItem>
                  <SelectItem value="OJK">OJK</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="defaultTopK">Default Top-K</Label>
              <Input
                id="defaultTopK"
                type="number"
                min={1}
                max={20}
                value={settings.defaultTopK}
                onChange={(e) =>
                  setSettings({ ...settings, defaultTopK: parseInt(e.target.value) || 5 })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiTimeout">API Timeout (ms)</Label>
              <Input
                id="apiTimeout"
                type="number"
                value={settings.apiTimeout}
                onChange={(e) =>
                  setSettings({ ...settings, apiTimeout: parseInt(e.target.value) || 30000 })
                }
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              <CardTitle>Appearance</CardTitle>
            </div>
            <CardDescription>Tampilan dan tema aplikasi</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="darkMode" className="flex-1">
                <div className="font-medium">Dark Mode</div>
                <div className="text-sm text-gray-500">
                  Gunakan tema gelap
                </div>
              </Label>
              <Switch
                id="darkMode"
                checked={settings.darkMode}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, darkMode: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              <CardTitle>Notifications</CardTitle>
            </div>
            <CardDescription>Pengaturan notifikasi</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="notifications" className="flex-1">
                <div className="font-medium">Enable Notifications</div>
                <div className="text-sm text-gray-500">
                  Tampilkan notifikasi untuk audit selesai
                </div>
              </Label>
              <Switch
                id="notifications"
                checked={settings.enableNotifications}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, enableNotifications: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              <CardTitle>API Configuration</CardTitle>
            </div>
            <CardDescription>Konfigurasi koneksi API backend</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Backend URL</Label>
                <Input
                  value={process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}
                  disabled
                  className="bg-gray-50"
                />
                <p className="text-xs text-gray-500">
                  Set via NEXT_PUBLIC_API_URL environment variable
                </p>
              </div>
              <div className="space-y-2">
                <Label>MLflow URL</Label>
                <Input
                  value={process.env.NEXT_PUBLIC_MLFLOW_URL || "http://localhost:5001"}
                  disabled
                  className="bg-gray-50"
                />
                <p className="text-xs text-gray-500">
                  Set via NEXT_PUBLIC_MLFLOW_URL environment variable
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Save className="h-4 w-4 mr-2" />
          Simpan Pengaturan
        </Button>
      </div>
    </div>
  );
}