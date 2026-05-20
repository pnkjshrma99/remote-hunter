"use client";

import { Bell, BriefcaseBusiness, Filter, Mail, Play, RefreshCcw } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ChartCard } from "@/components/chart-card";
import { JobTable } from "@/components/job-table";
import { createCoverLetter, deleteCoverLetter, getCoverLetters, getJobs, getStats, runScrape, ScrapeConfig } from "@/lib/api";

const stackOptions = ["", "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform", "CI/CD", "Python", "Linux"];
const sizeOptions = ["", "Startup", "Mid-size", "Enterprise"];
const sourceOptions = [
  { id: "remotive", label: "Remotive" },
  { id: "remoteok", label: "Remote OK" },
  { id: "weworkremotely", label: "WWR" },
  { id: "workingnomads", label: "Working Nomads" },
  { id: "greenhouse", label: "Greenhouse" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "arbeitnow", label: "Arbeitnow" }
];

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

  const jobsQuery = useQuery({ queryKey: ["jobs", filters], queryFn: () => getJobs(filters) });
  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const templatesQuery = useQuery({ queryKey: ["cover-letters"], queryFn: getCoverLetters });
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

  return (
    <main className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-ink">Remote Job Hunter</h1>
            <p className="mt-1 text-sm text-stone-600">Runtime search for remote roles across multiple job boards.</p>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1500px] gap-5 px-5 py-5 xl:grid-cols-[1fr_360px]">
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

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-ink">Scrape Config</h2>
              {scrapeMutation.data && (
                <span className="text-xs text-stone-600">
                  Found {scrapeMutation.data.jobs_found ?? 0}, new {scrapeMutation.data.jobs_new ?? 0}
                </span>
              )}
            </div>
            <div className="grid gap-3 lg:grid-cols-[1fr_120px_120px_140px]">
              <label className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                Job title / keywords
                <input
                  className="mt-1 w-full rounded border border-stone-300 px-3 py-2 text-sm normal-case tracking-normal outline-none focus:border-moss"
                  value={scrapeConfig.query}
                  onChange={(event) => setScrapeConfig({ ...scrapeConfig, query: event.target.value })}
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
          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
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

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
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

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-ink">Sources</h2>
            <div className="mt-3 space-y-2 text-sm text-stone-700">
              {Object.entries(stats?.by_source ?? {}).map(([source, count]) => (
                <div key={source} className="flex justify-between border-b border-stone-100 pb-2">
                  <span>{source}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))}
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
