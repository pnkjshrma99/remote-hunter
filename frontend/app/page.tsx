"use client";

import Link from "next/link";
import { Bell, BriefcaseBusiness, Filter, Mail, Play, RefreshCcw } from "lucide-react";
import type { JobProfile } from "@/types/job";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ChartCard } from "@/components/chart-card";
import { JobTable } from "@/components/job-table";
import { createCoverLetter, deleteCoverLetter, getCoverLetters, getCompanies, getCompany, getJobs, getStats, runScrape, ScrapeConfig, getJobProfiles } from "@/lib/api";

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
  { id: "arbeitnow", label: "Arbeitnow" },
  { id: "stackoverflow", label: "Stack Overflow" },
  { id: "angellist", label: "AngelList" },
  { id: "justremote", label: "JustRemote" },
  { id: "nofluffjobs", label: "No Fluff Jobs" }
];

const stackOptions = ["", "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform", "CI/CD", "Python", "Linux"];
const sizeOptions = ["", "Startup", "Mid-size", "Enterprise"];

export default function Home() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    search: "",
    tech_stack: "",
    company_size: "",
    is_applied: ""
  });
  const [template, setTemplate] = useState({
    name: "Junior DevOps - concise",
    company_type: "Global remote",
    content:
      "Hi {{company}} team,\n\nI am excited about the {{title}} role. I have hands-on exposure to Linux, Docker, Kubernetes, Terraform, CI/CD, and cloud operations, and I am looking for a junior remote DevOps/SRE role where I can grow while contributing reliably from India.\n\nBest,\n"
  });
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
    sources: sourceOptions.map((source) => source.id),
    linkedin_urls: []
  });
  const [linkedinUrlText, setLinkedinUrlText] = useState("");
  const [companySearchTerm, setCompanySearchTerm] = useState("");
  const [selectedCompanyName, setSelectedCompanyName] = useState("");

  const jobsQuery = useQuery({ queryKey: ["jobs", filters], queryFn: () => getJobs(filters) });
  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const templatesQuery = useQuery({ queryKey: ["cover-letters"], queryFn: getCoverLetters });
  const profilesQuery = useQuery({ queryKey: ["job-profiles"], queryFn: getJobProfiles });
  const companiesQuery = useQuery({
    queryKey: ["companies"],
    queryFn: () => getCompanies(),
    placeholderData: keepPreviousData
  });

  const companySearchQuery = useQuery({
    queryKey: ["companies", companySearchTerm],
    queryFn: () => getCompanies(companySearchTerm || undefined),
    enabled: true,
    placeholderData: keepPreviousData
  });

  const companyProfileQuery = useQuery({
    queryKey: ["company", selectedCompanyName],
    queryFn: () => getCompany(selectedCompanyName),
    enabled: selectedCompanyName !== ""
  });

  const selectProfile = (profile: JobProfile) => {
    setScrapeConfig({
      ...scrapeConfig,
      job_profile_id: profile.id,
      query: profile.name,
      min_experience: profile.min_experience,
      max_experience: profile.max_experience
    });
  };
  const scrapeMutation = useMutation({
    mutationFn: () =>
      runScrape({
        ...scrapeConfig,
        linkedin_urls: linkedinUrlText
          .split("\n")
          .map((url) => url.trim())
          .filter(Boolean)
      }),
    onSuccess: () => queryClient.invalidateQueries()
  });
  const templateMutation = useMutation({
    mutationFn: createCoverLetter,
    onSuccess: () => {
      setTemplate({ ...template, name: "" });
      queryClient.invalidateQueries({ queryKey: ["cover-letters"] });
    }
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: deleteCoverLetter,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cover-letters"] })
  });

  const jobs = jobsQuery.data ?? [];
  const stats = statsQuery.data;
  const appliedRate = useMemo(() => {
    if (!stats?.total_jobs) return "0%";
    return `${Math.round((stats.applied_count / stats.total_jobs) * 100)}%`;
  }, [stats]);

  const activeSources = useMemo(() => {
    return Object.entries(stats?.by_source ?? {}).sort(([, a], [, b]) => b - a);
  }, [stats]);

  return (
    <main className="min-h-screen bg-paper">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-ink">Remote Job Hunter</h1>
            <p className="mt-2 max-w-2xl text-sm text-stone-600 md:text-base">
              A modern remote career control center for discovering remote-friendly companies, tracking the best openings, and winning more applications with tailored outreach.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/analytics"
              className="rounded bg-sky px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#244f8e]"
            >
              Explore dashboards
            </Link>
            <button
              type="button"
              className="rounded border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:bg-stone-50"
              onClick={() => window.scrollTo({ top: 720, behavior: "smooth" })}
            >
              Run remote search
            </button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-[1500px] px-5 py-8">
        <div className="grid gap-6 rounded-3xl border border-stone-200 bg-white p-8 shadow-sm lg:grid-cols-[1.4fr_0.8fr]">
          <div className="space-y-5">
            <div className="inline-flex rounded-full bg-moss/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-moss">
              Remote hiring intelligence
            </div>
            <div>
              <h2 className="text-4xl font-bold tracking-tight text-ink sm:text-5xl">A smarter way to discover remote work and grow your career.</h2>
              <p className="mt-4 max-w-2xl text-base leading-7 text-stone-600">
                Use one dashboard to find curated remote roles, compare company profiles, surface career-fit benchmarks, and automate your job hunt with personal templates and smart alerts.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-slate-100 p-6 shadow-[0_18px_50px_-30px_rgba(15,23,42,0.2)]">
                <p className="text-sm font-semibold text-ink">Remote job discovery</p>
                <p className="mt-2 text-sm text-stone-600">Search hundreds of remote openings from multiple boards, filter by experience, stack, and company size.</p>
              </div>
              <div className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-sky-50 p-6 shadow-[0_18px_50px_-30px_rgba(15,23,42,0.2)]">
                <p className="text-sm font-semibold text-ink">Company intelligence</p>
                <p className="mt-2 text-sm text-stone-600">Lookup employer profiles, remote policies, verified ratings, and recent open roles.</p>
              </div>
            </div>
            {profilesQuery.data?.length ? (
              <div className="mt-6 rounded-[2rem] border border-sky-100 bg-gradient-to-br from-sky-50 via-white to-slate-100 p-6 shadow-[0_18px_50px_-30px_rgba(15,23,42,0.2)]">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">Suggested role profiles</p>
                    <p className="mt-2 text-sm text-sky-900">Tap a profile to fill your scraper criteria instantly.</p>
                  </div>
                  <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-800">Quick launch</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  {profilesQuery.data.slice(0, 6).map((profile) => (
                    <button
                      key={profile.id}
                      type="button"
                      className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-ink transition hover:border-sky-400 hover:bg-sky-50"
                      onClick={() => selectProfile(profile)}
                    >
                      {profile.name}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
          <div className="grid gap-4">
            <div className="rounded-3xl border border-stone-200 bg-slate-50 p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">What you get</p>
              <ul className="mt-4 space-y-3 text-sm text-stone-700">
                <li>✔ Unified dashboard for remote job performance and applications</li>
                <li>✔ Smart scraping with remote-first filters</li>
                <li>✔ Company profile search with recent listings</li>
                <li>✔ Cover letter templates and saved outreach tools</li>
              </ul>
            </div>
            <div className="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Professional dashboard</p>
              <div className="mt-4 grid gap-3 text-sm text-stone-700">
                <div className="rounded-2xl bg-stone-100 p-4">
                  <p className="font-semibold">Team ready</p>
                  <p className="mt-1">Designed for candidates and recruiters who need fast remote market visibility.</p>
                </div>
                <div className="rounded-2xl bg-stone-100 p-4">
                  <p className="font-semibold">Company profiles</p>
                  <p className="mt-1">See employer ratings, headquarters, remote friendliness, and open roles.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Discovery</p>
            <p className="mt-3 text-lg font-semibold text-ink">One-click remote search</p>
          </div>
          <div className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Insights</p>
            <p className="mt-3 text-lg font-semibold text-ink">Data-driven job metrics</p>
          </div>
          <div className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Career</p>
            <p className="mt-3 text-lg font-semibold text-ink">Cover letter automation</p>
          </div>
          <div className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Profile</p>
            <p className="mt-3 text-lg font-semibold text-ink">Company intelligence</p>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-[1500px] gap-5 px-5 py-5 xl:grid-cols-[1fr_380px]">
        <section className="space-y-5">
          <div className="grid gap-3 md:grid-cols-4">
            <Metric label="Active matches" value={stats?.total_jobs ?? 0} icon={<BriefcaseBusiness className="h-4 w-4" />} />
            <Metric label="New today" value={stats?.new_today ?? 0} icon={<Bell className="h-4 w-4" />} />
            <Metric label="Applied" value={stats?.applied_count ?? 0} icon={<Mail className="h-4 w-4" />} />
            <Metric label="Apply rate" value={appliedRate} icon={<Filter className="h-4 w-4" />} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <ChartCard title="Jobs by Tech Stack" values={stats?.by_tech_stack ?? {}} />
            <ChartCard title="Jobs by Company Size" values={stats?.by_company_size ?? {}} type="pie" />
            <ChartCard title="Jobs by Posted Day" values={stats?.by_day ?? {}} type="line" />
          </div>

          <section className="rounded-[2rem] border border-slate-200 bg-white/95 p-5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.18)] backdrop-blur-md">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-ink">Scrape Config</h2>
              {scrapeMutation.data && (
                <div className="space-y-2 text-xs text-stone-600">
                  <div>Found {scrapeMutation.data.jobs_found ?? 0} jobs, {scrapeMutation.data.jobs_new ?? 0} new.</div>
                  {scrapeMutation.data.duplicate_jobs !== undefined ? (
                    <div>Duplicate jobs: {scrapeMutation.data.duplicate_jobs}</div>
                  ) : null}
                  {scrapeMutation.data.verified_remote_jobs !== undefined ? (
                    <div>Verified remote jobs: {scrapeMutation.data.verified_remote_jobs}</div>
                  ) : null}
                  {scrapeMutation.data.total_sources !== undefined ? (
                    <div>Sources scanned: {scrapeMutation.data.total_sources}</div>
                  ) : null}
                  {scrapeMutation.data.duration_seconds !== undefined ? (
                    <div>Run time: {scrapeMutation.data.duration_seconds}s</div>
                  ) : null}
                  {scrapeMutation.data.query ? (
                    <div>Search query: {scrapeMutation.data.query}</div>
                  ) : null}
                  {scrapeMutation.data.sources_run?.length ? (
                    <div>Sources: {scrapeMutation.data.sources_run.join(", ")}</div>
                  ) : null}
                </div>
              )}
              {scrapeMutation.error ? (
                <div className="mt-2 rounded border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  {String(scrapeMutation.error)}
                </div>
              ) : null}
            </div>
            <div className="grid gap-3 lg:grid-cols-[1fr_1fr_120px_120px_140px]">
              <label className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Select Job Profile (Optional)
                <select
                  className="mt-1 w-full rounded border border-stone-300 px-3 py-2 text-sm normal-case tracking-normal outline-none focus:border-moss"
                  value={scrapeConfig.job_profile_id || ""}
                  onChange={(event) => {
                    const profileId = event.target.value || undefined;
                    if (profileId) {
                      const profile = profilesQuery.data?.find((p) => p.id === profileId);
                      if (profile) {
                        setScrapeConfig({
                          ...scrapeConfig,
                          job_profile_id: profileId,
                          query: profile.name,
                          min_experience: profile.min_experience,
                          max_experience: profile.max_experience
                        });
                      }
                    } else {
                      setScrapeConfig({
                        ...scrapeConfig,
                        job_profile_id: undefined,
                        query: ""
                      });
                    }
                  }}
                >
                  <option value="">Manual Entry</option>
                  {profilesQuery.data?.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-[11px] text-stone-500">
                  {scrapeConfig.job_profile_id
                    ? "Profile selected: values are auto-filled. You can still edit the fields below."
                    : "Manual entry selected: type your custom job title or keywords below."}
                </p>
              </label>
              <label className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Job title / keywords
                <input
                  className="mt-1 w-full rounded border border-stone-300 px-3 py-2 text-sm normal-case tracking-normal outline-none focus:border-moss"
                  value={scrapeConfig.query}
                  onChange={(event) => setScrapeConfig({ ...scrapeConfig, query: event.target.value, job_profile_id: undefined })}
                  placeholder="DevOps Engineer, SRE, Cloud Engineer"
                />
              </label>
              <NumberField
                label="Min years"
                value={scrapeConfig.min_experience}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, min_experience: value })}
              />
              <NumberField
                label="Max years"
                value={scrapeConfig.max_experience}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, max_experience: value })}
              />
              <NumberField
                label="Posted days"
                value={scrapeConfig.posted_within_days}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, posted_within_days: value })}
              />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <Toggle
                label="Remote only"
                description="Only return jobs that are tagged as remote."
                checked={scrapeConfig.remote_only}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, remote_only: value })}
              />
              <Toggle
                label="Global / India eligible"
                description="Include roles that are globally remote or available to candidates in India."
                checked={scrapeConfig.global_or_india}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, global_or_india: value })}
              />
              <Toggle
                label="Exclude Indian-HQ companies"
                description="Hide opportunities from companies headquartered in India."
                checked={scrapeConfig.exclude_indian_hq}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, exclude_indian_hq: value })}
              />
              <Toggle
                label="Strict title match"
                description="Match the job title more strictly to avoid unrelated senior or non-DevOps listings."
                checked={scrapeConfig.strict_title}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, strict_title: value })}
              />
              <Toggle
                label="Strict experience years"
                description="Enforce the experience range more firmly when filtering results."
                checked={scrapeConfig.strict_experience}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, strict_experience: value })}
              />
              <Toggle
                label="Force junior wording"
                description="Prefer junior-level phrasing in titles and descriptions to reduce senior-level matches."
                checked={scrapeConfig.strict_junior}
                onChange={(value) => setScrapeConfig({ ...scrapeConfig, strict_junior: value })}
              />
            </div>
            <div className="mt-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Sources</div>
              <div className="flex flex-wrap gap-2">
                {sourceOptions.map((source) => (
                  <label key={source.id} className="inline-flex items-center gap-2 rounded border border-stone-200 px-3 py-2 text-sm text-stone-700">
                    <input
                      type="checkbox"
                      checked={scrapeConfig.sources.includes(source.id)}
                      onChange={(event) => {
                        const sources = event.target.checked
                          ? [...scrapeConfig.sources, source.id]
                          : scrapeConfig.sources.filter((id) => id !== source.id);
                        setScrapeConfig({ ...scrapeConfig, sources });
                      }}
                    />
                    {source.label}
                  </label>
                ))}
              </div>
            </div>
            <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-stone-500">
              Extra LinkedIn search URLs
              <textarea
                className="mt-1 min-h-[72px] w-full rounded border border-stone-300 px-3 py-2 text-sm normal-case tracking-normal outline-none focus:border-moss"
                value={linkedinUrlText}
                onChange={(event) => setLinkedinUrlText(event.target.value)}
                placeholder="Optional: paste one public LinkedIn jobs search URL per line"
              />
            </label>
            <button
              className="mt-4 flex w-full items-center justify-center gap-2 rounded bg-coral px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#ad4938] disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => scrapeMutation.mutate()}
              disabled={scrapeMutation.isPending}
            >
              {scrapeMutation.isPending ? (
                <>
                  <RefreshCcw className="h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run Scraper
                </>
              )}
            </button>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <div className="grid gap-3 md:grid-cols-[1fr_180px_180px_160px]">
              <input
                className="rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                placeholder="Search title, company, description"
                value={filters.search}
                onChange={(event) => setFilters({ ...filters, search: event.target.value })}
              />
              <select
                className="rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                value={filters.tech_stack}
                onChange={(event) => setFilters({ ...filters, tech_stack: event.target.value })}
              >
                {stackOptions.map((option) => <option key={option} value={option}>{option || "All stacks"}</option>)}
              </select>
              <select
                className="rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                value={filters.company_size}
                onChange={(event) => setFilters({ ...filters, company_size: event.target.value })}
              >
                {sizeOptions.map((option) => <option key={option} value={option}>{option || "All company sizes"}</option>)}
              </select>
              <select
                className="rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                value={filters.is_applied}
                onChange={(event) => setFilters({ ...filters, is_applied: event.target.value })}
              >
                <option value="">All statuses</option>
                <option value="false">Not applied</option>
                <option value="true">Applied</option>
              </select>
            </div>
          </section>

          {jobsQuery.isLoading ? (
            <div className="rounded-lg border border-stone-200 bg-white p-10 text-center text-sm text-stone-600">Loading job matches...</div>
          ) : jobsQuery.error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-800">{String(jobsQuery.error)}</div>
          ) : (
            <JobTable jobs={jobs} />
          )}
        </section>

        <aside className="space-y-5">
          <section className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-cyan-50 p-5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.18)]">
            <h2 className="text-sm font-semibold text-ink">Company Intelligence</h2>
            <div className="mt-4 space-y-3">
              <input
                className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                placeholder="Search company name"
                value={companySearchTerm}
                onChange={(event) => {
                  setCompanySearchTerm(event.target.value);
                  setSelectedCompanyName("");
                }}
              />
              {companySearchTerm.trim() ? (
                companySearchQuery.isFetching ? (
                  <div className="rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm text-stone-600">Searching companies…</div>
                ) : companySearchQuery.error ? (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">Unable to search companies.</div>
                ) : (
                  <div className="space-y-2">
                    {(companySearchQuery.data ?? []).slice(0, 6).map((company: any) => (
                      <button
                        key={company.name || company.id}
                        type="button"
                        className="w-full rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-left text-sm text-ink transition hover:bg-stone-100"
                        onClick={() => setSelectedCompanyName(company.name)}
                      >
                        {company.name}
                        {company.industry ? <span className="ml-2 text-xs text-stone-500">· {company.industry}</span> : null}
                      </button>
                    ))}
                    {!companySearchQuery.data?.length && (
                      <p className="text-sm text-stone-600">No matching companies found yet.</p>
                    )}
                  </div>
                )
              ) : (
                <div className="space-y-3 rounded-2xl border border-stone-200 bg-slate-50 p-4">
                  <p className="text-sm text-stone-700">Top employers with current remote listings.</p>
                  <div className="grid gap-2">
                    {(companiesQuery.data ?? []).slice(0, 5).map((company: any) => (
                      <button
                        key={company.name || company.id}
                        type="button"
                        className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-left text-sm text-ink transition hover:border-sky-400 hover:bg-sky-50"
                        onClick={() => {
                          setSelectedCompanyName(company.name);
                          setCompanySearchTerm(company.name);
                        }}
                      >
                        <div className="font-semibold">{company.name}</div>
                        {company.industry ? <div className="text-xs text-stone-500">{company.industry}</div> : null}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {companyProfileQuery.data && selectedCompanyName ? (
                <div className="rounded-3xl border border-stone-200 bg-slate-50 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{companyProfileQuery.data.profile?.name ?? selectedCompanyName}</p>
                      <p className="text-xs text-stone-500">{companyProfileQuery.data.profile?.industry ?? "Remote-friendly employer"}</p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${companyProfileQuery.data.profile?.is_verified ? "bg-moss/10 text-moss" : "bg-stone-100 text-stone-600"}`}>
                      {companyProfileQuery.data.profile?.is_verified ? "Verified" : "Unverified"}
                    </span>
                  </div>
                  <p className="mb-3 text-sm leading-6 text-stone-700">{companyProfileQuery.data.profile?.description ?? "No description available for this company yet."}</p>
                  <div className="grid gap-2 sm:grid-cols-2 text-sm text-stone-700">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">HQ</p>
                      <p className="mt-1">{companyProfileQuery.data.profile?.headquarters ?? "N/A"}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Size</p>
                      <p className="mt-1">{companyProfileQuery.data.profile?.company_size ?? "N/A"}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Remote policy</p>
                      <p className="mt-1">{companyProfileQuery.data.profile?.remote_policy ?? "Flexible / remote friendly"}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-stone-500">Open jobs</p>
                      <p className="mt-1">{companyProfileQuery.data.stats?.open_jobs ?? companyProfileQuery.data.recent_jobs?.length ?? "—"}</p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-white/95 p-5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.18)] backdrop-blur-md">
            <h2 className="text-sm font-semibold text-ink">Apply Helper</h2>
            <div className="mt-4 space-y-3">
              <input
                className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                placeholder="Template name"
                value={template.name}
                onChange={(event) => setTemplate({ ...template, name: event.target.value })}
              />
              <input
                className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                placeholder="Company type"
                value={template.company_type}
                onChange={(event) => setTemplate({ ...template, company_type: event.target.value })}
              />
              <textarea
                className="min-h-[220px] w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-moss"
                value={template.content}
                onChange={(event) => setTemplate({ ...template, content: event.target.value })}
              />
              <button
                className="w-full rounded bg-moss px-4 py-2 text-sm font-semibold text-white hover:bg-[#285d50] disabled:opacity-60"
                disabled={!template.name || !template.content || templateMutation.isPending}
                onClick={() => templateMutation.mutate(template)}
              >
                Save Template
              </button>
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-white/95 p-5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.18)] backdrop-blur-md">
            <h2 className="text-sm font-semibold text-ink">Saved Templates</h2>
            <div className="mt-3 space-y-3">
              {(templatesQuery.data ?? []).map((item) => (
                <details key={item.id} className="rounded border border-stone-200 p-3">
                  <summary className="flex items-center justify-between cursor-pointer text-sm font-semibold text-ink">
                    <span>{item.name}</span>
                    <button
                      type="button"
                      className="rounded bg-rose-500 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-600"
                      onClick={(event) => {
                        event.stopPropagation();
                        deleteTemplateMutation.mutate(item.id);
                      }}
                      disabled={deleteTemplateMutation.isPending}
                    >
                      Remove
                    </button>
                  </summary>
                  <pre className="mt-3 whitespace-pre-wrap text-xs leading-5 text-stone-700">{item.content}</pre>
                </details>
              ))}
              {!templatesQuery.data?.length && <p className="text-sm text-stone-600">No templates saved yet.</p>}
            </div>
          </section>

          <section className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-sky-50 p-5 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.18)]">
            <h2 className="text-sm font-semibold text-ink">Remote source pulse</h2>
            <p className="mt-2 text-sm text-stone-600">
              Track where your best remote roles are coming from and use the source list to tune coverage.
            </p>
            <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
              {activeSources.slice(0, 5).map(([source, count]) => (
                <div key={source} className="min-w-[110px] rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-stone-700">
                  <div className="font-semibold">{source}</div>
                  <div className="mt-1 text-xs text-stone-500">{count} jobs</div>
                </div>
              ))}
            </div>
            <div className="mt-4 overflow-hidden rounded-[1.75rem] border border-slate-100 bg-white/90 shadow-sm">
              <div className="max-h-[260px] overflow-y-auto text-sm text-stone-700">
                {Object.entries(stats?.by_source ?? {}).length ? (
                  Object.entries(stats?.by_source ?? {}).map(([source, count]) => (
                    <div key={source} className="flex items-center justify-between border-b border-slate-100 px-4 py-4 last:border-b-0 hover:bg-slate-50 transition">
                      <div>
                        <p className="font-semibold text-ink">{source}</p>
                        <p className="text-xs text-stone-500">Latest remote match source</p>
                      </div>
                      <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-stone-700">{count}</div>
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-sm text-stone-600">No source activity yet. Run a scrape to populate the source panel and discover which job boards are most effective.</div>
                )}
              </div>
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}

function Metric({ label, value, icon }: { label: string; value: string | number; icon: ReactNode }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between text-stone-500">
        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
        {icon}
      </div>
      <div className="mt-3 text-2xl font-bold text-ink">{value}</div>
    </section>
  );
}

function NumberField({
  label,
  value,
  onChange
}: {
  label: string;
  value?: number | null;
  onChange: (value: number | null) => void;
}) {
  return (
    <label className="text-xs font-semibold uppercase tracking-wide text-stone-500">
      {label}
      <input
        className="mt-1 w-full rounded border border-stone-300 px-3 py-2 text-sm normal-case tracking-normal outline-none focus:border-moss"
        type="number"
        min="0"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
      />
    </label>
  );
}

function Toggle({
  label,
  checked,
  onChange,
  description
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  description?: string;
}) {
  return (
    <label
      className="flex items-center justify-between gap-3 rounded border border-stone-200 px-3 py-2 text-sm text-stone-700"
      title={description}
    >
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}
