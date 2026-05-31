import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // PAYWALL CHOKE POINT (defense-in-depth alongside `import 'server-only'` + the
    // disjoint Free/Paid types). The raw-value query module may be imported ONLY by
    // the single access.ts choke point — nowhere else in the app.
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/server/metrics/queries", "@/server/metrics/queries"],
              message:
                "Raw metric_values access is restricted. Import from @/server/metrics/access (the single server-only choke point), never the queries module directly.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["src/server/metrics/access.ts"],
    rules: { "no-restricted-imports": "off" },
  },
];

export default eslintConfig;
