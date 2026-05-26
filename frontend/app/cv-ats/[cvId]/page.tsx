"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BadgeCheck, BriefcaseBusiness, CheckCircle, FileText, Lightbulb, Target, Trophy } from "lucide-react";
import { getCV } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function CVATSPage() {
  const params = useParams();
  const cvId = Number(params.cvId);
  const { isAuthenticated, isLoading } = useAuth();

  const cvQuery = useQuery({
    queryKey: ["cv", cvId],
    queryFn: () => getCV(cvId),
    enabled: isAuthenticated && Number.isFinite(cvId),
  });

  if (isLoading || cvQuery.isLoading) {
    return <div className="p-8 text-center text-slate-600">Loading ATS analysis...</div>;
  }

  if (!isAuthenticated) {
    const nextPath = `/cv-ats/${cvId}`;
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold text-slate-950">Sign in to view ATS analysis</h1>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Link href={`/login?next=${encodeURIComponent(nextPath)}`} className="inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
              Sign in
            </Link>
            <Link href={`/register?next=${encodeURIComponent(nextPath)}`} className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              Create account
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const cv = cvQuery.data;
  const analysis = cv?.ats_analysis || cv?.parsed_data?.ats_analysis;
  const score = analysis?.score ?? cv?.ats_score ?? 0;

  if (!cv) {
    return <div className="p-8 text-center text-slate-600">CV not found</div>;
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-5">
          <Link href="/cv-upload" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950">
            <ArrowLeft className="h-4 w-4" />
            Back to CVs
          </Link>
        </div>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                  <Trophy className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase text-emerald-700">ATS Score Analysis</p>
                  <h1 className="mt-1 truncate text-2xl font-bold text-slate-950">{cv.file_name}</h1>
                </div>
              </div>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
                This score is calculated from extracted CV structure, skills depth, role alignment, experience clarity, keyword coverage, and credentials.
              </p>
            </div>
            <div className={`rounded-2xl px-6 py-5 text-center ${getScorePanelClass(score)}`}>
              <p className="text-xs font-semibold uppercase">Current ATS</p>
              <p className="mt-1 text-4xl font-black">{score}/100</p>
              <p className="mt-1 text-sm font-semibold">{analysis?.rating || getRating(score)}</p>
            </div>
          </div>
        </section>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section className="space-y-5">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Target className="h-5 w-5 text-slate-900" />
                <h2 className="text-lg font-semibold text-slate-950">Score Breakdown</h2>
              </div>
              <div className="space-y-4">
                {(analysis?.breakdown || []).map((item: any) => {
                  const percent = Math.round((item.score / item.max_score) * 100);
                  return (
                    <div key={item.label}>
                      <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                        <span className="font-semibold text-slate-800">{item.label}</span>
                        <span className="text-slate-500">{item.score}/{item.max_score}</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100">
                        <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${percent}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-slate-900" />
                <h2 className="text-lg font-semibold text-slate-950">Recommendations</h2>
              </div>
              <div className="space-y-3">
                {(analysis?.recommendations || []).map((recommendation: string) => (
                  <div key={recommendation} className="flex gap-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                    <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>{recommendation}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="space-y-5">
            <SignalCard icon={FileText} label="Tech stack" value={analysis?.signals?.tech_stack || 0} />
            <SignalCard icon={BadgeCheck} label="Skills" value={analysis?.signals?.skills || 0} />
            <SignalCard icon={BriefcaseBusiness} label="Job roles" value={analysis?.signals?.job_roles || 0} />
            <SignalCard icon={Target} label="Keywords" value={analysis?.signals?.keywords || 0} />
          </aside>
        </div>
      </div>
    </main>
  );
}

function SignalCard({ icon: Icon, label, value }: { icon: any; label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function getRating(score: number) {
  if (score >= 80) return "Strong";
  if (score >= 60) return "Good";
  return "Needs work";
}

function getScorePanelClass(score: number) {
  if (score >= 80) return "bg-emerald-100 text-emerald-900";
  if (score >= 60) return "bg-amber-100 text-amber-900";
  return "bg-red-100 text-red-900";
}
