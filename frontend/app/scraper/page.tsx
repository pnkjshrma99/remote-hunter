"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApplyHelper } from "@/components/apply-helper";
import { ChartCard } from "@/components/chart-card";
import { JobTable } from "@/components/job-table";
import {
  getJobProfiles,
  getJobs,
  getStats,
  runScrape,
  ScrapeConfig
} from "@/lib/api";
import type { ScrapeResult } from "@/lib/api";
import type { Job, JobProfile, JobStats } from "@/types/job";

const sourceOptions = [
  { id: "remotive", label: "Remotive" },
  { id: "remoteok", label: "Remote OK" },
  { id: "weworkremotely", label: "WWR" },
  { id: "workingnomads", label: "Working Nomads" },
  { id: "himalayas", label: "Himalayas" },
  { id: "jobicy", label: "Jobicy" },
  { id: "jobspresso", label: "Jobspresso" },
  { id: "greenhouse", label: "Greenhouse" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "arbeitnow", label: "ArbeitNow" },
  { id: "stackoverflow", label: "Stack Overflow" },
  { id: "angellist", label: "AngelList" },
  { id: "justremote", label: "JustRemote" },
  { id: "nofluffjobs", label: "No Fluff Jobs" }
];

const DEFAULT_SOURCE_IDS = sourceOptions.map((source) => source.id);

const SENIORITY_OPTIONS = [
  { value: "", label: "All levels" },
  { value: "Junior", label: "Junior" },
  { value: "Mid-Level", label: "Mid-Level" },
  { value: "Senior", label: "Senior" },
  { value: "Lead", label: "Lead / Principal" }
];

/** Strip parentheses and seniority text from profile names */
function cleanProfileName(name: string): string {
  return name.replace(/\s*\((Junior|Mid-Level|Senior|Lead)\)/, "").trim();
}

/** Get unique base profile names (deduplicated) */
function getUniqueBaseProfiles(profiles: JobProfile[]): { display: string; original: string; id: string }[] {
  const seen = new Set<string>();
  const result: { display: string; original: string; id: string }[] = [];
  for (const p of profiles) {
    const base = cleanProfileName(p.name);
    if (!seen.has(base)) {
      seen.add(base);
      result.push({ display: base, original: p.name, id: p.id });
    }
  }
  return result;
}

export default function ScraperPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const queryClient = useQueryClient();

  const [seniority, setSeniority] = useState("");
  const [scrapeConfig, setScrapeConfig] = useState<ScrapeConfig>({
    query: "DevOps Engineer",
    job_profile_id: undefined,
    min_experience: 0,
    max_experience: 2,
    posted_within_days: 14,
    remote_only: true,
    global_or_india: true,
    exclude_indian_hq: true,
    strict_experience: false,
    strict_title: true,
    strict_junior: false,
    send_alerts: false,
    sources: DEFAULT_SOURCE_IDS,
    linkedin_urls: []
  });

  const [filters, setFilters] = useState({
    search: "",
    tech_stack: "",
    company_size: "",
    is_applied: ""
  });
  const [result, setResult] = useState<any | null>(null);

  const jobsQuery = useQuery<Job[], Error>({
    queryKey: ["jobs", user?.id, filters],
    queryFn: () => getJobs(filters),
    enabled: isAuthenticated
  });

  const statsQuery = useQuery<JobStats, Error>({
    queryKey: ["stats", user?.id],
    queryFn: () => getStats(),
    enabled: isAuthenticated
  });

  const profilesQuery = useQuery<JobProfile[], Error>({
    queryKey: ["job-profiles"],
    queryFn: () => getJobProfiles()
  });

  const stackOptions = useMemo(() => ["", ...Object.keys(statsQuery.data?.by_tech_stack ?? {})], [statsQuery.data]);
  const sizeOptions = useMemo(() => ["", ...Object.keys(statsQuery.data?.by_company_size ?? {})], [statsQuery.data]);

  /** Get deduplicated base profile names for the dropdown */
  const baseProfiles = useMemo(
    () => profilesQuery.data ? getUniqueBaseProfiles(profilesQuery.data) : [],
    [profilesQuery.data]
  );

  const selectProfile = (profile: JobProfile) => {
    setScrapeConfig((prev) => ({
      ...prev,
      job_profile_id: profile.id,
      query: profile.name,
      min_experience: profile.min_experience,
      max_experience: profile.max_experience
    }));
  };

  /** Select a base profile by its clean name */
  const selectBaseProfile = (cleanName: string) => {
    // Find the matching profile (prefer first match)
    const matched = profilesQuery.data?.find(
      (p) => cleanProfileName(p.name) === cleanName
    );
    if (matched) {
      selectProfile(matched);
    }
  };

  const scrapeMutation = useMutation<ScrapeResult, Error, void>({
    mutationFn: () => {
      // Build query with seniority prefix
      const baseQuery = scrapeConfig.query;
      const finalQuery = seniority
        ? `${seniority} ${baseQuery}`
        : baseQuery;
      return runScrape({
        ...scrapeConfig,
        query: finalQuery,
        linkedin_urls: []
      });
    },
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["jobs", user?.id] });
      queryClient.invalidateQueries({ queryKey: ["stats", user?.id] });
    }
  });

  const jobs = jobsQuery.data ?? [];
  const stats = statsQuery.data;

  const activeSources = useMemo(
    () => Object.entries(stats?.by_source ?? {}).sort(([, a], [, b]) => b - a),
    [stats]
  );

  const appliedRate = useMemo(() => {
    if (!stats?.total_jobs) return "0%";
    return `${Math.round((stats.applied_count / stats.total_jobs) * 100)}%`;
  }, [stats]);

  const setFilterValue = (key: keyof typeof filters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const toggleSource = (sourceId: string) => {
    setScrapeConfig((current) => ({
      ...current,
      sources: current.sources.includes(sourceId)
        ? current.sources.filter((id) => id !== sourceId)
        : [...current.sources, sourceId]
    }));
  };

  const selectAllSources = () => {
    setScrapeConfig((current) => ({ ...current, sources: DEFAULT_SOURCE_IDS }));
  };

  const deselectAllSources = () => {
    setScrapeConfig((current) => ({ ...current, sources: [] }));
  };

  const runScrapeHandler = async () => {
    scrapeMutation.mutate();
  };

  if (isLoading) {
    return <div className="p-8">Checking authentication...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-lg border border-slate-200 text-center">
          <h2 className="text-2xl font-semibold text-slate-900 mb-4">Sign in to access the scraper workspace</h2>
          <p className="text-sm text-slate-600 mb-6">
            Run searches, review job analytics, and track remote opportunities after signing in.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Link href={`/login?next=${encodeURIComponent("/scraper")}`} className="rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">
              Sign in
            </Link>
            <Link href={`/register?next=${encodeURIComponent("/scraper")}`} className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              Create account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-[1500px] px-5 py-8">
        <div className="mb-8 flex flex-col gap-4 rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-indigo-600">Scraper workspace</p>
            <h1 className="text-4xl font-bold tracking-tight text-slate-950">Search, analyze, and apply to remote jobs from one place.</h1>
            <p className="max-w-2xl text-sm leading-7 text-slate-600">
              Configure your scraper, run remote searches, and explore job analytics with dynamic stack filters and live source insights.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <Link href="/analytics" className="inline-flex min-w-[150px] items-center justify-center whitespace-nowrap rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              Analytics dashboard
            </Link>
            <Link href="/" className="inline-flex min-w-[150px] items-center justify-center whitespace-nowrap rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              Home
            </Link>
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-[420px_1fr]">
          <aside className="space-y-6">
            <div className="space-y-6">
              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-950">Scrape config</h2>
                <p className="mt-2 text-sm text-slate-600">Set your search criteria for remote jobs and run a fresh scrape.</p>

                <div className="mt-6 space-y-5">
                  {/* Seniority level - prepends to query when scraping */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Seniority level</label>
                    <select
                      value={seniority}
                      onChange={(e) => setSeniority(e.target.value)}
                      className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    >
                      {SENIORITY_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <p className="mt-1.5 text-xs text-slate-400">
                      Selected level will be included in the scrape query (e.g. "Junior DevOps Engineer").
                    </p>
                  </div>

                  {/* Job title / keywords - clean names without (Junior) / (Senior) etc. */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Job title / keywords</label>
                    <div className="relative mt-2">
                      <select
                        value={cleanProfileName(scrapeConfig.query)}
                        onChange={(e) => {
                          if (e.target.value) {
                            selectBaseProfile(e.target.value);
                          } else {
                            setScrapeConfig({ ...scrapeConfig, query: "", job_profile_id: undefined });
                          }
                        }}
                        className="w-full appearance-none rounded-2xl border border-slate-300 bg-white px-4 py-3 pr-10 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                      >
                        <option value="">Select a job role...</option>
                        {baseProfiles.map((bp) => (
                          <option key={bp.id} value={bp.display}>
                            {bp.display}
                          </option>
                        ))}
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-slate-500">
                        <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20"><path d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" /></svg>
                      </div>
                    </div>
                    <p className="mt-1.5 text-xs text-slate-400">Or type a custom search term below</p>
                    <input
                      type="text"
                      value={scrapeConfig.query}
                      onChange={(e) => setScrapeConfig({ ...scrapeConfig, query: e.target.value, job_profile_id: undefined })}
                      placeholder="DevOps Engineer"
                      className="mt-1 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    />
                  </div>

                  {/* Experience */}
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Min years
                      <input
                        type="number"
                        value={scrapeConfig.min_experience ?? 0}
                        onChange={(e) => setScrapeConfig({ ...scrapeConfig, min_experience: Number(e.target.value) })}
                        className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                      />
                    </label>
                    <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Max years
                      <input
                        type="number"
                        value={scrapeConfig.max_experience ?? 0}
                        onChange={(e) => setScrapeConfig({ ...scrapeConfig, max_experience: Number(e.target.value) })}
                        className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                      />
                    </label>
                  </div>

                  {/* Posted within days */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Posted within days</label>
                    <input
                      type="number"
                      value={scrapeConfig.posted_within_days ?? 14}
                      onChange={(e) => setScrapeConfig({ ...scrapeConfig, posted_within_days: Number(e.target.value) })}
                      className="mt-2 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    />
                  </div>

                  {/* Filters row 1 */}
                  <div className="grid grid-cols-2 gap-3">
                    <label className="flex items-center gap-2 rounded-2xl border border-slate-300 px-3 py-3 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={scrapeConfig.remote_only}
                        onChange={(e) => setScrapeConfig({ ...scrapeConfig, remote_only: e.target.checked })}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                      />
                      Remote only
                    </label>
                    <label className="flex items-center gap-2 rounded-2xl border border-slate-300 px-3 py-3 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={scrapeConfig.global_or_india}
                        onChange={(e) => setScrapeConfig({ ...scrapeConfig, global_or_india: e.target.checked })}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                      />
                      Remote eligible globally
                    </label>
                  </div>

                  {/* Filters row 2 */}
                  <div className="grid grid-cols-2 gap-3">
                    <label className="flex items-center gap-2 rounded-2xl border border-slate-300 px-3 py-3 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={scrapeConfig.exclude_indian_hq}
                        onChange={(e) => setScrapeConfig({ ...scrapeConfig, exclude_indian_hq: e.target.checked })}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                      />
                      Exclude IN HQ
                    </label>
                    <label className="flex items-center gap-2 rounded-2xl border border-slate-300 px-3 py-3 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={scrapeConfig.strict_title}
                        onChange={(e) => setScrapeConfig({ ...scrapeConfig, strict_title: e.target.checked })}
                        className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                      />
                      Strict title
                    </label>
                  </div>
                </div>

                {/* Sources */}
                <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sources</p>
                  <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-slate-700">
                    {sourceOptions.map((source) => (
                      <label key={source.id} className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2">
                        <input
                          type="checkbox"
                          checked={scrapeConfig.sources.includes(source.id)}
                          onChange={() => toggleSource(source.id)}
                          className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                        />
                        <span>{source.label}</span>
                      </label>
                    ))}
                  </div>
                  <div className="mt-4 flex gap-3">
                    <button
                      type="button"
                      onClick={selectAllSources}
                      className="inline-flex items-center justify-center rounded-full bg-indigo-100 px-4 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-200"
                    >
                      Select all
                    </button>
                    <button
                      type="button"
                      onClick={deselectAllSources}
                      className="inline-flex items-center justify-center rounded-full bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {/* Run scraper button inside Scrape config */}
                <div className="mt-6 pt-4 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={runScrapeHandler}
                    disabled={scrapeMutation.status === "pending" || !scrapeConfig.sources.length}
                    className="w-full rounded-full bg-indigo-600 px-6 py-3.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {scrapeMutation.status === "pending" ? (
                      <span className="inline-flex items-center justify-center gap-2">
                        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Running scrape...
                      </span>
                    ) : (
                      "Run scraper"
                    )}
                  </button>
                </div>
              </section>

              {user && <ApplyHelper userId={user.id} userEmail={user.email} />}
            </div>
          </aside>

          <section className="space-y-6">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="grid gap-4 md:grid-cols-4">
                <StatCard label="Active matches" value={stats?.total_jobs ?? 0} />
                <StatCard label="New today" value={stats?.new_today ?? 0} />
                <StatCard label="Applied" value={stats?.applied_count ?? 0} />
                <StatCard label="Apply rate" value={appliedRate} />
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <ChartCard title="Jobs by Tech Stack" values={stats?.by_tech_stack ?? {}} />
              <ChartCard title="Jobs by Company Size" values={stats?.by_company_size ?? {}} type="pie" />
              <ChartCard title="Jobs by Posted Day" values={stats?.by_day ?? {}} type="line" />
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">Search results</p>
                  <p className="mt-2 text-sm text-slate-600">Filter the latest job matches by stack, size, or application status.</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <input
                    type="text"
                    value={filters.search}
                    onChange={(e) => setFilterValue("search", e.target.value)}
                    placeholder="Search title, company, description"
                    className="min-w-[220px] rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  />
                  <select
                    value={filters.tech_stack}
                    onChange={(e) => setFilterValue("tech_stack", e.target.value)}
                    className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="">All stacks</option>
                    {stackOptions.map((option) => (
                      option ? <option key={option} value={option}>{option}</option> : null
                    ))}
                  </select>
                  <select
                    value={filters.company_size}
                    onChange={(e) => setFilterValue("company_size", e.target.value)}
                    className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="">All company sizes</option>
                    {sizeOptions.map((option) => (
                      option ? <option key={option} value={option}>{option}</option> : null
                    ))}
                  </select>
                  <select
                    value={filters.is_applied}
                    onChange={(e) => setFilterValue("is_applied", e.target.value)}
                    className="rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="">All statuses</option>
                    <option value="false">Not applied</option>
                    <option value="true">Applied</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              {result?.error ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                  <strong>Error:</strong> {String(result.error)}
                </div>
              ) : result ? (
                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                  <h3 className="text-sm font-semibold text-slate-900">Last scrape</h3>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl bg-white p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Status</p>
                      <p className="mt-2 text-xl font-bold text-slate-900">{result.status}</p>
                    </div>
                    {result.jobs_found !== undefined && (
                      <div className="rounded-2xl bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Jobs found</p>
                        <p className="mt-2 text-xl font-bold text-slate-900">{result.jobs_found}</p>
                      </div>
                    )}
                    {result.jobs_new !== undefined && (
                      <div className="rounded-2xl bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">New jobs</p>
                        <p className="mt-2 text-xl font-bold text-slate-900">{result.jobs_new}</p>
                      </div>
                    )}
                    {result.sources_run && (
                      <div className="rounded-2xl bg-white p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Sources</p>
                        <p className="mt-2 text-xl font-bold text-slate-900">{result.sources_run.length}</p>
                      </div>
                    )}
                  </div>
                  {result.sources_run && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {result.sources_run.map((source: string) => (
                        <span key={source} className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
                          {source}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            <JobTable jobs={jobs} />

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-950">Source pulse</h2>
              <p className="mt-2 text-sm text-slate-600">Track the best boards and top remote sources from your latest matches.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {activeSources.slice(0, 4).map(([source, count]) => (
                  <div key={source} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-sm font-semibold text-slate-900">{source}</p>
                    <p className="mt-2 text-2xl font-bold text-slate-950">{count}</p>
                  </div>
                ))}
                {!activeSources.length && (
                  <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
                    Run a scrape to populate your source pulse and reveal source performance.
                  </div>
                )}
              </div>
            </section>
          </section>
        </div>
      </div>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="mt-4 text-3xl font-bold text-slate-950">{value}</p>
    </div>
  );
}
