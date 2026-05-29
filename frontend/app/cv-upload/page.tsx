"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, Sparkles, BarChart3, Trophy, BriefcaseBusiness, GitCompare, CalendarDays, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { uploadCV, getMyCVs, deleteCV, matchJobsForCV, getCV } from "@/lib/api";
import { CVAnalysis } from "@/components/cv-analysis";
import { TechStackDisplay } from "@/components/tech-stack-display";

type MatchResult = {
  cvId: number;
  fileName: string;
  matchesCount: number;
  scrapedJobs: number;
};

export default function CVUploadPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedCVId, setSelectedCVId] = useState<number | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);

  const cvsQuery = useQuery({
    queryKey: ["my-cvs"],
    queryFn: getMyCVs,
    enabled: isAuthenticated
  });

  const uploadMutation = useMutation({
    mutationFn: uploadCV,
    onSuccess: (data: any) => {
      // If async parsing, poll until complete
      if (data.status === "pending") {
        const cvId = data.id;
        const poll = setInterval(async () => {
          try {
            const cv = await getCV(cvId);
            if (cv.parsed_data?.status === "completed" || cv.parsed_data?.status === "failed") {
              clearInterval(poll);
              queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
            }
          } catch {
            clearInterval(poll);
          }
        }, 1000);
      } else {
        queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
      }
      setFile(null);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCV,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
    }
  });

  const matchMutation = useMutation({
    mutationFn: (cv: any) => matchJobsForCV(cv.id).then((data) => ({ data, cv })),
    onSuccess: ({ data, cv }: any) => {
      queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
      queryClient.invalidateQueries({ queryKey: ["matched-jobs", cv.id] });
      setMatchResult({
        cvId: cv.id,
        fileName: cv.file_name,
        matchesCount: data.matches_count,
        scrapedJobs: data.scraped_jobs,
      });
    },
    onError: (error) => {
      alert(`Failed to match jobs: ${error.message}`);
    }
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  const cvs = cvsQuery.data || [];
  const stats = buildCVStats(cvs);
  const comparisonCVs = compareIds
    .map((id) => cvs.find((cv: any) => cv.id === id))
    .filter(Boolean);

  const toggleCompare = (cvId: number) => {
    setSelectedCVId(null);
    setCompareIds((current) => {
      if (current.includes(cvId)) {
        return current.filter((id) => id !== cvId);
      }
      return [...current.slice(-1), cvId];
    });
  };

  const backToCVList = () => {
    setSelectedCVId(null);
    setCompareIds([]);
    window.setTimeout(() => {
      document.getElementById("cv-list-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };

  if (isLoading) {
    return <div className="p-8 text-center text-slate-600">Loading...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-lg">
          <h2 className="mb-4 text-2xl font-semibold text-slate-900">Sign in to upload CV</h2>
          <p className="mb-6 text-sm text-slate-600">Upload your CV to get AI-powered job recommendations.</p>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Link href={`/login?next=${encodeURIComponent("/cv-upload")}`} className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">
              Sign in
            </Link>
            <Link href={`/register?next=${encodeURIComponent("/cv-upload")}`} className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50">
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
        {/* Header */}
        <div className="mb-6 rounded-[2rem] border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-6 shadow-lg sm:p-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4 max-w-2xl">
              <div className="relative">
                <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 opacity-20 blur-sm"></div>
                <img src="/logo.svg" alt="Remote Job Hunter Logo" className="relative h-16 w-16 flex-shrink-0" />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-indigo-600">AI-Powered Job Matching</p>
                <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">Upload Your CV</h1>
                <p className="text-sm leading-7 text-slate-600">
                  Upload your resume to automatically extract skills, experience, and get personalized job recommendations based on your profile.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/scraper" className="rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Scraper
              </Link>
              <Link href="/" className="rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                Home
              </Link>
            </div>
          </div>
        </div>

        <CVDashboardStats stats={stats} />

        <div className="grid gap-6 lg:grid-cols-[400px_minmax(0,1fr)]">
          {/* Left Sidebar - Upload */}
          <aside className="space-y-5">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-950">Upload CV</h2>
              
              <div
                className={`relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 transition-colors ${
                  dragActive ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/30"
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={handleFileChange}
                  className="absolute inset-0 cursor-pointer opacity-0"
                />
                <Upload className="mb-3 h-10 w-10 text-slate-400" />
                <p className="text-sm font-medium text-slate-700">
                  {file ? file.name : "Drag & drop your CV here"}
                </p>
                <p className="mt-1 text-xs text-slate-500">PDF, DOCX, DOC, TXT</p>
              </div>

              {file && (
                <div className="mt-4 flex items-center justify-between rounded-xl bg-slate-50 p-3">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-slate-500" />
                    <span className="text-sm text-slate-700">{file.name}</span>
                  </div>
                  <button
                    onClick={() => setFile(null)}
                    className="rounded-lg p-1 text-slate-400 hover:text-slate-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={!file || uploadMutation.isPending}
                className="mt-4 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
              >
                {uploadMutation.isPending ? (
                  <span className="inline-flex items-center justify-center gap-2">
                    <Sparkles className="h-4 w-4 animate-spin" />
                    Processing...
                  </span>
                ) : "Upload & Parse CV"}
              </button>

              {uploadMutation.isSuccess && (
                <div className="mt-4 flex items-center gap-2 rounded-xl bg-green-50 p-3 text-sm text-green-700">
                  <CheckCircle className="h-4 w-4" />
                  <span>CV uploaded and parsed successfully!</span>
                </div>
              )}

              {uploadMutation.isError && (
                <div className="mt-4 flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4" />
                  <span>Failed to upload CV. Please try again.</span>
                </div>
              )}
            </div>

            {/* Info Card */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-slate-950">What we extract</h3>
              <ul className="space-y-2 text-xs text-slate-600">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  <span>Technical skills & tech stack</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  <span>Years of experience</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  <span>Education & certifications</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  <span>ATS score calculation</span>
                </li>
              </ul>
            </div>

            {/* Your CVs List */}
            {cvsQuery.data && cvsQuery.data.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="mb-4 text-sm font-semibold text-slate-950">Your CVs</h2>
                <div className="space-y-2">
                  {cvsQuery.data.map((cv: any) => (
                    <button
                      key={cv.id}
                      onClick={() => setSelectedCVId(selectedCVId === cv.id ? null : cv.id)}
                      className={`w-full rounded-lg border p-3 text-left text-xs transition-colors ${
                        selectedCVId === cv.id
                          ? "border-indigo-500 bg-indigo-50"
                          : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/30"
                      }`}
                    >
                      <p className="font-medium text-slate-900">{cv.file_name}</p>
                      <p className="mt-1 text-slate-500">
                        {cv.tech_stack?.length || 0} skills • {cv.job_roles?.length || 0} roles
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </aside>

          {/* Main Content - CV Analysis or List */}
          <section className="space-y-5">
            {comparisonCVs.length === 2 ? (
              <CVComparisonView cvs={comparisonCVs} onClose={backToCVList} />
            ) : selectedCVId ? (
              // Show CV Analysis
              <>
                {cvsQuery.data && (
                  <div className="space-y-3">
                    <button
                      onClick={backToCVList}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                    >
                      <ArrowLeft className="h-4 w-4" />
                      Back to CV list
                    </button>
                    <CVAnalysis
                      cvId={selectedCVId}
                      cvFileName={cvsQuery.data.find((c: any) => c.id === selectedCVId)?.file_name || "CV"}
                    />
                  </div>
                )}
              </>
            ) : (
              // Show CV List
              <div id="cv-list-panel" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-950">Your CVs</h2>
                  <span className="text-xs text-slate-500">{cvsQuery.data?.length || 0} uploaded</span>
                </div>

                {cvsQuery.isLoading ? (
                  <div className="py-8 text-center text-sm text-slate-500">Loading...</div>
                ) : cvsQuery.data && cvsQuery.data.length > 0 ? (
                  <div className="space-y-3">
                    {matchResult && (
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                        <div className="flex items-start gap-3">
                          <CheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
                          <div>
                            <p className="font-semibold text-emerald-950">Analysis is done for {matchResult.fileName}</p>
                            <p className="mt-1 text-xs">
                              Scraped {matchResult.scrapedJobs} jobs and found {matchResult.matchesCount} matches.
                            </p>
                            <Link href="/cv-jobs" className="mt-3 inline-flex rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-800">
                              View matches
                            </Link>
                          </div>
                        </div>
                      </div>
                    )}
                    {cvsQuery.data.map((cv: any) => (
                      <CVCard
                        key={cv.id}
                        cv={cv}
                        onDelete={() => deleteMutation.mutate(cv.id)}
                        onMatch={() => matchMutation.mutate(cv)}
                        onViewAnalysis={() => setSelectedCVId(cv.id)}
                        onCompare={() => toggleCompare(cv.id)}
                        isSelectedForCompare={compareIds.includes(cv.id)}
                        isMatching={matchMutation.isPending}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center">
                    <FileText className="mx-auto mb-3 h-12 w-12 text-slate-300" />
                    <p className="text-sm text-slate-500">No CVs uploaded yet</p>
                    <p className="mt-1 text-xs text-slate-400">Upload your first CV to get started</p>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function CVDashboardStats({ stats }: { stats: { totalCVs: number; totalSkills: number; highestATS: number; totalMatchedJobs: number } }) {
  const cards = [
    { label: "Total CVs", value: stats.totalCVs, icon: FileText, tone: "bg-slate-900 text-white" },
    { label: "Total skills", value: stats.totalSkills, icon: BarChart3, tone: "bg-indigo-600 text-white" },
    { label: "Highest ATS", value: `${stats.highestATS || 0}/100`, icon: Trophy, tone: "bg-emerald-600 text-white" },
    { label: "Matched jobs", value: stats.totalMatchedJobs, icon: BriefcaseBusiness, tone: "bg-cyan-700 text-white" },
  ];

  return (
    <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div key={card.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500">{card.label}</p>
                <p className="mt-2 text-2xl font-bold text-slate-950">{card.value}</p>
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${card.tone}`}>
                <Icon className="h-5 w-5" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CVComparisonView({ cvs, onClose }: { cvs: any[]; onClose: () => void }) {
  const [first, second] = cvs;
  const firstSkills = normalizeSkills(first);
  const secondSkills = normalizeSkills(second);
  const uniqueFirst = firstSkills.filter((skill) => !secondSkills.includes(skill));
  const uniqueSecond = secondSkills.filter((skill) => !firstSkills.includes(skill));
  const strongerATS = (first.ats_score || 0) >= (second.ats_score || 0) ? first : second;
  const roleSuggestion = getRoleSuggestion(first, second);

  return (
    <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">CV Comparison</h2>
          <p className="text-sm text-slate-500">Side-by-side skills, score, and role fit.</p>
        </div>
        <button onClick={onClose} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to CV list
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {[first, second].map((cv) => (
          <div key={cv.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950">{cv.file_name}</p>
                <p className="mt-1 text-xs text-slate-500">{cv.experience_years || 0} years exp / {cv.matched_jobs_count || 0} matches</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${getATSScoreStyle(cv.ats_score || 0)}`}>
                {cv.ats_score || 0}/100
              </span>
            </div>
            <div className="mt-4">
              <TechStackDisplay techs={normalizeSkills(cv).slice(0, 10)} maxVisible={10} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ComparisonDetail title={`Unique to ${first.file_name}`} items={uniqueFirst} />
        <ComparisonDetail title={`Unique to ${second.file_name}`} items={uniqueSecond} />
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-xs font-semibold uppercase text-emerald-700">Suggested use</p>
          <p className="mt-2 text-sm font-semibold text-emerald-950">{strongerATS.file_name} has the stronger ATS score.</p>
          <p className="mt-2 text-xs leading-5 text-emerald-800">{roleSuggestion}</p>
        </div>
      </div>
    </div>
  );
}

function ComparisonDetail({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{title}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length > 0 ? items.slice(0, 12).map((item) => (
          <span key={item} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{item}</span>
        )) : (
          <span className="text-xs text-slate-500">No unique skills found.</span>
        )}
      </div>
    </div>
  );
}

function CVCard({
  cv,
  onDelete,
  onMatch,
  onViewAnalysis,
  onCompare,
  isSelectedForCompare,
  isMatching
}: {
  cv: any;
  onDelete: () => void;
  onMatch: () => void;
  onViewAnalysis: () => void;
  onCompare: () => void;
  isSelectedForCompare: boolean;
  isMatching: boolean;
}) {
  const score = cv.ats_score ?? 0;
  const scoreStyle = getATSScoreStyle(score);
  const matchRate = cv.match_rate || 0;
  const topSkills = cv.tech_stack?.length ? cv.tech_stack : cv.skills || [];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50">
              <FileText className="h-5 w-5 text-slate-500" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-slate-950">{cv.file_name}</span>
              <span className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500">
                <CalendarDays className="h-3.5 w-3.5" />
                Uploaded {formatRelativeDate(cv.created_at)}
              </span>
            </div>
            <Link href={`/cv-ats/${cv.id}`} className={`rounded-full px-3 py-1 text-xs font-bold transition hover:brightness-95 ${scoreStyle}`}>
              ATS {score || "N/A"}{score ? "/100" : ""}
            </Link>
          </div>
          
          {/* Job Roles */}
          {cv.job_roles && cv.job_roles.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {cv.job_roles.slice(0, 3).map((role: string) => (
                <span key={role} className="rounded-md bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700">
                  {role}
                </span>
              ))}
              {cv.job_roles.length > 3 && (
                <span className="text-[10px] text-slate-500">+{cv.job_roles.length - 3} more</span>
              )}
            </div>
          )}
          
          {/* Tech Stack - Using TechStackDisplay */}
          <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-700">Top skills</span>
              <span className="text-xs text-slate-500">{topSkills.length} total</span>
            </div>
            {topSkills.length > 0 ? (
              <TechStackDisplay techs={topSkills.slice(0, 10)} maxVisible={10} />
            ) : null}
          </div>
          
          {/* Keywords */}
          {cv.keywords && cv.keywords.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {cv.keywords.slice(0, 4).map((keyword: string) => (
                <span key={keyword} className="rounded-md bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                  {keyword}
                </span>
              ))}
              {cv.keywords.length > 4 && (
                <span className="text-[10px] text-slate-500">+{cv.keywords.length - 4} more</span>
              )}
            </div>
          )}
          
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            {cv.experience_years && <span>{cv.experience_years} years experience</span>}
            <span>{cv.matched_jobs_count || 0} matched jobs</span>
            <span>{matchRate}% match rate</span>
          </div>
        </div>
        <div className="flex shrink-0 flex-col gap-2">
          <button
            onClick={onViewAnalysis}
            className="rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
          >
            View Analysis
          </button>
          <button
            onClick={onCompare}
            className={`inline-flex items-center justify-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-medium ${
              isSelectedForCompare
                ? "border-teal-300 bg-teal-50 text-teal-700"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            <GitCompare className="h-3 w-3" />
            Compare
          </button>
          <Link
            href={`/cv-ats/${cv.id}`}
            className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-center text-xs font-medium text-emerald-700 hover:bg-emerald-100"
          >
            ATS Analysis
          </Link>
          <button
            onClick={onMatch}
            disabled={isMatching}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isMatching ? (
              <span className="inline-flex items-center gap-1">
                <Sparkles className="h-3 w-3 animate-spin" />
                Scraping...
              </span>
            ) : (
              "Match Jobs"
            )}
          </button>
          <button
            onClick={onDelete}
            className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

function buildCVStats(cvs: any[]) {
  const uniqueSkills = new Set<string>();
  cvs.forEach((cv) => {
    normalizeSkills(cv).forEach((skill) => uniqueSkills.add(skill));
  });

  return {
    totalCVs: cvs.length,
    totalSkills: uniqueSkills.size,
    highestATS: cvs.reduce((highest, cv) => Math.max(highest, cv.ats_score || 0), 0),
    totalMatchedJobs: cvs.reduce((total, cv) => total + (cv.matched_jobs_count || 0), 0),
  };
}

function normalizeSkills(cv: any) {
  return Array.from(new Set([...(cv.tech_stack || []), ...(cv.skills || [])]))
    .map((skill) => String(skill).trim())
    .filter(Boolean);
}

function getATSScoreStyle(score: number) {
  if (score >= 80) return "bg-emerald-100 text-emerald-800";
  if (score >= 60) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}

function formatRelativeDate(value?: string) {
  if (!value) return "recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";

  const diffMs = Date.now() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays <= 0) return "today";
  if (diffDays === 1) return "1 day ago";
  if (diffDays < 30) return `${diffDays} days ago`;

  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths === 1) return "1 month ago";
  if (diffMonths < 12) return `${diffMonths} months ago`;

  const diffYears = Math.floor(diffMonths / 12);
  return diffYears === 1 ? "1 year ago" : `${diffYears} years ago`;
}

function getRoleSuggestion(first: any, second: any) {
  const firstRoles = first.job_roles || [];
  const secondRoles = second.job_roles || [];
  const firstMatchText = firstRoles.length ? firstRoles.slice(0, 2).join(", ") : "broad technical roles";
  const secondMatchText = secondRoles.length ? secondRoles.slice(0, 2).join(", ") : "general software roles";

  if ((first.ats_score || 0) === (second.ats_score || 0)) {
    return `${first.file_name} fits ${firstMatchText}; ${second.file_name} fits ${secondMatchText}. Pick based on the job title keywords.`;
  }

  const stronger = (first.ats_score || 0) > (second.ats_score || 0) ? first : second;
  const roles = (stronger.job_roles || []).slice(0, 2).join(", ") || "roles closest to its extracted skills";
  return `Use ${stronger.file_name} first for ${roles}. Use the other CV when its unique skills appear in the job description.`;
}
