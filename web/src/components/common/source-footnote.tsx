import type { Attribution } from "@/server/data/types";

/**
 * Tiny, text-only source attribution (DESIGN.md component #6) — shown on BOTH tiers
 * for license compliance (invariant #8). No clickable deep-links (D6). Renders nothing
 * until sources are recorded.
 */
export function SourceFootnote({ attributions }: { attributions: Attribution[] }) {
  if (attributions.length === 0) return null;
  return (
    <footer className="mt-8 border-t border-line pt-4 text-xs leading-relaxed text-ink-3">
      <p className="mb-1 font-medium text-ink-2">Sources</p>
      <ul className="space-y-0.5">
        {attributions.map((a, i) => (
          <li key={i}>
            {a.title ?? "Source"}
            {a.publicationDate ? ` (${a.publicationDate})` : ""}
            {a.license ? ` — ${a.license}` : ""}
            {a.retrievedAt ? `, retrieved ${a.retrievedAt.slice(0, 10)}` : ""}
          </li>
        ))}
      </ul>
      <p className="mt-2">Ranks computed from these figures; nothing estimated.</p>
    </footer>
  );
}
