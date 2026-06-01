import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Protect /account ONLY; every other route stays public + crawlable.
//
// This is deliberately edge-safe: it does NOT import the Auth.js/postgres stack (that
// would pull the Node DB driver into the edge bundle, and database sessions can't be
// validated at the edge anyway). It only checks for the PRESENCE of a session cookie to
// bounce obviously-anonymous visitors. The authoritative check is app/account/page.tsx,
// which calls getSession() and redirects if there is no real session.
export function middleware(req: NextRequest) {
  const hasSessionCookie =
    req.cookies.has("authjs.session-token") ||
    req.cookies.has("__Secure-authjs.session-token");

  if (!hasSessionCookie) {
    const signInUrl = new URL("/sign-in", req.url);
    signInUrl.searchParams.set("callbackUrl", req.nextUrl.pathname);
    return NextResponse.redirect(signInUrl);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/account/:path*"] };
