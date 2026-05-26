"use client";

import { ExternalLink, CheckCircle2, Circle, Search, MapPin, Building2, Clock, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { markApplied } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Job } from "@/types/job";

export function JobTable({ jobs }: { jobs: Job[] }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, applied }: { id: number; applied: boolean }) => markApplied(id, applied),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs", user?.id] });
      queryClient.invalidateQueries({ queryKey: ["stats", user?.id] });
    }
  });

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Calculate pagination
  const totalPages = Math.ceil(jobs.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedJobs = jobs.slice(startIndex, endIndex);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleItemsPerPageChange = (value: number) => {
    setItemsPerPage(value);
    setCurrentPage(1); // Reset to first page when changing items per page
  };

  if (!jobs.length) {
    return (
      <div className="flex min-h-[240px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white/50">
        <div className="text-center">
          <Search className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          <p className="text-sm font-medium text-slate-500">No jobs match your filters</p>
          <p className="mt-1 text-xs text-slate-400">Try a different search or run a fresh scrape.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/80">
              <th className="w-10 px-3 py-3 text-center">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Done</span>
              </th>
              <th className="px-3 py-3 text-left">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Position</span>
              </th>
              <th className="px-3 py-3 text-left">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Company</span>
              </th>
              <th className="px-3 py-3 text-left">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Stack</span>
              </th>
              <th className="px-3 py-3 text-left">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Location</span>
              </th>
              <th className="px-3 py-3 text-left">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Source</span>
              </th>
              <th className="px-3 py-3 text-left">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Posted</span>
              </th>
              <th className="w-14 px-2 py-3 text-center">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Open</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {paginatedJobs.map((job) => (
              <tr
                key={job.id}
                className={`group transition-colors hover:bg-indigo-50/40 ${job.is_applied ? "bg-green-50/30" : ""}`}
              >
                {/* Checkmark */}
                <td className="px-3 py-3 text-center">
                  <button
                    className="rounded-lg p-1.5 transition-colors hover:bg-white"
                    title={job.is_applied ? "Mark as not applied" : "Mark as applied"}
                    onClick={() => mutation.mutate({ id: job.id, applied: !job.is_applied })}
                  >
                    {job.is_applied ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <Circle className="h-4 w-4 text-slate-300 group-hover:text-slate-400" />
                    )}
                  </button>
                </td>

                {/* Position */}
                <td className="px-3 py-3">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-sm font-medium text-slate-800">{job.title}</span>
                    <div className="flex items-center gap-1">
                      {job.is_hot_job && (
                        <span className="inline-flex items-center rounded-full bg-gradient-to-r from-orange-400 to-rose-500 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                          🔥 Hot
                        </span>
                      )}
                      {job.is_verified_remote && (
                        <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                          ✓ Remote
                        </span>
                      )}
                      {job.is_sponsored && (
                        <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                          Sponsored
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
                    {job.experience_level && (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {job.experience_level}
                      </span>
                    )}
                    {job.seniority_tag && (
                      <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
                        {job.seniority_tag}
                      </span>
                    )}
                    {job.is_duplicate && (
                      <span className="flex items-center gap-1 text-amber-500">
                        <AlertCircle className="h-3 w-3" />
                        Duplicate
                      </span>
                    )}
                  </div>
                </td>

                {/* Company */}
                <td className="px-3 py-3">
                  <div className="flex items-center gap-1.5">
                    <Building2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    <span className="text-sm text-slate-700 truncate max-w-[120px]">{job.company}</span>
                  </div>
                </td>

                {/* Stack */}
                <td className="px-3 py-3">
                  <div className="flex max-w-[140px] flex-wrap gap-1">
                    {(job.tech_stack || "").split(",").slice(0, 3).map((tech) => (
                      <span
                        key={`${job.id}-${tech}`}
                        className="rounded-md bg-gradient-to-b from-slate-50 to-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 ring-1 ring-slate-200/50"
                      >
                        {tech.trim()}
                      </span>
                    ))}
                    {(job.tech_stack || "").split(",").length > 3 && (
                      <span className="text-[10px] text-slate-400">+{job.tech_stack!.split(",").length - 3}</span>
                    )}
                  </div>
                </td>

                {/* Location / Region */}
                <td className="px-3 py-3">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    <span className="text-sm text-slate-600 truncate max-w-[100px]">{job.region_eligibility || job.location || "Remote"}</span>
                  </div>
                </td>

                {/* Source */}
                <td className="px-3 py-3">
                  <span className="inline-flex items-center rounded-md bg-indigo-50 px-2 py-1 text-[11px] font-medium text-indigo-600 ring-1 ring-indigo-100/50">
                    {job.source}
                  </span>
                </td>

                {/* Posted */}
                <td className="px-3 py-3">
                  <span className="whitespace-nowrap text-sm text-slate-500">{formatDate(job.posted_at || job.scraped_at)}</span>
                </td>

                {/* Open */}
                <td className="px-2 py-3 text-center">
                  <a
                    className="inline-flex items-center justify-center rounded-lg bg-slate-800 p-2 text-white shadow-sm transition-all hover:bg-slate-700 hover:shadow-md active:scale-95"
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    title="Open job posting"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="border-t border-slate-100 bg-slate-50/50 px-4 py-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {/* Items per page dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Show</span>
            <select
              value={itemsPerPage}
              onChange={(e) => handleItemsPerPageChange(Number(e.target.value))}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
            <span className="text-xs text-slate-500">per page</span>
          </div>

          {/* Page info and navigation */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">
              Showing {startIndex + 1} to {Math.min(endIndex, jobs.length)} of {jobs.length} jobs
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700 disabled:opacity-40 disabled:hover:bg-white disabled:hover:text-slate-400"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              {/* Page numbers */}
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => handlePageChange(pageNum)}
                      className={`min-w-[32px] rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
                        currentPage === pageNum
                          ? "bg-indigo-600 text-white shadow-sm"
                          : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700 disabled:opacity-40 disabled:hover:bg-white disabled:hover:text-slate-400"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(d);
  } catch {
    return "—";
  }
}