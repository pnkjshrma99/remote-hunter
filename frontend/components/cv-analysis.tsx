"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, TrendingUp, Code, Award, Calendar, ExternalLink, Pencil, Plus, X, GripVertical, Save } from "lucide-react";
import { getCV, getMatchedJobs, updateCV } from "@/lib/api";
import { TechStackDisplay } from "./tech-stack-display";

interface CVAnalysisProps {
  cvId: number;
  cvFileName: string;
}

type EditableCVDraft = {
  tech_stack: string[];
  job_roles: string[];
  keywords: string[];
  experience_years: number | null;
};

export function CVAnalysis({ cvId, cvFileName }: CVAnalysisProps) {
  const [showAllJobs, setShowAllJobs] = useState(false);
  const [draftSkill, setDraftSkill] = useState("");
  const [draftRole, setDraftRole] = useState("");
  const [draftKeyword, setDraftKeyword] = useState("");
  const [draft, setDraft] = useState<EditableCVDraft | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();

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
  const allSkills = cv ? Array.from(new Set([...(cv.tech_stack || []), ...(cv.skills || [])])) as string[] : [];

  const updateMutation = useMutation({
    mutationFn: (data: any) => updateCV(cvId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cv", cvId] });
      queryClient.invalidateQueries({ queryKey: ["my-cvs"] });
      setIsEditing(false);
      setDraft(null);
      setDraftSkill("");
      setDraftRole("");
      setDraftKeyword("");
    }
  });

  const startEditing = () => {
    if (!cv) return;
    setDraft({
      tech_stack: [...(cv.tech_stack || [])],
      job_roles: [...(cv.job_roles || [])],
      keywords: [...(cv.keywords || [])],
      experience_years: cv.experience_years ?? null,
    });
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setDraft(null);
    setDraftSkill("");
    setDraftRole("");
    setDraftKeyword("");
  };

  const saveChanges = () => {
    if (!draft) return;
    updateMutation.mutate(draft);
  };

  const addItem = (field: "tech_stack" | "job_roles" | "keywords", value: string, reset: () => void) => {
    const item = value.trim();
    if (!item || !draft) return;
    setDraft({
      ...draft,
      [field]: Array.from(new Set([...(draft[field] || []), item]))
    });
    reset();
  };

  const removeItem = (field: "tech_stack" | "job_roles" | "keywords", value: string) => {
    if (!draft) return;
    setDraft({
      ...draft,
      [field]: (draft[field] || []).filter((item: string) => item !== value)
    });
  };

  const moveItem = (field: "tech_stack" | "job_roles" | "keywords", index: number, direction: -1 | 1) => {
    if (!draft) return;
    const next = [...(draft[field] || [])];
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= next.length) return;
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    setDraft({ ...draft, [field]: next });
  };

  const updateExperience = (value: string) => {
    if (!draft) return;
    setDraft({
      ...draft,
      experience_years: value === "" ? null : Number(value)
    });
  };

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
              {allSkills.length}
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

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">Extracted data</p>
          <p className="text-xs text-slate-500">Click Edit to fix skills, roles, and experience before matching jobs.</p>
        </div>
        {isEditing ? (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={cancelEditing}
              disabled={updateMutation.isPending}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={saveChanges}
              disabled={updateMutation.isPending || !draft}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              <Save size={14} />
              {updateMutation.isPending ? "Saving..." : "Save changes"}
            </button>
          </div>
        ) : (
          <button
            onClick={startEditing}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Pencil size={14} />
            Edit
          </button>
        )}
      </div>

      {isEditing && draft && (
        <div className="grid gap-3 rounded-lg border border-indigo-100 bg-indigo-50/40 p-4 sm:grid-cols-[1fr_220px]">
          <label className="space-y-1">
            <span className="text-xs font-semibold text-slate-700">Experience years</span>
            <input
              type="number"
              min={0}
              max={80}
              value={draft.experience_years ?? ""}
              onChange={(event) => updateExperience(event.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
            />
          </label>
          <div className="flex items-end">
            <div className="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-slate-600">
              <Save size={14} />
              {updateMutation.isError ? "Save failed" : "Edits are saved together"}
            </div>
          </div>
        </div>
      )}

      {/* Tech Stack Section */}
      {(cv.tech_stack && cv.tech_stack.length > 0) || isEditing ? (
        <div className="space-y-3 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-2">
            <Code size={18} className="text-slate-900" />
            <h4 className="font-semibold text-slate-900">Tech Stack ({isEditing && draft ? draft.tech_stack.length : cv.tech_stack?.length || 0})</h4>
          </div>
          {isEditing && draft ? (
            <EditableList
              items={draft.tech_stack}
              onRemove={(item) => removeItem("tech_stack", item)}
              onMove={(index, direction) => moveItem("tech_stack", index, direction)}
              inputValue={draftSkill}
              onInputChange={setDraftSkill}
              onAdd={() => addItem("tech_stack", draftSkill, () => setDraftSkill(""))}
              placeholder="Add skill"
            />
          ) : (
            <TechStackDisplay techs={cv.tech_stack} maxVisible={8} />
          )}
        </div>
      ) : null}

      {/* Job Roles Section */}
      {(cv.job_roles && cv.job_roles.length > 0) || isEditing ? (
        <div className="space-y-3 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-2">
            <Award size={18} className="text-slate-900" />
            <h4 className="font-semibold text-slate-900">Job Roles ({isEditing && draft ? draft.job_roles.length : cv.job_roles?.length || 0})</h4>
          </div>
          {isEditing && draft ? (
            <EditableList
              items={draft.job_roles}
              onRemove={(item) => removeItem("job_roles", item)}
              onMove={(index, direction) => moveItem("job_roles", index, direction)}
              inputValue={draftRole}
              onInputChange={setDraftRole}
              onAdd={() => addItem("job_roles", draftRole, () => setDraftRole(""))}
              placeholder="Add role"
              tone="slate"
            />
          ) : (
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
          )}
        </div>
      ) : null}

      {/* Keywords Section */}
      {(cv.keywords && cv.keywords.length > 0) || isEditing ? (
        <div className="space-y-3 border-t border-slate-200 pt-4">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-slate-900" />
            <h4 className="font-semibold text-slate-900">Keywords ({isEditing && draft ? draft.keywords.length : cv.keywords?.length || 0})</h4>
          </div>
          {isEditing && draft ? (
            <EditableList
              items={draft.keywords}
              onRemove={(item) => removeItem("keywords", item)}
              onMove={(index, direction) => moveItem("keywords", index, direction)}
              inputValue={draftKeyword}
              onInputChange={setDraftKeyword}
              onAdd={() => addItem("keywords", draftKeyword, () => setDraftKeyword(""))}
              placeholder="Add keyword"
              tone="slate"
            />
          ) : (
            <div className="flex flex-wrap gap-2">
              {cv.keywords.map((keyword: string) => (
                <span
                  key={keyword}
                  className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                >
                  {keyword}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : null}

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

function EditableList({
  items,
  onRemove,
  onMove,
  inputValue,
  onInputChange,
  onAdd,
  placeholder,
  tone = "indigo"
}: {
  items: string[];
  onRemove: (item: string) => void;
  onMove: (index: number, direction: -1 | 1) => void;
  inputValue: string;
  onInputChange: (value: string) => void;
  onAdd: () => void;
  placeholder: string;
  tone?: "indigo" | "slate";
}) {
  const chipClass = tone === "indigo"
    ? "bg-indigo-100 text-indigo-800"
    : "bg-slate-100 text-slate-800";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <span key={`${item}-${index}`} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${chipClass}`}>
            <GripVertical size={12} className="text-slate-400" />
            {item}
            <button onClick={() => onMove(index, -1)} disabled={index === 0} className="text-slate-500 disabled:opacity-30" aria-label={`Move ${item} earlier`}>Up</button>
            <button onClick={() => onMove(index, 1)} disabled={index === items.length - 1} className="text-slate-500 disabled:opacity-30" aria-label={`Move ${item} later`}>Down</button>
            <button onClick={() => onRemove(item)} className="rounded-full text-slate-500 hover:text-red-600" aria-label={`Remove ${item}`}>
              <X size={12} />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={inputValue}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAdd();
            }
          }}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
        />
        <button onClick={onAdd} className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800">
          <Plus size={14} />
          Add
        </button>
      </div>
    </div>
  );
}
