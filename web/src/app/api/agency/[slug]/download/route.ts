import { NextResponse } from "next/server";
import { getAgencySummary } from "@/server/data/agencies";
import { getSession, isPaid } from "@/server/entitlement";
import { getDetailMetrics } from "@/server/metrics/access";
import { buildDetailModel } from "@/server/metrics/detail-model";
import { financialsToCsv } from "@/server/metrics/csv";

// THE MONEY GATE (viewing is free; the paid artifact is this per-agency CSV).
// Entitlement is checked LIVE per request — the real session + isPaid (which reads
// subscription_status from the DB), never a cached or caller-supplied flag.
export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ slug: string }> },
): Promise<Response> {
  const { slug } = await params;

  const summary = await getAgencySummary(slug);
  if (!summary) return new Response("Unknown agency.", { status: 404 });

  const session = await getSession();
  if (!session?.userId) {
    return NextResponse.redirect(
      new URL("/sign-in?callbackUrl=" + encodeURIComponent("/agency/" + slug), req.url),
    );
  }
  if (!(await isPaid(session))) {
    return new Response("A membership is required to download data.", { status: 403 });
  }

  const metrics = await getDetailMetrics(slug);
  const csv = financialsToCsv(buildDetailModel(metrics).financials);
  return new Response(csv, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${slug}-financials.csv"`,
      "Cache-Control": "no-store",
    },
  });
}
