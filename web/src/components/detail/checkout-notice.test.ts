import { describe, expect, it } from "vitest";
import { checkoutStateFrom } from "./checkout-notice";

describe("checkoutStateFrom", () => {
  it("maps success + active subscription to success-active", () => {
    expect(checkoutStateFrom("success", true)).toBe("success-active");
  });

  it("maps success WITHOUT an active subscription to success-pending (webhook lag)", () => {
    expect(checkoutStateFrom("success", false)).toBe("success-pending");
  });

  it("maps cancel to cancel regardless of subscription", () => {
    expect(checkoutStateFrom("cancel", false)).toBe("cancel");
    expect(checkoutStateFrom("cancel", true)).toBe("cancel");
  });

  it("returns null when there is no checkout param", () => {
    expect(checkoutStateFrom(undefined, false)).toBeNull();
    expect(checkoutStateFrom(undefined, true)).toBeNull();
  });

  it("returns null for an unrecognized checkout value", () => {
    expect(checkoutStateFrom("bogus", true)).toBeNull();
  });
});
