/**
 * Sanitize a caller-supplied `returnTo` into a same-site path. Guards the checkout
 * redirect against open-redirect: only a path starting with a single "/" is allowed
 * ("//host" and "https://host" are rejected — they would send the user off-site after
 * Stripe). A "?" or "#" is rejected too, so the caller can safely append its own
 * "?checkout=success" without producing a double query string. Anything else falls back
 * to `/account`. Pure + unit-tested.
 */
export function safeReturnTo(raw: unknown): string {
  if (
    typeof raw === "string" &&
    raw.startsWith("/") &&
    !raw.startsWith("//") &&
    !raw.includes("?") &&
    !raw.includes("#")
  ) {
    return raw;
  }
  return "/account";
}
