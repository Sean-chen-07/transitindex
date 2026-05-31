import Link from "next/link";
import { cn } from "@/lib/cn";
import type { FeedFreshness } from "@/server/data/types";

/** Pending: no metric sourced yet for this agency (the seed-only default). */
export function PendingNotice({ slug }: { slug: string }) {
  return (
    <div className="rounded-card border border-dashed border-line-2 bg-card-2 p-4 text-sm text-ink-2">
      <p className="font-medium text-ink">Fundamentals pending</p>
      <p className="mt-1">
        We haven&apos;t sourced this agency&apos;s numbers yet.{" "}
        <Link href={`/agency/${slug}`} className="text-teal underline-offset-2 hover:underline">
          Request this agency →
        </Link>
      </p>
    </div>
  );
}

/** A single metric that exists for some agencies but isn't sourced for this one. */
export function NotSourced({ label }: { label: string }) {
  return (
    <span className="text-sm text-ink-3">
      {label}: <span className="italic">— not yet sourced</span>
    </span>
  );
}

/** Honest freshness banner. Tolerates zero runs (neutral "being sourced"). */
export function FreshnessBanner({ feeds }: { feeds: FeedFreshness[] }) {
  const anyGood = feeds.some((f) => f.lastGoodAt);
  if (!anyGood) {
    return (
      <p className="text-xs text-ink-3">
        Data is being sourced. Ranks appear here as each agency&apos;s figures land.
      </p>
    );
  }
  return null;
}

export function ErrorNotice({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-card border border-line bg-card-2 p-4 text-sm text-ink-2",
        className,
      )}
      role="status"
    >
      Data temporarily unavailable. Please try again shortly.
    </div>
  );
}

export function EmptySearch({ query }: { query: string }) {
  return (
    <p className="py-8 text-center text-ink-2">
      No agency matches &ldquo;{query}&rdquo;. Browse by province below ↓
    </p>
  );
}
