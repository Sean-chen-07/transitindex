import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { signIn } from "@/server/auth";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to TransitIndex to open the full data.",
};

// Server-rendered. The two forms post to server actions that call Auth.js signIn — no
// client JS, no password. callbackUrl is where Auth.js returns the visitor after sign-in
// (defaults to the membership area).
export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const { callbackUrl } = await searchParams;
  const redirectTo = callbackUrl ?? "/account";

  return (
    <main className="mx-auto max-w-md">
      <nav className="mb-4 text-sm">
        <Link href="/" className="text-teal underline-offset-2 hover:underline">
          ← All agencies
        </Link>
      </nav>

      <header className="mb-6">
        <h1 className="text-3xl font-extrabold text-ink">Sign in</h1>
        <p className="mt-1 text-ink-2">
          New here or coming back — the same link signs you in. No password to remember.
        </p>
      </header>

      <div className="rounded-card border border-line bg-card p-6">
        <form
          action={async (formData) => {
            "use server";
            const email = formData.get("email") as string;
            await signIn("resend", { email, redirectTo });
          }}
          className="flex flex-col gap-3"
        >
          <label htmlFor="email" className="text-sm font-medium text-ink">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@city.ca"
            className="min-h-[44px] rounded-full border border-line bg-card px-4 py-2 text-sm text-ink placeholder:text-ink-3"
          />
          <Button type="submit" variant="primary" className="w-full">
            Email me a sign-in link
          </Button>
          <p className="text-xs text-ink-3">
            We&apos;ll email you a secure sign-in link — no password. The link works once
            and expires shortly.
          </p>
        </form>

        <div className="my-5 flex items-center gap-3 text-xs text-ink-3">
          <span className="h-px flex-1 bg-line" />
          or
          <span className="h-px flex-1 bg-line" />
        </div>

        <form
          action={async () => {
            "use server";
            await signIn("google", { redirectTo });
          }}
        >
          <Button type="submit" variant="outline" className="w-full">
            Continue with Google
          </Button>
        </form>
      </div>
    </main>
  );
}
