"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { uploadCV, getMyCVs, deleteCV, matchJobsForCV } from "@/lib/api";
import { CVAnalysis } from "@/components/cv-analysis";
import { TechStackDisplay } from "@/components/tech-stack-display";

export default function CVUploadPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [selectedCVId, setSelectedCVId] = useState<number | null>(null);

  const cvsQuery = useQuery({
    queryKey: ["my-cvs"],
    queryFn: getMyCVs,
    enabled: isAuthenticated
  });

  const uploadMutation = useMutation({
    mutationFn: uploadCV,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
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
    mutationFn: matchJobsForCV,
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
      alert(`Successfully scraped ${data.scraped_jobs} jobs and matched ${data.matches_count} jobs! Redirecting to your job recommendations...`);
      window.location.href = '/cv-jobs';
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

  if (isLoading) {
    return <div className="p-8 text-center text-slate-600">Loading...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-lg">
          <h2 className="mb-4 text-2xl font-semibold text-slate-900">Sign in to upload CV</h2>
          <p className="mb-6 text-sm text-slate-600">Upload your CV to get AI-powered job recommendations.</p>
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
            {selectedCVId ? (
              // Show CV Analysis
              <>
                {cvsQuery.data && (
                  <CVAnalysis
                    cvId={selectedCVId}
                    cvFileName={cvsQuery.data.find((c: any) => c.id === selectedCVId)?.file_name || "CV"}
                  />
                )}
              </>
            ) : (
              // Show CV List
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-950">Your CVs</h2>
                  <span className="text-xs text-slate-500">{cvsQuery.data?.length || 0} uploaded</span>
                </div>

                {cvsQuery.isLoading ? (
                  <div className="py-8 text-center text-sm text-slate-500">Loading...</div>
                ) : cvsQuery.data && cvsQuery.data.length > 0 ? (
                  <div className="space-y-3">
                    {cvsQuery.data.map((cv: any) => (
                      <CVCard
                        key={cv.id}
                        cv={cv}
                        onDelete={() => deleteMutation.mutate(cv.id)}
                        onMatch={() => matchMutation.mutate(cv.id)}
                        onViewAnalysis={() => setSelectedCVId(cv.id)}
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

function CVCard({ cv, onDelete, onMatch, onViewAnalysis, isMatching }: { cv: any; onDelete: () => void; onMatch: () => void; onViewAnalysis: () => void; isMatching: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-500" />
            <span className="text-sm font-medium text-slate-900">{cv.file_name}</span>
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
          <div className="mt-2">
            {cv.tech_stack && cv.tech_stack.length > 0 ? (
              <TechStackDisplay techs={cv.tech_stack} maxVisible={5} />
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
          
          <div className="mt-2 text-xs text-slate-500">
            {cv.experience_years && <span>{cv.experience_years} years experience</span>}
            {cv.ats_score && <span className="ml-3">ATS Score: {cv.ats_score}/100</span>}
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <button
            onClick={onViewAnalysis}
            className="rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
          >
            View Analysis
          </button>
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
