"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApplyHelper } from "@/components/apply-helper";
import { ChartCard } from "@/components/chart-card";
import { JobTable } from "@/components/job-table";
import {
  getHotJobs,
  getJobProfiles,
  getJobs,
  getStats,
  getSavedSearches,
  getCompanies,
  getLearningPaths,
  getJobBundles,
  runScrape,
  runSavedSearch,
  createSavedSearch,
  ScrapeConfig,
} from "@/lib/api";
import type { ScrapeResult } from "@/lib/api";
import type { Job, JobProfile, JobStats } from "@/types/job";

const sourceOptions = [
  // API-based (most reliable)
  { id: "remotive", label: "Remotive", category: "api" },
  { id: "remoteok", label: "Remote OK", category: "api" },
  { id: "arbeitnow", label: "ArbeitNow", category: "api" },
  { id: "devto", label: "Dev.to", category: "api" },
  { id: "greenhouse", label: "Greenhouse", category: "api" },
  // RSS-based (reliable)
  { id: "weworkremotely", label: "WWR", category: "rss" },
  { id: "workingnomads", label: "Working Nomads", category: "rss" },
  { id: "himalayas", label: "Himalayas", category: "rss" },
  { id: "jobicy", label: "Jobicy", category: "rss" },
  { id: "jobspresso", label: "Jobspresso", category: "rss" },
  { id: "nofluffjobs", label: "No Fluff Jobs", category: "rss" },
  { id: "virtualvocations", label: "Virtual Vocations", category: "rss" },
  { id: "jobscollider", label: "JobsCollider", category: "rss" },
  { id: "remotepython", label: "RemotePython", category: "rss" },
  { id: "fossjobs", label: "FOSS Jobs", category: "rss" },
  { id: "remoteworkhub", label: "Remote Work Hub", category: "rss" },
  { id: "cryptojobs", label: "CryptoJobs", category: "rss" },
  { id: "europeremotely", label: "EuropeRemotely", category: "rss" },
  { id: "remotecouk", label: "Remote.co.uk", category: "rss" },
  { id: "skipthedrive", label: "SkipTheDrive", category: "rss" },
];

const DEFAULT_SOURCE_IDS = sourceOptions.map((s) => s.id);

const SENIORITY_OPTIONS = [
  { value: "", label: "All levels" },
  { value: "Junior", label: "Junior" },
  { value: "Mid-Level", label: "Mid-Level" },
  { value: "Senior", label: "Senior" },
  { value: "Lead", label: "Lead / Principal" }
];

function cleanProfileName(name: string): string {
  return name.replace(/\s*\((Junior|Mid-Level|Senior|Lead)\)/, "").trim();
}

function getUniqueBaseProfiles(profiles: JobProfile[]) {
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
  const [showSources, setShowSources] = useState(false);

  // Compact filters for the job table results
  const [filters, setFilters] = useState({
    search: "",
    tech_stack: "",
    company_size: "",
    experience_level: "",
    region_eligibility: "",
    seniority_tag: "",
    is_verified_remote: "",
    is_duplicate: "",
    is_sponsored: "",
    is_hot_job: "",
    is_applied: ""
  });
  const [result, setResult] = useState<any | null>(null);

  // === QUERIES ===
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

  const hotJobsQuery = useQuery<Job[], Error>({
    queryKey: ["hot-jobs"],
    queryFn: () => getHotJobs(10),
    enabled: isAuthenticated,
    refetchInterval: 60_000
  });

  const savedSearchesQuery = useQuery<any[]>({
    queryKey: ["saved-searches", user?.email],
    queryFn: () => getSavedSearches(user!.email),
    enabled: isAuthenticated && !!user?.email
  });

  const companiesQuery = useQuery<any[]>({
    queryKey: ["companies-summary"],
    queryFn: () => getCompanies(),
    enabled: isAuthenticated
  });

  const learningPathsQuery = useQuery<any[]>({
    queryKey: ["learning-paths-featured"],
    queryFn: () => getLearningPaths(true),
    enabled: isAuthenticated
  });

  const jobBundlesQuery = useQuery<any[]>({
    queryKey: ["job-bundles-featured"],
    queryFn: () => getJobBundles(undefined, true),
    enabled: isAuthenticated
  });

  const stats = statsQuery.data;
  const jobs = jobsQuery.data ?? [];

  // === DERIVED ===
  const stackOptions = useMemo(
    () => ["", ...Object.keys(statsQuery.data?.by_tech_stack ?? {})],
    [statsQuery.data]
  );
  const sizeOptions = useMemo(
    () => ["", ...Object.keys(statsQuery.data?.by_company_size ?? {})],
    [statsQuery.data]
  );
  const baseProfiles = useMemo(
    () => (profilesQuery.data ? getUniqueBaseProfiles(profilesQuery.data) : []),
    [profilesQuery.data]
  );
  const activeSources = useMemo(
    () => Object.entries(stats?.by_source ?? {}).sort(([, a], [, b]) => b - a),
    [stats]
  );
  const appliedRate = useMemo(() => {
    if (!stats?.total_jobs) return "0%";
    return `${Math.round((stats.applied_count / stats.total_jobs) * 100)}%`;
  }, [stats]);

  const selectProfile = (profile: JobProfile) => {
    setScrapeConfig((prev) => ({
      ...prev,
      job_profile_id: profile.id,
      query: cleanProfileName(profile.name),
      min_experience: profile.min_experience,
      max_experience: profile.max_experience
    }));
  };

  const selectBaseProfile = (cleanName: string) => {
    const matched = profilesQuery.data?.find((p) => cleanProfileName(p.name) === cleanName);
    if (matched) selectProfile(matched);
  };

  const scrapeMutation = useMutation<ScrapeResult, Error, void>({
    mutationFn: () => {
      const baseQuery = scrapeConfig.query;
      const finalQuery = seniority ? `${seniority} ${baseQuery}` : baseQuery;
      return runScrape({ ...scrapeConfig, query: finalQuery, linkedin_urls: [] });
    },
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["jobs", user?.id] });
      queryClient.invalidateQueries({ queryKey: ["stats", user?.id] });
    }
  });

  const setFilterValue = (key: keyof typeof filters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const toggleSource = (id: string) => {
    setScrapeConfig((prev) => ({
      ...prev,
      sources: prev.sources.includes(id)
        ? prev.sources.filter((s) => s !== id)
        : [...prev.sources, id]
    }));
  };

  // === LOADING / AUTH GATE ===
  if (isLoading) {
    return <div className="p-8 text-center text-slate-600">Checking authentication...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-lg">
          <h2 className="mb-4 text-2xl font-semibold text-slate-900">Sign in to access the scraper workspace</h2>
          <p className="mb-6 text-sm text-slate-600">Run searches, review job analytics, and track remote opportunities after signing in.</p>
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
      <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-5 sm:py-8">
        {/* ===== HEADER ===== */}
        <div className="mb-6 rounded-[2rem] border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-6 shadow-lg sm:p-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4 max-w-2xl">
              <div className="relative">
                <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 opacity-20 blur-sm"></div>
                <img src="/logo.svg" alt="Remote Job Hunter Logo" className="relative h-16 w-16 flex-shrink-0" />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-indigo-600">Scraper workspace</p>
                <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">Remote job command center</h1>
                <p className="text-sm leading-7 text-slate-600">
                  Configure scrapers, browse jobs, track sources, and manage your remote job hunt in one workspace.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/analytics" className="rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Analytics
              </Link>
              <Link href="/" className="rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Home
              </Link>
            </div>
          </div>

          {/* Quick stats row */}
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
            <QuickStat label="Active jobs" value={stats?.total_jobs ?? 0} />
            <QuickStat label="New today" value={stats?.new_today ?? 0} />
            <QuickStat label="Applied" value={stats?.applied_count ?? 0} />
            <QuickStat label="Apply rate" value={appliedRate} />
          </div>
        </div>

        {/* ===== TWO-COLUMN LAYOUT ===== */}
        <div className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)] xl:grid-cols-[400px_minmax(0,1fr)]">
          {/* ===== LEFT SIDEBAR ===== */}
          <aside className="space-y-5 min-w-0">
            {/* --- Scrape Config --- */}
            <ScrapeConfigCard
              seniority={seniority}
              setSeniority={setSeniority}
              scrapeConfig={scrapeConfig}
              setScrapeConfig={setScrapeConfig}
              baseProfiles={baseProfiles}
              selectBaseProfile={selectBaseProfile}
              showSources={showSources}
              setShowSources={setShowSources}
              sourceOptions={sourceOptions}
              toggleSource={toggleSource}
              scrapeMutation={scrapeMutation}
              runScrapeHandler={() => scrapeMutation.mutate()}
            />

            {/* --- Quick Actions --- */}
            <QuickActionsCard
              user={user}
              queryClient={queryClient}
              savedSearches={savedSearchesQuery.data}
              savedSearchesLoading={savedSearchesQuery.isLoading}
            />

            {/* --- Top Companies (from unused /companies API) --- */}
            <TopCompaniesCard companies={companiesQuery.data} />

            {/* --- Featured Learning Paths (from unused /learning-paths API) --- */}
            {learningPathsQuery.data && learningPathsQuery.data.length > 0 && (
              <LearningPathsCard paths={learningPathsQuery.data} />
            )}

            {/* --- Apply Helper --- */}
            {user && <ApplyHelper userId={user.id} userEmail={user.email} />}
          </aside>

          {/* ===== MAIN CONTENT ===== */}
          <section className="space-y-5 min-w-0">
            {/* Charts */}
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <ChartCard title="Jobs by Tech Stack" values={stats?.by_tech_stack ?? {}} />
              <ChartCard title="Jobs by Company Size" values={stats?.by_company_size ?? {}} type="pie" />
              <ChartCard title="Jobs by Day" values={stats?.by_day ?? {}} type="line" />
            </div>

            {/* Compact Filters + Job Table */}
            <CompactFilterBar
              filters={filters}
              setFilterValue={setFilterValue as (key: string, value: string) => void}
              stackOptions={stackOptions}
              sizeOptions={sizeOptions}
            />

            {/* Scrape Result */}
            {result && <ScrapeResultCard result={result} />}

            {/* Job Table */}
            <JobTable jobs={jobs} />

            {/* Bottom row: Source Pulse + Hot Jobs side-by-side */}
            <div className="grid gap-5 sm:grid-cols-2">
              <SourcePulseCard activeSources={activeSources} />
              <HotJobsCard hotJobsQuery={hotJobsQuery} />
            </div>

            {/* Job Bundles (from unused /job-bundles API) */}
            {jobBundlesQuery.data && jobBundlesQuery.data.length > 0 && (
              <JobBundlesCard bundles={jobBundlesQuery.data} />
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

// =========================================================================
// Sub-components
// =========================================================================

function QuickStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
    </div>
  );
}

function ScrapeConfigCard({
  seniority, setSeniority,
  scrapeConfig, setScrapeConfig,
  baseProfiles, selectBaseProfile,
  showSources, setShowSources,
  sourceOptions, toggleSource,
  scrapeMutation, runScrapeHandler,
}: {
  seniority: string;
  setSeniority: (v: string) => void;
  scrapeConfig: ScrapeConfig;
  setScrapeConfig: (c: ScrapeConfig) => void;
  baseProfiles: { display: string; id: string }[];
  selectBaseProfile: (n: string) => void;
  showSources: boolean;
  setShowSources: (v: boolean) => void;
  sourceOptions: { id: string; label: string; category: string }[];
  toggleSource: (id: string) => void;
  scrapeMutation: { status: string };
  runScrapeHandler: () => void;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-slate-950">Scrape config</h2>
      <p className="mb-4 text-xs text-slate-500">Configure and run a remote job scraper.</p>

      <div className="space-y-3">
        {/* Seniority */}
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Seniority</label>
          <select value={seniority} onChange={(e) => setSeniority(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
            {SENIORITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Title */}
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Role</label>
          <select value={cleanProfileName(scrapeConfig.query)}
            onChange={(e) => { if (e.target.value) selectBaseProfile(e.target.value); else setScrapeConfig({ ...scrapeConfig, query: "", job_profile_id: undefined }); }}
            className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
            <option value="">Select...</option>
            {baseProfiles.map((bp) => <option key={bp.id} value={bp.display}>{bp.display}</option>)}
          </select>
          <input type="text" value={scrapeConfig.query}
            onChange={(e) => setScrapeConfig({ ...scrapeConfig, query: e.target.value, job_profile_id: undefined })}
            placeholder="Or type custom role…"
            className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
        </div>

        {/* Experience */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Min yrs</label>
            <input type="number" value={scrapeConfig.min_experience ?? 0}
              onChange={(e) => setScrapeConfig({ ...scrapeConfig, min_experience: Number(e.target.value) })}
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Max yrs</label>
            <input type="number" value={scrapeConfig.max_experience ?? 0}
              onChange={(e) => setScrapeConfig({ ...scrapeConfig, max_experience: Number(e.target.value) })}
              className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
          </div>
        </div>

        {/* Posted within */}
        <div>
          <label className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Posted within days</label>
          <input type="number" value={scrapeConfig.posted_within_days ?? 14}
            onChange={(e) => setScrapeConfig({ ...scrapeConfig, posted_within_days: Number(e.target.value) })}
            className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
        </div>

        {/* Toggle filters */}
        <div className="flex flex-wrap gap-2">
          <ToggleChip checked={scrapeConfig.remote_only} onChange={(v) => setScrapeConfig({ ...scrapeConfig, remote_only: v })} label="Remote only" />
          <ToggleChip checked={scrapeConfig.global_or_india} onChange={(v) => setScrapeConfig({ ...scrapeConfig, global_or_india: v })} label="Global eligible" />
          <ToggleChip checked={scrapeConfig.exclude_indian_hq} onChange={(v) => setScrapeConfig({ ...scrapeConfig, exclude_indian_hq: v })} label="Exclude IN HQ" />
          <ToggleChip checked={scrapeConfig.strict_title} onChange={(v) => setScrapeConfig({ ...scrapeConfig, strict_title: v })} label="Strict title" />
        </div>

        {/* Sources toggle */}
        <div>
          <button onClick={() => setShowSources(!showSources)}
            className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800">
            {showSources ? "Hide" : "Show"} sources ({scrapeConfig.sources.length} selected)
            <svg className={`h-3 w-3 transition ${showSources ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
          </button>
          {showSources && (
            <div className="mt-2 space-y-2 text-xs">
              {(["api", "rss"] as const).map((cat) => {
                const items = sourceOptions.filter((s) => s.category === cat);
                if (items.length === 0) return null;
                return (
                  <div key={cat}>
                    <p className="mb-1 font-medium text-slate-500 uppercase tracking-wider text-[10px]">
                      {cat === "api" ? "API (most reliable)" : "RSS feeds"}
                    </p>
                    <div className="grid grid-cols-2 gap-1.5">
                      {items.map((s) => (
                        <label key={s.id} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5">
                          <input type="checkbox" checked={scrapeConfig.sources.includes(s.id)} onChange={() => toggleSource(s.id)} className="h-3.5 w-3.5 rounded border-slate-300 text-indigo-600" />
                          <span>{s.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Run button */}
        <button onClick={runScrapeHandler} disabled={scrapeMutation.status === "pending" || !scrapeConfig.sources.length}
          className="mt-2 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50">
          {scrapeMutation.status === "pending" ? (
            <span className="inline-flex items-center justify-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Scraping…
            </span>
          ) : "Run scraper"}
        </button>
      </div>
    </section>
  );
}

function ToggleChip({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button onClick={() => onChange(!checked)}
      className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
        checked ? "border-indigo-300 bg-indigo-50 text-indigo-700" : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
      }`}>
      {checked ? "✓ " : ""}{label}
    </button>
  );
}

function QuickActionsCard({ user, queryClient, savedSearches, savedSearchesLoading }: { user: any; queryClient: any; savedSearches: any[] | undefined; savedSearchesLoading: boolean }) {
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const saveCurrentSearch = async () => {
    if (!user?.email) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const name = `Search ${new Date().toLocaleString(undefined, { month: "short", day: "numeric" })}`;
      await createSavedSearch(user.email, name, {
        query: "DevOps Engineer",
        min_experience: 0,
        max_experience: 2,
        posted_within_days: 14,
        remote_only: true,
        global_or_india: true,
        exclude_indian_hq: true,
        strict_experience: false,
        strict_title: true,
        strict_junior: false,
        send_alerts: true,
        sources: [],
        linkedin_urls: []
      });
      queryClient.invalidateQueries({ queryKey: ["saved-searches"] });
      setSaveMsg("Saved ✓");
    } catch (err: any) {
      setSaveMsg(err?.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-slate-950">Quick actions</h2>
      <div className="mt-3 space-y-2">
        <button onClick={saveCurrentSearch} disabled={saving}
          className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
          {saving ? "Saving…" : "💾 Save current search"}
        </button>
        {saveMsg && <p className="text-xs text-slate-500">{saveMsg}</p>}
      </div>

      {/* Saved searches */}
      <div className="mt-4">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Saved searches</p>
        {savedSearchesLoading ? (
          <p className="mt-2 text-xs text-slate-400">Loading…</p>
        ) : savedSearches && savedSearches.length > 0 ? (
          <div className="mt-2 space-y-1.5 max-h-[160px] overflow-y-auto">
            {savedSearches.slice(0, 5).map((s: any) => (
              <div key={s.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs">
                <span className="truncate text-slate-700">{s.name || "Unnamed"}</span>
                <button onClick={async () => { try { await runSavedSearch(s.id); } catch {} }}
                  className="shrink-0 rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-200">
                  Run
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400">No saved searches yet.</p>
        )}
      </div>
    </section>
  );
}

function TopCompaniesCard({ companies }: { companies: any[] | undefined }) {
  if (!companies || companies.length === 0) return null;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-slate-950">Top companies</h2>
      <p className="mb-3 text-xs text-slate-500">Employers with active remote listings.</p>
      <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
        {companies.slice(0, 8).map((c: any) => (
          <div key={c.name || c.company} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs">
            <span className="font-medium text-slate-700">{c.name || c.company}</span>
            <span className="text-slate-500">{c.job_count ?? c.total_jobs ?? "—"} jobs</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function LearningPathsCard({ paths }: { paths: any[] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-slate-950">📚 Learning paths</h2>
      <p className="mb-3 text-xs text-slate-500">Skill tracks for top roles.</p>
      <div className="space-y-1.5">
        {paths.slice(0, 4).map((p: any) => (
          <div key={p.id || p.name} className="rounded-xl bg-gradient-to-r from-sky-50 to-white px-3 py-2 text-xs">
            <p className="font-semibold text-slate-800">{p.name || p.profile_name}</p>
            <p className="text-slate-500">{p.description ? p.description.slice(0, 60) + "…" : "Explore skills →"}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function CompactFilterBar({ filters, setFilterValue, stackOptions, sizeOptions }: {
  filters: Record<string, string>;
  setFilterValue: (key: string, value: string) => void;
  stackOptions: string[];
  sizeOptions: string[];
}) {
  const [expanded, setExpanded] = useState(false);

  const baseFilters = (
    <>
      <input type="text" value={filters.search} onChange={(e) => setFilterValue("search", e.target.value)}
        placeholder="Search title, company…"
        className="min-w-[160px] rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
      <select value={filters.tech_stack} onChange={(e) => setFilterValue("tech_stack", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Stack</option>
        {stackOptions.map((o) => o ? <option key={o} value={o}>{o}</option> : null)}
      </select>
      <select value={filters.company_size} onChange={(e) => setFilterValue("company_size", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Size</option>
        {sizeOptions.map((o) => o ? <option key={o} value={o}>{o}</option> : null)}
      </select>
      <select value={filters.is_applied} onChange={(e) => setFilterValue("is_applied", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Status</option>
        <option value="false">Not applied</option>
        <option value="true">Applied</option>
      </select>
    </>
  );

  const advancedFilters = (
    <>
      <select value={filters.experience_level} onChange={(e) => setFilterValue("experience_level", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Experience</option>
        <option value="Entry level">Entry</option>
        <option value="Mid-Senior level">Mid-Senior</option>
        <option value="Senior">Senior</option>
      </select>
      <select value={filters.region_eligibility} onChange={(e) => setFilterValue("region_eligibility", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Region</option>
        <option value="Global">Global</option>
        <option value="India">India</option>
        <option value="US only">US only</option>
        <option value="EU only">EU only</option>
      </select>
      <select value={filters.seniority_tag} onChange={(e) => setFilterValue("seniority_tag", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Seniority</option>
        <option value="junior">Junior</option>
        <option value="mid">Mid</option>
        <option value="senior">Senior</option>
      </select>
      <select value={filters.is_verified_remote} onChange={(e) => setFilterValue("is_verified_remote", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Remote type</option>
        <option value="true">Verified remote</option>
        <option value="false">Not verified</option>
      </select>
      <select value={filters.is_hot_job} onChange={(e) => setFilterValue("is_hot_job", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">All jobs</option>
        <option value="true">🔥 Hot only</option>
      </select>
      <select value={filters.is_duplicate} onChange={(e) => setFilterValue("is_duplicate", e.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
        <option value="">Duplicates</option>
        <option value="false">No dupes</option>
        <option value="true">Dupes only</option>
      </select>
    </>
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        {baseFilters}
        <button onClick={() => setExpanded(!expanded)}
          className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">
          {expanded ? "Fewer filters" : `+${6} more`}
        </button>
      </div>
      {expanded && (
        <div className="mt-2 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
          {advancedFilters}
        </div>
      )}
    </div>
  );
}

function ScrapeResultCard({ result }: { result: any }) {
  if (result?.error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
        <strong>Error:</strong> {String(result.error)}
      </div>
    );
  }
  if (!result) return null;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-4">
        <ResultBadge label="Status" value={result.status} />
        {result.jobs_found !== undefined && <ResultBadge label="Found" value={result.jobs_found} />}
        {result.jobs_new !== undefined && <ResultBadge label="New" value={result.jobs_new} />}
        {result.duplicate_jobs !== undefined && <ResultBadge label="Duplicates" value={result.duplicate_jobs} />}
        {result.verified_remote_jobs !== undefined && <ResultBadge label="Verified remote" value={result.verified_remote_jobs} />}
        {result.duration_seconds !== undefined && <ResultBadge label="Duration" value={`${result.duration_seconds}s`} />}
      </div>
      {result.sources_run && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {result.sources_run.map((s: string) => (
            <span key={s} className="rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-semibold text-indigo-700">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function ResultBadge({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-slate-50 px-4 py-2">
      <p className="text-xs uppercase tracking-[0.15em] text-slate-500">{label}</p>
      <p className="mt-0.5 text-lg font-bold text-slate-900">{value}</p>
    </div>
  );
}

function SourcePulseCard({ activeSources }: { activeSources: [string, number][] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-slate-950">Source pulse</h2>
      <p className="mb-3 text-xs text-slate-500">Which boards deliver the most matches.</p>
      <div className="space-y-2">
        {activeSources.slice(0, 6).map(([source, count]) => (
          <div key={source} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5">
            <span className="text-sm font-medium text-slate-700">{source}</span>
            <span className="text-sm font-bold text-slate-900">{count}</span>
          </div>
        ))}
        {!activeSources.length && (
          <p className="text-xs text-slate-400">Run a scrape to see source data.</p>
        )}
      </div>
    </section>
  );
}

function HotJobsCard({ hotJobsQuery }: { hotJobsQuery: { isLoading: boolean; data: Job[] | undefined } }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-950">🔥 Hot jobs</h2>
          <p className="text-xs text-slate-500">Verified remote, recent, high-quality.</p>
        </div>
        <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700">Live</span>
      </div>
      <div className="mt-3 space-y-2 max-h-[300px] overflow-y-auto">
        {hotJobsQuery.isLoading ? (
          <p className="text-xs text-slate-400">Loading…</p>
        ) : hotJobsQuery.data && hotJobsQuery.data.length > 0 ? (
          hotJobsQuery.data.map((job) => (
            <div key={job.id} className="rounded-xl border border-slate-100 bg-gradient-to-r from-orange-50 to-white p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <p className="text-xs font-semibold text-slate-900">{job.title}</p>
                    {job.is_verified_remote && <span className="rounded-full bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold text-green-700">✓</span>}
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">{job.company}</p>
                </div>
                <a href={job.url} target="_blank" rel="noreferrer" className="shrink-0 rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-slate-700">Apply</a>
              </div>
              {job.tech_stack && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {job.tech_stack.split(",").slice(0, 3).map((t) => (
                    <span key={t.trim()} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">{t.trim()}</span>
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <p className="text-xs text-slate-400">No hot jobs yet. Run a scrape & mark via API.</p>
        )}
      </div>
    </section>
  );
}

function JobBundlesCard({ bundles }: { bundles: any[] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-slate-950">📦 Job bundles</h2>
      <p className="mb-3 text-xs text-slate-500">Curated groups of related remote roles.</p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {bundles.slice(0, 6).map((b: any) => (
          <div key={b.id || b.name} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-800">{b.name || b.title}</p>
            <p className="mt-1 text-xs text-slate-500">{b.description ? b.description.slice(0, 80) : ""}</p>
            <p className="mt-1.5 text-xs font-semibold text-indigo-600">{b.job_count ?? b.total_jobs ?? "—"} roles</p>
          </div>
        ))}
      </div>
    </section>
  );
}