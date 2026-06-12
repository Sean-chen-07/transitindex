import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <p className="text-sm font-medium uppercase tracking-wide text-ink-3">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink">
        We don&apos;t have a page by that name
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-ink-2">
        The agency or page you&apos;re looking for isn&apos;t in the index. It may have
        moved, or the link may be out of date.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex min-h-[44px] items-center justify-center rounded-full bg-coral px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-coral/90"
      >
        Back to the directory
      </Link>
    </div>
  );
}
