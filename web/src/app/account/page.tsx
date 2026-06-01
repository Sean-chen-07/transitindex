import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { eq } from "drizzle-orm";
import { db } from "@/server/db";
import { users } from "@/db/schema";
import { getSession } from "@/server/entitlement";
import { createCheckoutSession, createBillingPortalSession } from "@/server/billing/checkout";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Your membership",
  description: "Manage your TransitIndex membership.",
};

// force-dynamic: subscription_status is read LIVE per request (a cancelled member must lose
// access immediately), so this page must never be statically cached.
export const dynamic = "force-dynamic";

export default async function AccountPage({
  searchParams,
}: {
  searchParams: Promise<{ checkout?: string }>;
}) {
  const session = await getSession();
  if (!session?.userId) redirect("/sign-in?callbackUrl=/account");

  const { checkout } = await searchParams;
  const [user] = await db
    .select({ status: users.subscriptionStatus, email: users.email })
    .from(users)
    .where(eq(users.id, session.userId));

  // Single definition of "entitled", matching isPaid(): the webhook folds a Stripe trial
  // into 'active', so the column only ever holds 'active' for a paid/trialing member.
  const active = user?.status === "active";

  return (
    <main className="mx-auto max-w-md">
      <nav className="mb-4 text-sm">
        <Link href="/" className="text-teal underline-offset-2 hover:underline">
          ← All agencies
        </Link>
      </nav>

      <header className="mb-6">
        <h1 className="text-3xl font-extrabold text-ink">Your membership</h1>
        <p className="mt-1 text-ink-2">{user?.email}</p>
      </header>

      {checkout === "success" && (
        <div className="mb-6 rounded-card border border-teal/40 bg-teal-soft p-4 text-sm text-ink">
          You&apos;re in — thanks for joining. Every raw figure is now unlocked.
        </div>
      )}
      {checkout === "cancel" && (
        <div className="mb-6 rounded-card border border-line bg-card-2 p-4 text-sm text-ink-2">
          No charge was made. You can subscribe whenever you&apos;re ready.
        </div>
      )}

      {active ? (
        <div className="rounded-card border border-line bg-card p-6">
          <p className="font-semibold text-ink">Membership active</p>
          <p className="mb-4 mt-1 text-sm text-ink-2">
            Every raw figure, reporting period, and source is unlocked across all agencies.
          </p>
          <form
            action={async () => {
              "use server";
              await createBillingPortalSession();
            }}
          >
            <Button type="submit" variant="outline" className="w-full">
              Manage billing
            </Button>
          </form>
        </div>
      ) : (
        <div className="rounded-card border border-line bg-card p-6">
          <p className="font-semibold text-ink">Open the full data — $20/year</p>
          <p className="mb-4 mt-1 text-sm text-ink-2">
            Ranks are always free. A membership unlocks every raw figure, its reporting
            period, and the exact source — for all agencies.
          </p>
          <form
            action={async () => {
              "use server";
              await createCheckoutSession();
            }}
          >
            <Button type="submit" variant="primary" className="w-full">
              Subscribe — $20/year
            </Button>
          </form>
        </div>
      )}
    </main>
  );
}
