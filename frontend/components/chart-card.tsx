"use client";

import dynamic from "next/dynamic";
import type { Data } from "plotly.js";

const Plot = dynamic(() => import("react-plotly.js").then((mod) => mod.default), {
  ssr: false
});

type Props = {
  title: string;
  values: Record<string, number>;
  type?: "bar" | "pie" | "line";
};

export function ChartCard({ title, values, type = "bar" }: Props) {
  const labels = Object.keys(values);
  const nums = Object.values(values);
  const hasData = nums.some((value) => value > 0);
  const data: Data[] =
    type === "pie"
      ? [{ type: "pie" as const, labels, values: nums, hole: 0.45, marker: { colors: ["#2f6f5e", "#c95b45", "#2f6db5", "#d59f2f", "#755caa"] } }]
      : [
          {
            type: type === "line" ? "scatter" : "bar",
            x: labels,
            y: nums,
            mode: type === "line" ? "lines+markers" : undefined,
            marker: { color: "#2f6f5e" }
          }
        ];

  return (
    <section className="min-h-[260px] rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      {hasData ? (
        <Plot
          data={data}
          layout={{
            autosize: true,
            margin: { l: 36, r: 14, t: 16, b: 46 },
            paper_bgcolor: "white",
            plot_bgcolor: "white",
            font: { family: "Inter, sans-serif", size: 11, color: "#172126" },
            showlegend: type === "pie"
          }}
          config={{ displayModeBar: false, responsive: true }}
          className="h-[220px] w-full"
          useResizeHandler
        />
      ) : (
        <div className="flex h-[220px] items-center justify-center text-sm text-stone-500">
          No chart data yet
        </div>
      )}
    </section>
  );
}
