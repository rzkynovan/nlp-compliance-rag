import "server-only";

import { cookies } from "next/headers";
import { parseSession, TOKEN_COOKIE, type Session } from "./session";

/** Request-time: panggil hanya dari dalam batas <Suspense>. */
export async function getSession(): Promise<Session | null> {
  const store = await cookies();
  return parseSession(store.get(TOKEN_COOKIE)?.value);
}
