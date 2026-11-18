import { NextResponse, type NextRequest } from "next/server";
import {
  HOME_AFTER_LOGIN,
  LOGIN_PATH,
  TOKEN_COOKIE,
  isAdvancedOnly,
  parseSession,
  resolveRedirect,
} from "@/lib/auth/session";

// Pemeriksaan optimistis: semua halaman dashboard (termasuk "/") butuh sesi.
// Backend tetap menjadi penentu otorisasi untuk setiap panggilan API.
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const session = parseSession(request.cookies.get(TOKEN_COOKIE)?.value);

  if (pathname === LOGIN_PATH) {
    if (!session) return NextResponse.next();
    const target = resolveRedirect(request.nextUrl.searchParams.get("from"), session.role);
    return NextResponse.redirect(new URL(target, request.url));
  }

  if (!session) {
    const loginUrl = new URL(LOGIN_PATH, request.url);
    if (pathname !== "/") loginUrl.searchParams.set("from", pathname + search);
    const response = NextResponse.redirect(loginUrl);
    // Token kedaluwarsa/rusak dibuang supaya tidak dikirim lagi ke backend.
    response.cookies.delete(TOKEN_COOKIE);
    return response;
  }

  if (isAdvancedOnly(pathname) && session.role !== "advanced") {
    return NextResponse.redirect(new URL(HOME_AFTER_LOGIN, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.[a-zA-Z0-9]+$).*)"],
};
