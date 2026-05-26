"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles, TrendingUp, Code, Award, Calendar, ExternalLink } from "lucide-react";
import { getCV, getMatchedJobs } from "@/lib/api";
import { TechStackDisplay } from "./tech-stack-display";

interface CVAnalysisProps {
  cvId: number;
  cvFileName: string;
}

export function CVAnalysis({ cvId, cvFileName }: CVAnalysisProps) {
  const [showAllJobs, setShowAllJobs] = useState(false);

  const cvQuery = useQuery({
    queryKey: ["cv", cvId],
    queryFn: () => getCV(cvId),
  });

  const matchedJobsQuery = useQuery({
    queryKey: ["matched-jobs", cvId],
    queryFn: () => getMatchedJobs(cvId),
  });

  const cv = cvQuery.data;
  const matchedJobs = matchedJobsQuery.data || [];
  const displayJobs = showAllJobs ? matchedJobs : matchedJobs.slice(0, 5);

  if (cvQuery.isLoading) {
    return <div className="py-8 text-center text-slate-600">Loading CV analysis...</div>;
  }

  if (!cv) {
    return <div className="py-8 text-center text-slate-600">CV not found</div>;
  }

  return (
    <div className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {/* CV Header */}
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xl font-bold text-slate-900">{cvFileName}</h3>
            <p className="mt-1 text-sm text-slate-600">CV Profile Analysis</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-3 py-1">
            <Sparkles size={14} className="text-indigo-600" />
            <span className="text-xs font-semibold text-indigo-600">AI Analyzed</span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-600">Experience</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {cv.experience_years || 0}
              <span className="text-sm text-slate-600"> years</span>
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-600">Tech Stack</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {cv.tech_stack?.length || 0}
              <span className="text-sm text-slate-600"> skills</span>
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-600">Job Roles</p>
            <p className="mt-1 text-xl font-bold text-slate-900">
              {cv.job_roles?.length || 0}
              <span className="text-sm text-slate-600"> roles</span>
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-indigo-50 p-3">
            <p className="text-xs text-indigo-700">Matched Jobs</p>
            <p className="mt-1 text-xl font-bold text-indigo-900">
              {matchedJobs.length}
              <span className="text-sm text-indigo-700"> found</span>
            </p>
          </div>
        </div>
      </div>

      {/* Tech Stack Section */}
      {cv.tech_stack && cv.tech_stack.length > 0 && (
        <div className="space-y-3 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-2">
            <Code size={18} className="text-slate-900" />
            <h4 className="font-semibold text-slate-900">Tech Stack ({cv.tech_stack.length})</h4>
          </div>
          <TechStackDisplay techs={cv.tech_stack} maxVisible={8} />
        </div>
      )}

      {/* Job Roles Section */}
      {cv.job_roles && cv.job_roles.length > 0 && (
        <div className="space-y-3 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-2">
            <Award size={18} className="text-slate-900" />
            <h4 className="font-semibold text-slate-900">Job Roles ({cv.job_roles.length})</h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {cv.job_roles.map((role: string) => (
              <span
                key={role}
                className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
              >
                {role}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Matched Jobs Section */}
      {matchedJobs.length > 0 && (
        <div className="space-y-4 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={18} className="text-slate-900" />
            <h4 className="font-semibold text-slate-900">Top Matches</h4>
          </div>
          <div className="space-y-3">
            {displayJobs.map((job: any, index: number) => (
              <div key={job.id || job.url || `${job.title}-${index}`} className="rounded-lg border border-slate-200 p-4 hover:border-indigo-300 hover:bg-indigo-50/30">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h5 className="font-semibold text-slate-900">{job.title}</h5>
                    <p className="text-sm text-slate-600">{job.company}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {job.match_score && (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">
                          {job.match_score}% match
                        </span>
                      )}
                      {job.posted_at && (
                        <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                          <Calendar size={12} />
                          {new Date(job.posted_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
                  >
                    <ExternalLink size={16} />
                  </a>
                </div>
              </div>
            ))}
          </div>
          {matchedJobs.length > 5 && (
            <button
              onClick={() => setShowAllJobs(!showAllJobs)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              {showAllJobs ? "Show less" : `View all ${matchedJobs.length} matches`}
            </button>
          )}
        </div>
      )}

      {matchedJobs.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-6 text-center">
          <p className="text-sm text-slate-600">No matching jobs found yet. Run the scraper to find jobs.</p>
        </div>
      )}
    </div>
  );
}
