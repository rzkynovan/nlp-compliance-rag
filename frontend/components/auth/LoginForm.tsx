"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Eye, EyeOff } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { ApiError, loginApi } from "@/lib/api";
import { resolveRedirect, saveSession } from "@/lib/auth/session";

export function LoginForm() {
  const from = useSearchParams().get("from");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Username dan password wajib diisi.");
      return;
    }
    setError("");
    setPending(true);
    try {
      const response = await loginApi(username.trim(), password);
      const session = saveSession(response.access_token);
      if (!session) throw new Error("Token dari server tidak valid.");
      // Navigasi penuh: proxy langsung melihat cookie baru dan cache router
      // (termasuk redirect ke /login yang sempat di-prefetch) ikut terbuang.
      window.location.assign(resolveRedirect(from, session.role));
    } catch (err) {
      setPending(false);
      if (err instanceof ApiError && err.status === 401) {
        setError("Username atau password salah.");
      } else if (err instanceof ApiError && err.status === 0) {
        setError("Tidak dapat terhubung ke server. Pastikan backend berjalan.");
      } else {
        setError(err instanceof Error ? err.message : "Login gagal. Coba lagi.");
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <FieldGroup className="gap-5">
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <Field>
          <FieldLabel htmlFor="username">Username</FieldLabel>
          <Input
            id="username"
            name="username"
            autoComplete="username"
            autoFocus
            required
            placeholder="Masukkan username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={pending}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="password">Password</FieldLabel>
          <InputGroup>
            <InputGroupInput
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              placeholder="Masukkan password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={pending}
            />
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                size="icon-xs"
                aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? <EyeOff /> : <Eye />}
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
        <Button type="submit" size="lg" className="w-full" disabled={pending}>
          {pending && <Spinner data-icon="inline-start" />}
          {pending ? "Masuk..." : "Masuk"}
        </Button>
      </FieldGroup>
    </form>
  );
}
