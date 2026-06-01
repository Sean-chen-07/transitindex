"use client";

import * as React from "react";
import Link from "next/link";
import { Lock, Check } from "lucide-react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { logConversion } from "@/app/actions/log-conversion";
import { createCheckoutSession } from "@/server/billing/checkout";

/**
 * The account-gate upgrade dialog — replaces the KILLED "1 free / used" cookie meter.
 * Numbers are account-gated, NEVER metered: there is no free-view counter here. Radix
 * Dialog is focus-trapped, ESC-closable, with an aria-hidden background. Opening it logs
 * a `gate_view` conversion event (the funnel instrumentation).
 *
 * The CTA posts to the createCheckoutSession server action (auth-gated; it redirects an
 * anonymous caller to /sign-in and logs `checkout_start` itself, so we don't log it here).
 */
export function UpgradeDialog({ agencyId }: { agencyId?: number | null }) {
  const [open, setOpen] = React.useState(false);
  const logged = React.useRef(false);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next && !logged.current) {
      logged.current = true;
      void logConversion({ eventType: "gate_view", agencyId: agencyId ?? null });
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <button className="inline-flex min-h-[44px] items-center gap-2 rounded-full bg-coral px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-coral/90">
          <Lock aria-hidden className="h-4 w-4" />
          Open full data — $20/yr
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>Open the full data</DialogTitle>
        <DialogDescription>
          Ranks are always free. A membership unlocks every raw figure, its reporting
          period, and the exact source — for all agencies.
        </DialogDescription>
        <ul className="my-4 space-y-2 text-sm text-ink">
          {[
            "Every metric's exact number, not just the rank",
            "Reporting period + source for each figure",
            "Trend history per metric",
          ].map((line) => (
            <li key={line} className="flex items-start gap-2">
              <Check aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-teal" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
        {/* createCheckoutSession logs checkout_start + redirects to Stripe (or /sign-in). */}
        <form action={createCheckoutSession}>
          <Button variant="primary" className="w-full" type="submit">
            Continue — $20/year
          </Button>
        </form>
        <p className="mt-3 text-center text-xs text-ink-3">
          Already a member?{" "}
          <Link href="/sign-in" className="text-teal underline-offset-2 hover:underline">
            Sign in
          </Link>
        </p>
      </DialogContent>
    </Dialog>
  );
}
