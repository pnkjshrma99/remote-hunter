"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getAnalyticsDashboard,
  getSourcePerformance,
  getMarketHeatmap,
  getSalaryInsights,
  getHiringTrends,
  getStats,
} from "@/lib/api";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Globe,
  DollarSign,
  Target,
  ExternalLink,
  Layers,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

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

  const { data: jobStats } = useQuery({
    queryKey: ["job-stats-analytics"],
    queryFn: getStats,
  });

  const maxTrendValue = Math.max(1, ...(hiringTrends?.trend_data?.map((item: any) => item.total_jobs) ?? [1]));
  const latestTrend = hiringTrends?.trend_data?.slice(-1)?.[0];
  const trendStart = hiringTrends?.trend_data?.[0];

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
    const growth = hiringTrends?.growth_rate_percent ?? 0;
    return { totalJobs, topSource, sourceCount, averageVerified, growth };
  }, [marketHeatmap, sourcePerformance, hiringTrends]);

  if (dashboardLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-lg font-semibold text-slate-700">Loading analytics…</p>
        </div>
      </div>
    );
  }

  // Progress bar colour helper
  const barColor = (val: number) => {
    if (val >= 80) return "bg-emerald-500";
    if (val >= 50) return "bg-amber-500";
    return "bg-rose-500";
  };

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 sm:py-8">
        {/* ===== HEADER ===== */}
        <div className="mb-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-sky-600 px-6 py-6 sm:px-8 sm:py-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div className="text-white">
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.28em] text-indigo-200">Analytics Dashboard</p>
                <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Remote hiring intelligence</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-indigo-100">
                  Source performance, market trends, and salary insights for remote job seekers.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-white/10 px-4 py-3 text-white backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-200">Refreshed</p>
                  <p className="mt-0.5 text-sm font-semibold">
                    {dashboard?.generated_at
                      ? new Date(dashboard.generated_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                      : "—"}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Metric cards row */}
          <div className="grid grid-cols-2 gap-px bg-slate-100 sm:grid-cols-4">
            <MetricTile icon={BarChart3} label="Active jobs" value={metrics.totalJobs} color="text-indigo-600" bg="bg-indigo-50" />
            <MetricTile icon={Layers} label="Sources tracked" value={metrics.sourceCount} color="text-emerald-600" bg="bg-emerald-50" />
            <MetricTile icon={CheckCircle2} label="Avg. verified" value={`${metrics.averageVerified}%`} color="text-violet-600" bg="bg-violet-50" />
            <MetricTile
              icon={metrics.growth >= 0 ? TrendingUp : TrendingDown}
              label="Growth rate"
              value={`${metrics.growth >= 0 ? "+" : ""}${metrics.growth}%`}
              color={metrics.growth >= 0 ? "text-emerald-600" : "text-rose-600"}
              bg={metrics.growth >= 0 ? "bg-emerald-50" : "bg-rose-50"}
            />
          </div>
        </div>

        {/* ===== MAIN GRID ===== */}
        <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          {/* --- SOURCE PERFORMANCE --- */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Source Performance</h2>
                <p className="mt-1 text-xs text-slate-500">Which boards deliver the best matches and quality.</p>
              </div>
              <span className="rounded-full bg-indigo-100 px-3 py-1 text-[11px] font-semibold text-indigo-700">
                Top: {metrics.topSource}
              </span>
            </div>
            {sourcePerformance && sourcePerformance.length > 0 ? (
              <div className="space-y-4">
                {sourcePerformance.map((source: any, idx: number) => {
                  const total = source.total_scraped || 1;
                  const matchW = Math.min((source.total_matched / total) * 100, 100);
                  const dupW = Math.min(source.duplicate_rate || 0, 100);
                  const verW = Math.min(source.verified_remote_rate || 0, 100);
                  return (
                    <div key={source.source} className="rounded-xl bg-slate-50 p-4 transition hover:bg-slate-100/60">
                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-500">#{idx + 1}</span>
                          <span className="text-sm font-semibold text-slate-800">{source.source}</span>
                        </div>
                        <span className="text-sm font-bold text-slate-900">{source.total_scraped}</span>
                      </div>
                      <div className="space-y-1.5">
                        {/* Match rate */}
                        <div className="flex items-center gap-2 text-[11px]">
                          <span className="w-16 text-slate-400">Match</span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                            <div className={`h-full rounded-full ${barColor(matchW)} transition-all`} style={{ width: `${matchW}%` }} />
                          </div>
                          <span className="w-10 text-right font-medium text-slate-600">{source.match_rate}%</span>
                        </div>
                        {/* Duplicate rate */}
                        <div className="flex items-center gap-2 text-[11px]">
                          <span className="w-16 text-slate-400">Dupes</span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                            <div className="h-full rounded-full bg-amber-400 transition-all" style={{ width: `${Math.min(dupW, 100)}%` }} />
                          </div>
                          <span className="w-10 text-right font-medium text-slate-600">{source.duplicate_rate}%</span>
                        </div>
                        {/* Verified remote rate */}
                        <div className="flex items-center gap-2 text-[11px]">
                          <span className="w-16 text-slate-400">Verified</span>
                          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                            <div className={`h-full rounded-full ${barColor(verW)} transition-all`} style={{ width: `${verW}%` }} />
                          </div>
                          <span className="w-10 text-right font-medium text-slate-600">{source.verified_remote_rate}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500">
                No source data yet. Run a scrape to populate.
              </div>
            )}
          </section>

          {/* --- RIGHT COLUMN --- */}
          <div className="space-y-6">
            {/* Hiring Trends */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">Hiring Trends</h2>
                  <p className="mt-1 text-xs text-slate-500">Remote job volume over time.</p>
                </div>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm outline-none"
                >
                  <option value={7}>7d</option>
                  <option value={30}>30d</option>
                  <option value={90}>90d</option>
                </select>
              </div>

              {/* Stat summary */}
              <div className="mb-4 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-gradient-to-br from-sky-50 to-white p-3 ring-1 ring-sky-100/50">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-sky-600">Total</p>
                  <p className="mt-1 text-xl font-bold text-slate-800">{hiringTrends?.total_jobs_in_period ?? 0}</p>
                </div>
                <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-white p-3 ring-1 ring-emerald-100/50">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">Growth</p>
                  <p className={`mt-1 text-xl font-bold ${(hiringTrends?.growth_rate_percent ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                    {hiringTrends?.growth_rate_percent >= 0 ? "+" : ""}{hiringTrends?.growth_rate_percent ?? 0}%
                  </p>
                </div>
                <div className="rounded-xl bg-gradient-to-br from-violet-50 to-white p-3 ring-1 ring-violet-100/50">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-600">Today</p>
                  <p className="mt-1 text-xl font-bold text-slate-800">{latestTrend?.total_jobs ?? 0}</p>
                </div>
                <div className="rounded-xl bg-gradient-to-br from-amber-50 to-white p-3 ring-1 ring-amber-100/50">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-600">Start</p>
                  <p className="mt-1 text-xl font-bold text-slate-800">{trendStart?.total_jobs ?? 0}</p>
                </div>
              </div>

              {/* Trend bar chart */}
              <div className="rounded-xl bg-slate-50 p-4">
                <div className="space-y-1.5 max-h-[240px] overflow-y-auto pr-1">
                  {hiringTrends?.trend_data?.slice(-21).map((trend: any) => {
                    const pct = Math.min((trend.total_jobs / maxTrendValue) * 100, 100);
                    const isToday = trend.date === new Date().toISOString().slice(0, 10);
                    return (
                      <div key={trend.date} className="flex items-center gap-2">
                        <span className={`w-20 text-[10px] ${isToday ? "font-semibold text-indigo-600" : "text-slate-400"}`}>
                          {formatTrendDate(trend.date)}
                        </span>
                        <div className="h-3.5 flex-1 overflow-hidden rounded-full bg-slate-200">
                          <div
                            className={`h-full rounded-full transition-all ${isToday ? "bg-indigo-500" : "bg-sky-400"}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className={`w-8 text-right text-[10px] font-medium ${isToday ? "text-indigo-600" : "text-slate-500"}`}>
                          {trend.total_jobs}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>

            {/* Market Heatmap compact */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-1 text-lg font-semibold text-slate-900">Market Heatmap</h2>
              <p className="mb-4 text-xs text-slate-500">Where remote jobs cluster across dimensions.</p>
              <div className="grid grid-cols-2 gap-3">
                <HeatBlock title="Region" data={marketHeatmap?.by_region} color="bg-indigo-500" />
                <HeatBlock title="Role" data={marketHeatmap?.by_role} color="bg-emerald-500" />
                <HeatBlock title="Company size" data={marketHeatmap?.by_company_size} color="bg-amber-500" />
                <HeatBlock title="Tech stack" data={marketHeatmap?.by_tech_stack} maxItems={4} color="bg-violet-500" />
              </div>
            </section>
          </div>
        </div>

        {/* ===== BOTTOM ROW: SALARY + EXTRA ===== */}
        <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          {/* Salary Insights */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Salary Insights</h2>
                <p className="mt-1 text-xs text-slate-500">Compensation by seniority, region, and company size.</p>
              </div>
              {salaryInsights?.overall_average && (
                <div className="rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 px-4 py-1.5 text-xs font-bold text-white shadow-sm">
                  Avg ${salaryInsights.overall_average.toLocaleString()}
                </div>
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <SalaryCard title="By Seniority" data={salaryInsights?.by_seniority} icon="👤" />
              <SalaryCard title="By Region" data={salaryInsights?.by_region} icon="🌍" />
              <SalaryCard title="By Company Size" data={salaryInsights?.by_company_size} icon="🏢" />
            </div>
            {!salaryInsights?.overall_average && (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-xs text-slate-400">
                Salary data will appear after jobs with salary info are scraped.
              </div>
            )}
          </section>

          {/* Quick stats / insights */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="mb-1 text-lg font-semibold text-slate-900">Quick Stats</h2>
            <p className="mb-4 text-xs text-slate-500">Overall job market summary.</p>
            <div className="space-y-3">
              <QuickStatRow label="Total jobs" value={jobStats?.total_jobs ?? marketHeatmap?.total_jobs ?? 0} />
              <QuickStatRow label="Applied" value={jobStats?.applied_count ?? 0} />
              <QuickStatRow label="New today" value={jobStats?.new_today ?? 0} />
              <QuickStatRow label="Sources" value={sourcePerformance?.length ?? 0} />
              <QuickStatRow label="With salary" value={salaryInsights?.total_with_salary ?? 0} />
              <div className="rounded-xl bg-gradient-to-r from-slate-50 to-indigo-50 p-4">
                <p className="text-xs font-medium text-slate-500">Top source</p>
                <p className="mt-1 text-lg font-bold text-indigo-600">{metrics.topSource}</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

// =========================================================================
// Sub-components
// =========================================================================

function MetricTile({ icon: Icon, label, value, color, bg }: { icon: any; label: string; value: string | number; color: string; bg: string }) {
  return (
    <div className="bg-white px-5 py-4">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${bg}`}>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</p>
          <p className="mt-0.5 text-xl font-bold text-slate-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

function HeatBlock({ title, data, color, maxItems = 4 }: { title: string; data?: Record<string, number>; color: string; maxItems?: number }) {
  const entries = data ? Object.entries(data).slice(0, maxItems) : [];
  const maxVal = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      <div className="space-y-1.5">
        {entries.map(([key, val]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-full truncate text-[10px] text-slate-500">{key}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-200">
              <div className={`h-full rounded-full ${color}`} style={{ width: `${(val / maxVal) * 100}%` }} />
            </div>
            <span className="w-6 text-right text-[10px] font-medium text-slate-700">{val}</span>
          </div>
        ))}
        {entries.length === 0 && <p className="text-[10px] text-slate-400">No data</p>}
      </div>
    </div>
  );
}

function SalaryCard({ title, data, icon }: { title: string; data?: Record<string, number | null>; icon: string }) {
  const entries = data ? Object.entries(data).filter(([, v]) => v !== null) : [];
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="text-base">{icon}</span>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      </div>
      <div className="space-y-2">
        {entries.slice(0, 5).map(([key, val]) => (
          <div key={key} className="flex items-center justify-between rounded-lg bg-white px-3 py-2 shadow-sm">
            <span className="text-xs capitalize text-slate-600">{key}</span>
            <span className="text-xs font-bold text-slate-800">${Number(val).toLocaleString()}</span>
          </div>
        ))}
        {entries.length === 0 && <p className="text-xs text-slate-400">—</p>}
      </div>
    </div>
  );
}

function QuickStatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2.5">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-semibold text-slate-800">{value}</span>
    </div>
  );
}

function formatTrendDate(dateStr: string) {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(d);
  } catch {
    return dateStr;
  }
}