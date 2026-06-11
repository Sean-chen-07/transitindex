import { ImageResponse } from "next/og";

// Static social-share card (1200x630). Brand colours mirror DESIGN.md tokens.
export const alt = "TransitIndex — Canadian transit agency fundamentals";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  const bar = (h: number) => ({
    width: "14px",
    height: `${h}px`,
    borderRadius: "4px",
    background: "#fbf9f4",
  });

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#f4f0e7",
          padding: "80px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "26px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: "9px",
              width: "108px",
              height: "108px",
              borderRadius: "24px",
              background: "#e2725b",
              padding: "26px",
            }}
          >
            <div style={bar(24)} />
            <div style={bar(40)} />
            <div style={bar(56)} />
          </div>
          <div style={{ fontSize: "46px", fontWeight: 700, color: "#2e2c28" }}>
            TransitIndex
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div
            style={{
              fontSize: "70px",
              fontWeight: 800,
              color: "#2e2c28",
              lineHeight: 1.08,
              letterSpacing: "-2px",
            }}
          >
            Every Canadian transit agency, ranked on the fundamentals.
          </div>
          <div style={{ fontSize: "32px", color: "#5f5b52" }}>
            Every rank and every number, free to view.
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
