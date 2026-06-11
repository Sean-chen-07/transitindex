import { describe, it, expect } from "vitest";
import { safeReturnTo } from "@/lib/safe-return-to";

describe("safeReturnTo — open-redirect guard for checkout returnTo", () => {
  it("allows a same-site path", () => {
    expect(safeReturnTo("/agency/ttc")).toBe("/agency/ttc");
    expect(safeReturnTo("/account")).toBe("/account");
  });

  it("rejects protocol-relative //host (off-site redirect)", () => {
    expect(safeReturnTo("//evil.com")).toBe("/account");
  });

  it("rejects an absolute URL with a scheme", () => {
    expect(safeReturnTo("https://evil.com")).toBe("/account");
    expect(safeReturnTo("http://evil.com/agency/ttc")).toBe("/account");
  });

  it("rejects a path that does not start with /", () => {
    expect(safeReturnTo("agency/ttc")).toBe("/account");
  });

  it("rejects a path carrying a query or fragment (avoids double ?checkout=)", () => {
    expect(safeReturnTo("/agency/ttc?checkout=success")).toBe("/account");
    expect(safeReturnTo("/agency/ttc#frag")).toBe("/account");
  });

  it("falls back to /account for non-string input", () => {
    expect(safeReturnTo(null)).toBe("/account");
    expect(safeReturnTo(undefined)).toBe("/account");
    expect(safeReturnTo(42)).toBe("/account");
  });
});
