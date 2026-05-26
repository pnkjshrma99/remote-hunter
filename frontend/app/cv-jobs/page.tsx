"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, TrendingUp, Target, Sparkles, ArrowRight, Filter } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getMyCVs, getMatchedJobs } from "@/lib/api";

export default function CVJobsPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const queryClient = useQueryClient();
  const [selectedCV, setSelectedCV] = useState<number | null>(null);
  const [minMatchScore, setMinMatchScore] = useState(50);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const cvsQuery = useQuery({
    queryKey: ["my-cvs"],
    queryFn: getMyCVs,
    enabled: isAuthenticated
  });

  const matchedJobsQuery = useQuery({
    queryKey: ["matched-jobs", selectedCV],
    queryFn: () => selectedCV ? getMatchedJobs(selectedCV) : [],
    enabled: isAuthenticated && selectedCV !== null
  });

  const filteredJobs = matchedJobsQuery.data?.filter(
    (job: any) => job.match_score >= minMatchScore
  ) || [];

  // Reset to page 1 when filters change
  const handleFilterChange = (newScore: number) => {
    setMinMatchScore(newScore);
    setCurrentPage(1);
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
  };

  // Calculate pagination
  const totalPages = Math.ceil(filteredJobs.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedJobs = filteredJobs.slice(startIndex, endIndex);

  // Reset page when CV changes
  const handleCVChange = (cvId: number) => {
    setSelectedCV(cvId);
    setCurrentPage(1);
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-600">Loading...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-lg">
          <h2 className="mb-4 text-2xl font-semibold text-slate-900">Sign in to view CV-based jobs</h2>
          <p className="mb-6 text-sm text-slate-600">Upload your CV to get personalized job recommendations.</p>
          <Link href="/login" className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-5 sm:py-8">
        {/* Header */}
        <div className="mb-6 rounded-[2rem] border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-6 shadow-lg sm:p-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4 max-w-2xl">
              <div className="relative">
                <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 opacity-20 blur-sm"></div>
                <img src="/logo.svg" alt="Remote Job Hunter Logo" className="relative h-16 w-16 flex-shrink-0" />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-indigo-600">AI-Powered Recommendations</p>
                <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">CV-Based Job Matches</h1>
                <p className="text-sm leading-7 text-slate-600">
                  Jobs automatically matched to your CV skills, experience, and tech stack. Sorted by relevance.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/cv-upload" className="rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Upload CV
              </Link>
              <Link href="/scraper" className="rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Scraper
              </Link>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
          {/* Left Sidebar - CV Selection */}
          <aside className="space-y-5">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Select CV</h2>
              
              {cvsQuery.isLoading ? (
                <div className="py-4 text-center text-sm text-slate-500">Loading...</div>
              ) : cvsQuery.data && cvsQuery.data.length > 0 ? (
                <div className="space-y-2">
                  {cvsQuery.data.map((cv: any) => (
                    <button
                      key={cv.id}
                      onClick={() => handleCVChange(cv.id)}
                      className={`w-full rounded-xl border p-3 text-left transition-colors ${
                        selectedCV === cv.id
                          ? "border-indigo-500 bg-indigo-50"
                          : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/30"
                      }`}
                    >
                      <div className="text-sm font-medium text-slate-900">{cv.file_name}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {cv.tech_stack?.length || 0} technologies • {cv.job_roles?.length || 0} roles • {cv.experience_years || 0} years exp
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center">
                  <p className="text-sm text-slate-500">No CVs uploaded</p>
                  <Link href="/cv-upload" className="mt-2 inline-block text-xs text-indigo-600 hover:text-indigo-700">
                    Upload your first CV →
                  </Link>
                </div>
              )}
            </div>

            {/* Filter Card */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-slate-950">Filter by Match Score</h3>
              <div className="space-y-3">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={minMatchScore}
                  onChange={(e) => handleFilterChange(Number(e.target.value))}
                  className="w-full"
                />
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <span>0%</span>
                  <span className="font-semibold text-indigo-600">{minMatchScore}%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>

            {/* Stats Card */}
            {selectedCV && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="mb-3 text-sm font-semibold text-slate-950">Match Statistics</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-600">Total Matches</span>
                    <span className="text-sm font-semibold text-slate-900">{filteredJobs.length}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-600">High Match (80%+)</span>
                    <span className="text-sm font-semibold text-green-600">
                      {filteredJobs.filter((j: any) => j.match_score >= 80).length}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-600">Medium Match (50-79%)</span>
                    <span className="text-sm font-semibold text-amber-600">
                      {filteredJobs.filter((j: any) => j.match_score >= 50 && j.match_score < 80).length}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </aside>

          {/* Main Content - Job Matches */}
          <section className="space-y-5">
            {!selectedCV ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-12 shadow-sm text-center">
                <Target className="mx-auto mb-4 h-16 w-16 text-slate-300" />
                <h3 className="text-lg font-semibold text-slate-900">Select a CV to see matched jobs</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Choose a CV from the sidebar to view jobs that match your skills and experience.
                </p>
              </div>
            ) : matchedJobsQuery.isLoading ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-12 shadow-sm text-center">
                <Sparkles className="mx-auto h-8 w-8 animate-spin text-indigo-600" />
                <p className="mt-3 text-sm text-slate-600">Finding your perfect matches...</p>
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-12 shadow-sm text-center">
                <TrendingUp className="mx-auto mb-4 h-16 w-16 text-slate-300" />
                <h3 className="text-lg font-semibold text-slate-900">No matches found</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Try lowering the match score filter or upload a different CV.
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  {paginatedJobs.map((job: any) => (
                    <JobMatchCard key={job.job_id} job={job} />
                  ))}
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <span>Page {currentPage} of {totalPages}</span>
                        <span className="text-slate-400">•</span>
                        <span>{startIndex + 1}-{Math.min(endIndex, filteredJobs.length)} of {filteredJobs.length}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <select
                          value={pageSize}
                          onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                        >
                          <option value={5}>5 per page</option>
                          <option value={10}>10 per page</option>
                          <option value={50}>50 per page</option>
                          <option value={100}>100 per page</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                        disabled={currentPage === 1}
                        className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
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
                              onClick={() => setCurrentPage(pageNum)}
                              className={`rounded-lg px-3 py-2 text-sm font-medium ${
                                currentPage === pageNum
                                  ? "bg-indigo-600 text-white"
                                  : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                              }`}
                            >
                              {pageNum}
                            </button>
                          );
                        })}
                      </div>
                      <button
                        onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                        disabled={currentPage === totalPages}
                        className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function JobMatchCard({ job }: { job: any }) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-amber-500";
    return "bg-slate-500";
  };

  const getScoreLabel = (score: number) => {
    if (score >= 80) return "Excellent";
    if (score >= 60) return "Good";
    if (score >= 40) return "Fair";
    return "Low";
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${getScoreColor(job.match_score)} text-white font-bold text-lg`}>
                {job.match_score}
              </div>
              <div className="mt-1 text-center text-[10px] font-medium text-slate-500">{getScoreLabel(job.match_score)}</div>
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-slate-900">{job.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{job.company}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {job.tech_stack && job.tech_stack.split(",").slice(0, 4).map((tech: string) => (
                  <span key={tech} className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                    {tech.trim()}
                  </span>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
                <span>{job.location}</span>
                <span>•</span>
                <span>Matched: {job.skills_matched?.length || 0} skills</span>
                {job.skills_missing && job.skills_missing.length > 0 && (
                  <>
                    <span>•</span>
                    <span className="text-amber-600">Missing: {job.skills_missing.length} skills</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          className="flex-shrink-0 rounded-xl bg-slate-900 p-3 text-white hover:bg-slate-800 transition-colors"
        >
          <ExternalLink className="h-5 w-5" />
        </a>
      </div>
    </div>
  );
}
