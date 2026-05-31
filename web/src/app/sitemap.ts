import type { MetadataRoute } from "next";
import { listAgencies } from "@/server/data/agencies";

// Reads ONLY the free data layer (slugs) — never a metric value.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  const groups = await listAgencies();
  const agencyUrls = groups.flatMap((g) =>
    g.agencies.map((a) => ({
      url: `${base}/agency/${a.slug}`,
      changeFrequency: "monthly" as const,
    })),
  );
  return [{ url: base, changeFrequency: "daily" as const }, ...agencyUrls];
}
