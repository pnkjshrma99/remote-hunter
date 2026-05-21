"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getAnalyticsDashboard,
  getSourcePerformance,
  getMarketHeatmap,
  getSalaryInsights,
  getHiringTrends,
} from "@/lib/api";

export default function AnalyticsDashboard() {
  const [days, setDays] = useState(30);

  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ["analytics-dashboard"],
    queryFn: getAnalyticsDashboard,
  });

  const { data: sourcePerformance } = useQuery({
    queryKey: ["source-performance"],
    queryFn: getSourcePerformance,
  });

  const { data: marketHeatmap } = useQuery({
    queryKey: ["market-heatmap"],
    queryFn: getMarketHeatmap,
  });

  const { data: salaryInsights } = useQuery({
    queryKey: ["salary-insights"],
    queryFn: getSalaryInsights,
  });

  const { data: hiringTrends } = useQuery({
    queryKey: ["hiring-trends", days],
    queryFn: () => getHiringTrends(days),
  });

  const metrics = useMemo(() => {
    const totalJobs = marketHeatmap?.total_jobs ?? 0;
    const topSource = sourcePerformance?.[0]?.source ?? "—";
    const sourceCount = sourcePerformance?.length ?? 0;
    const averageVerified = sourcePerformance?.length
      ? Number(
          (
            sourcePerformance.reduce((sum: number, item: any) => sum + (item.verified_remote_rate ?? 0), 0) /
            sourcePerformance.length
          ).toFixed(1)
        )
      : 0;

    return { totalJobs, topSource, sourceCount, averageVerified };
  }, [marketHeatmap, sourcePerformance]);

  if (dashboardLoading) {
    return (
      <div className="min-h-screen bg-paper py-20">
        <div className="mx-auto max-w-4xl rounded-[2rem] border border-slate-200 bg-white p-12 text-center shadow-[0_25px_80px_-48px_rgba(15,23,42,0.18)]">
          <p className="text-xl font-semibold text-stone-700">Loading analytics dashboard…</p>
        </div>
      </div>
    );
  }

  const maxTrendValue = Math.max(1, ...(hiringTrends?.trend_data?.map((item: any) => item.total_jobs) ?? [1]));

  return (
    <main className="min-h-screen bg-paper py-10">
      <div className="mx-auto max-w-[1500px] px-5">
        <div className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-sky-50 p-8 shadow-[0_25px_80px_-48px_rgba(15,23,42,0.18)]">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">Analytics Dashboard</p>
              <h1 className="mt-4 text-4xl font-bold tracking-tight text-ink">Remote hiring performance overview</h1>
              <p className="mt-3 text-base leading-7 text-stone-600">
                Monitor source health, market dynamics, and compensation insights with a dashboard built for serious remote job hunters.
              </p>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
              <p className="text-xs uppercase tracking-[0.24em] text-stone-500">Last refreshed</p>
              <p className="mt-2 text-sm font-semibold text-ink">{dashboard?.generated_at ? new Date(dashboard.generated_at).toLocaleString() : "—"}</p>
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Active jobs" value={metrics.totalJobs} variant="active" />
          <MetricCard label="Tracked sources" value={metrics.sourceCount} variant="sources" />
          <MetricCard label="Verified remote avg." value={`${metrics.averageVerified}%`} variant="verified" />
          <MetricCard label="Top source" value={metrics.topSource} variant="top" />
        </div>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
          <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[0_25px_80px_-48px_rgba(15,23,42,0.18)]">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Source Performance</h2>
                <p className="mt-2 text-sm text-stone-600">Find the highest performing boards and duplicate-heavy sources at a glance.</p>
              </div>
              <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-700">
                {metrics.topSource}
              </span>
            </div>
            {sourcePerformance ? (
              <div className="overflow-x-auto rounded-[1.5rem] border border-slate-100 bg-slate-50">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-white text-slate-500">
                    <tr>
                      <th className="px-4 py-4">Source</th>
                      <th className="px-4 py-4 text-right">Scraped</th>
                      <th className="px-4 py-4 text-right">Match</th>
                      <th className="px-4 py-4 text-right">Duplicate</th>
                      <th className="px-4 py-4 text-right">Verified</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourcePerformance.map((source: any) => (
                      <tr key={source.source} className="border-t border-slate-100 hover:bg-white/80">
                        <td className="px-4 py-4 font-medium text-ink">{source.source}</td>
                        <td className="px-4 py-4 text-right text-slate-600">{source.total_scraped}</td>
                        <td className="px-4 py-4 text-right text-slate-600">{source.match_rate}%</td>
                        <td className="px-4 py-4 text-right text-slate-600">{source.duplicate_rate}%</td>
                        <td className="px-4 py-4 text-right text-slate-600">{source.verified_remote_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-[1.5rem] border border-slate-100 bg-slate-50 p-6 text-sm text-stone-600">No source performance data available yet.</div>
            )}
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-sky-50 p-6 shadow-[0_25px_80px_-48px_rgba(15,23,42,0.18)]">
            <h2 className="text-2xl font-semibold text-ink">Market heatmap</h2>
            <p className="mt-2 text-sm text-stone-600">Heatmap of where remote matches cluster across the market.</p>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <HeatmapCard title="Region" data={marketHeatmap?.by_region} />
              <HeatmapCard title="Role" data={marketHeatmap?.by_role} />
              <HeatmapCard title="Company size" data={marketHeatmap?.by_company_size} />
              <HeatmapCard title="Tech stack" data={marketHeatmap?.by_tech_stack} maxEntries={6} />
            </div>
          </section>
        </div>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
          <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[0_25px_80px_-48px_rgba(15,23,42,0.18)]">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Salary Insights</h2>
                <p className="mt-2 text-sm text-stone-600">Compensation patterns for seniority, location, and company size.</p>
              </div>
              {salaryInsights?.overall_average ? (
                <div className="rounded-full bg-sky-100 px-4 py-2 text-sm font-semibold text-sky-800">
                  Avg. ${salaryInsights.overall_average}
                </div>
              ) : null}
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <InsightCard title="Seniority" data={salaryInsights?.by_seniority} />
              <InsightCard title="Region" data={salaryInsights?.by_region} />
              <InsightCard title="Company size" data={salaryInsights?.by_company_size} />
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-cyan-50 p-6 shadow-[0_25px_80px_-48px_rgba(15,23,42,0.18)]">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Hiring Trends</h2>
                <p className="mt-2 text-sm text-stone-600">The latest direction of remote hiring demand.</p>
              </div>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm shadow-sm outline-none"
              >
                <option value={7}>7 days</option>
                <option value={30}>30 days</option>
                <option value={90}>90 days</option>
              </select>
            </div>
            <div className="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-5">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-sm text-stone-600">
                <div>
                  <p>Total jobs: <span className="font-semibold text-ink">{hiringTrends?.total_jobs_in_period ?? 0}</span></p>
                </div>
                <div className={
                  `rounded-full px-3 py-1 text-xs font-semibold ${
                    hiringTrends?.growth_rate_percent >= 0 ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                  }`
                }>
                  {hiringTrends?.growth_rate_percent >= 0 ? "+" : ""}{hiringTrends?.growth_rate_percent ?? 0}% growth
                </div>
              </div>
              <div className="space-y-3 max-h-[340px] overflow-y-auto">
                {hiringTrends?.trend_data?.map((trend: any) => (
                  <div key={trend.date} className="rounded-3xl bg-white p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-ink">{trend.date}</span>
                      <span className="text-sm font-semibold text-slate-700">{trend.total_jobs}</span>
                    </div>
                    <div className="mt-3 h-3 rounded-full bg-slate-200">
                      <div
                        className="h-3 rounded-full bg-sky-500"
                        style={{ width: `${Math.min((trend.total_jobs / maxTrendValue) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function MetricCard({ label, value, variant }: { label: string; value: string | number; variant: "active" | "sources" | "verified" | "top" }) {
  const accentClass = {
    active: "bg-[#0ea5e9] text-white shadow-[0_22px_80px_-50px_rgba(56,189,248,0.35)]",
    sources: "bg-gradient-to-br from-emerald-500 to-sky-500 text-white shadow-[0_22px_80px_-50px_rgba(16,185,129,0.25)]",
    verified: "bg-gradient-to-br from-violet-500 to-sky-500 text-white shadow-[0_22px_80px_-50px_rgba(139,92,246,0.25)]",
    top: "bg-gradient-to-br from-amber-500 to-orange-500 text-white shadow-[0_22px_80px_-50px_rgba(251,191,36,0.25)]",
  }[variant];

  return (
    <div className={`rounded-[1.75rem] border border-slate-200 p-6 ${accentClass}`}>
      <p className="text-xs uppercase tracking-[0.24em] text-white/80">{label}</p>
      <p className="mt-4 text-3xl font-semibold">{value}</p>
    </div>
  );
}

function HeatmapCard({ title, data, maxEntries = 5 }: { title: string; data?: Record<string, number>; maxEntries?: number }) {
  return (
    <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-ink mb-4">{title}</h3>
      <div className="space-y-3">
        {data ? (
          Object.entries(data).slice(0, maxEntries).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
              <span className="text-sm text-stone-700">{key}</span>
              <span className="text-sm font-semibold text-ink">{value}</span>
            </div>
          ))
        ) : (
          <p className="text-sm text-stone-500">No data available.</p>
        )}
      </div>
    </div>
  );
}

function InsightCard({ title, data }: { title: string; data?: Record<string, number> }) {
  return (
    <div className="rounded-[1.75rem] border border-slate-200 bg-slate-50 p-5 shadow-sm">
      <h4 className="text-sm font-semibold text-stone-800 mb-4">{title}</h4>
      <div className="space-y-3 text-sm text-stone-700">
        {data ? (
          Object.entries(data).map(([key, value]) => (
            <div key={key} className="flex justify-between rounded-2xl bg-white px-4 py-3 shadow-sm">
              <span className="capitalize">{key}</span>
              <span className="font-semibold">${value}</span>
            </div>
          ))
        ) : (
          <p className="text-stone-500">No insight available.</p>
        )}
      </div>
    </div>
  );
}
