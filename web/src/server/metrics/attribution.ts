/**
 * Required attribution text by source license (invariant #8 — shown on BOTH tiers).
 * The StatCan notice follows Statistics Canada's open-licence wording; the municipal
 * Open Government Licence lines are sensible defaults to refine against
 * ../../source-registry.md before the first public render carrying that source.
 */
const ATTRIBUTION: Record<string, string> = {
  statcan_open:
    "Source: Statistics Canada, Table 23-10-0307. Adapted from Statistics Canada, used under the Statistics Canada Open Licence.",
  ogl_toronto: "Contains information licensed under the Open Government Licence – Toronto.",
  ogl_ottawa: "Contains information licensed under the Open Government Licence – Ottawa.",
  ogl_calgary: "Contains information licensed under the Open Government Licence – Calgary.",
  ogl_edmonton: "Contains information licensed under the Open Government Licence – Edmonton.",
  ogl_montreal: "Contains information licensed under the Open Government Licence – Montréal.",
  ogl_metrovancouver:
    "Contains information licensed under the Open Government Licence – Metro Vancouver.",
  ogl_mississauga:
    "Contains information licensed under the Open Government Licence – Mississauga.",
  public_document: "Source: agency public document. Facts compiled and cited by TransitIndex.",
};

export function licenseToAttribution(license: string | null): string {
  if (!license) return "Source cited on the agency page.";
  return ATTRIBUTION[license] ?? "Source cited on the agency page.";
}
