"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { requestAgency } from "@/app/actions/request-agency";

/**
 * "Request this agency" — logs demand on pending detail pages (agency + optional email).
 * Calls the server action, which accepts only these fields and never returns a value.
 */
export function RequestAgencyForm({ agencyId }: { agencyId: number }) {
  const [email, setEmail] = React.useState("");
  const [done, setDone] = React.useState(false);
  const [pending, setPending] = React.useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    const res = await requestAgency({ agencyId, email: email || undefined });
    setPending(false);
    if (res.ok) setDone(true);
  }

  if (done) {
    return (
      <p className="text-sm text-teal" role="status">
        Thanks — we&apos;ll prioritize sourcing this agency.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email (optional) — to hear when it lands"
        aria-label="Email to be notified"
        className="min-h-[44px] flex-1 rounded-full border border-line bg-card px-4 py-2 text-sm text-ink placeholder:text-ink-3"
      />
      <Button type="submit" variant="teal" disabled={pending}>
        {pending ? "Sending…" : "Request this agency"}
      </Button>
    </form>
  );
}
