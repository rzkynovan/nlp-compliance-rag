import { NextRequest, NextResponse } from "next/server";

// Routes that require authentication (any role)
const AUTH_REQUIRED = ["/audit", "/history", "/experiments", "/settings", "/testing"];

// Routes that require advanced role
const ADVANCED_ONLY = ["/experiments", "/settings", "/testing"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if path requires auth
  const requiresAuth = AUTH_REQUIRED.some((route) => pathname.startsWith(route));
  if (!requiresAuth) return NextResponse.next();

  // Read auth from cookie (we'll store role there for middleware access)
  const role = request.cookies.get("user_role")?.value;
  const token = request.cookies.get("access_token")?.value;

  // Not authenticated — redirect to login
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Basic user trying to access advanced-only routes
  const requiresAdvanced = ADVANCED_ONLY.some((route) => pathname.startsWith(route));
  if (requiresAdvanced && role !== "advanced") {
    return NextResponse.redirect(new URL("/audit", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/audit/:path*", "/history/:path*", "/experiments/:path*", "/settings/:path*", "/testing/:path*"],
};
