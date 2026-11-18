"use client";

import { createContext, useContext } from "react";
import type { Session } from "@/lib/auth/session";

const SessionContext = createContext<Session | null>(null);

/** Sesi dibaca di server (cookie) lalu diteruskan, sehingga render pertama sudah tahu user & role. */
export function SessionProvider({ session, children }: { session: Session; children: React.ReactNode }) {
  return <SessionContext value={session}>{children}</SessionContext>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession harus dipakai di dalam SessionProvider");
  return session;
}
