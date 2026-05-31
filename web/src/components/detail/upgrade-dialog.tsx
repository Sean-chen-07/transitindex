"use client";

import * as React from "react";
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

/**
 * The account-gate upgrade dialog — replaces the KILLED "1 free / used" cookie meter.
 * Numbers are account-gated, NEVER metered: there is no free-view counter here. Radix
 * Dialog is focus-trapped, ESC-closable, with an aria-hidden background. Opening it logs
 * a `gate_view` conversion event (the funnel instrumentation).
 *
 * NOTE: the $20/yr checkout + sign-in links are wired in steps 7-8 (auth + Stripe). In
 * this free-app build the CTA is a visual placeholder.
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
        {/* TODO(step 8): wire to createCheckoutSession() + log checkout_start. */}
        <Button variant="primary" className="w-full" type="button">
          Continue — $20/year
        </Button>
        <p className="mt-3 text-center text-xs text-ink-3">
          Already a member? Sign in {/* TODO(step 7): /sign-in */}
        </p>
      </DialogContent>
    </Dialog>
  );
}
