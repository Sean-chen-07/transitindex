"use client";

import * as React from "react";
import Link from "next/link";
import { Download, Check } from "lucide-react";
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
 * The subscribe-to-download dialog. Viewing is free for everyone (docs/design/
 * detail-view-metrics.md §6) — the only paid perk is the per-agency CSV download, gated
 * server-side in /api/agency/[slug]/download. Radix Dialog is focus-trapped, ESC-closable,
 * with an aria-hidden background. Opening it logs a `gate_view` conversion event once (the
 * gate-view funnel event — the gate is now the download).
 *
 * The CTA posts to the createCheckoutSession server action (auth-gated; it redirects an
 * anonymous caller to /sign-in and logs `checkout_start` itself, so we don't log it here).
 * returnTo is the agency page path — Stripe and sign-in both land the user back there.
 */
export function SubscribeDialog({
  returnTo,
  agencyId,
}: {
  returnTo: string;
  agencyId?: number | null;
}) {
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
          <Download aria-hidden className="h-4 w-4" />
          Download this agency&apos;s data (CSV)
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>Download this agency&apos;s full dataset</DialogTitle>
        <DialogDescription>
          Viewing every number on TransitIndex is free, always. A membership lets you take
          the data with you — one agency at a time.
        </DialogDescription>
        <ul className="my-4 space-y-2 text-sm text-ink">
          {[
            "The full all-years financial statement grid",
            "A clean CSV that opens in Excel",
            "Every agency page gets its own download",
          ].map((line) => (
            <li key={line} className="flex items-start gap-2">
              <Check aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-teal" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
        {/* createCheckoutSession logs checkout_start + redirects to Stripe (or /sign-in). */}
        {/* TODO(pricing): add price copy when pricing is decided */}
        <form action={createCheckoutSession}>
          <input type="hidden" name="returnTo" value={returnTo} />
          <Button variant="primary" className="w-full" type="submit">
            Continue to checkout
          </Button>
        </form>
        <p className="mt-3 text-center text-xs text-ink-3">
          Already a member?{" "}
          <Link
            href={`/sign-in?callbackUrl=${encodeURIComponent(returnTo)}`}
            className="text-teal underline-offset-2 hover:underline"
          >
            Sign in
          </Link>
        </p>
      </DialogContent>
    </Dialog>
  );
}
