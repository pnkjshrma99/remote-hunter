"use client";

import { ExternalLink, CheckCircle2, Circle, Search } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { markApplied } from "@/lib/api";
import { Job } from "@/types/job";

export function JobTable({ jobs }: { jobs: Job[] }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, applied }: { id: number; applied: boolean }) => markApplied(id, applied),
    onSuccess: () => queryClient.invalidateQueries()
  });

  if (!jobs.length) {
    return (
      <div className="flex min-h-[280px] items-center justify-center rounded-lg border border-dashed border-stone-300 bg-white">
        <div className="text-center text-sm text-stone-600">
          <Search className="mx-auto mb-3 h-8 w-8 text-stone-400" />
          No matching jobs yet. Run a scrape or loosen the filters.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-stone-200 bg-white shadow-sm overflow-x-auto">
      <div className="max-h-[620px] overflow-auto">
        <table className="w-full min-w-full table-auto text-left text-sm">
          <thead className="sticky top-0 bg-stone-100 text-xs uppercase tracking-wide text-stone-600">
            <tr>
              <th className="w-12 px-3 py-3">Track</th>
              <th className="px-3 py-3">Role</th>
              <th className="px-3 py-3">Company</th>
              <th className="px-3 py-3">Stack</th>
              <th className="px-3 py-3">Eligibility</th>
              <th className="px-3 py-3">Source</th>
              <th className="px-3 py-3">Posted</th>
              <th className="w-24 px-3 py-3">Apply</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {jobs.map((job) => (
              <tr key={job.id} className="hover:bg-stone-50">
                <td className="px-3 py-3">
                  <button
                    className="rounded p-1 text-moss hover:bg-green-50"
                    title={job.is_applied ? "Mark as not applied" : "Mark as applied"}
                    onClick={() => mutation.mutate({ id: job.id, applied: !job.is_applied })}
                  >
                    {job.is_applied ? <CheckCircle2 className="h-5 w-5" /> : <Circle className="h-5 w-5" />}
                  </button>
                </td>
                <td className="px-3 py-3">
                  <div className="font-semibold text-ink">{job.title}</div>
                  <div className="mt-1 text-xs text-stone-500">{job.experience_level || "Unspecified"}</div>
                </td>
                <td className="px-3 py-3 text-stone-700">{job.company}</td>
                <td className="px-3 py-3">
                  <div className="flex max-w-[260px] flex-wrap gap-1">
                    {(job.tech_stack || "Unknown").split(",").map((tech) => (
                      <span key={`${job.id}-${tech}`} className="rounded bg-stone-100 px-2 py-1 text-xs text-stone-700">
                        {tech.trim()}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <div className="text-stone-700">{job.region_eligibility}</div>
                  <div className="mt-1 max-w-[220px] truncate text-xs text-stone-500">{job.location}</div>
                </td>
                <td className="px-3 py-3 text-stone-600">{job.source}</td>
                <td className="px-3 py-3 text-stone-600">{formatDate(job.posted_at || job.scraped_at)}</td>
                <td className="px-3 py-3">
                  <a
                    className="inline-flex items-center gap-1 rounded bg-ink px-3 py-2 text-xs font-semibold text-white hover:bg-moss"
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Apply <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}
