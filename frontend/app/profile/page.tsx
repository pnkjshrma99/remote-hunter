"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Building2, GraduationCap, Save, User, Briefcase, Settings, Link as LinkIcon, Loader2, Key, Copy, Check, ExternalLink } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { getProfile, updateProfile, addExperience, updateExperience, deleteExperience, addEducation, updateEducation, deleteEducation, createApiToken, listApiTokens, revokeApiToken } from "@/lib/api";
import type { UserProfile, WorkExperience, Education, ApiToken } from "@/lib/api";

function emptyExperience(): WorkExperience {
  return { company: "", title: "", start_date: "", location: "", currently_working: false };
}

function emptyEducation(): Education {
  return { school: "", degree: "", field_of_study: "", start_date: "", location: "" };
}

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["profile", user?.id],
    queryFn: getProfile,
    enabled: !!user,
  });

  const [form, setForm] = useState<Record<string, any>>({
    first_name: "", last_name: "", middle_name: "",
    phone: "", address: "", city: "", state: "", postal_code: "", country: "",
    linkedin_url: "", github_url: "", portfolio_url: "", website: "",
    headline: "", summary: "",
    authorized_to_work_in_us: false,
    visa_sponsorship_needed: false,
    currently_employed: false,
    notice_period_days: "",
    desired_roles: "",
    desired_salary_min: "", desired_salary_max: "",
    preferred_locations: "",
    remote_only: true,
    open_to_relocation: false,
    open_to_contract: true,
    open_to_fulltime: true,
    how_did_you_hear: "",
    cover_letter_intro: "",
    gender: "", hispanic_latino: "", veteran_status: "", disability_status: "",
    custom_answers: "",
  });
  const [experiences, setExperiences] = useState<WorkExperience[]>([]);
  const [education, setEducation] = useState<Education[]>([]);
  const [editingExp, setEditingExp] = useState<number | null>(null);
  const [editingEdu, setEditingEdu] = useState<number | null>(null);
  const [newExp, setNewExp] = useState<WorkExperience>(emptyExperience());
  const [newEdu, setNewEdu] = useState<Education>(emptyEducation());
  const [showNewExp, setShowNewExp] = useState(false);
  const [showNewEdu, setShowNewEdu] = useState(false);
  const [apiTokens, setApiTokens] = useState<ApiToken[]>([]);
  const [newTokenName, setNewTokenName] = useState("");
  const [newTokenValue, setNewTokenValue] = useState("");
  const [showNewToken, setShowNewToken] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  useEffect(() => {
    listApiTokens().then(setApiTokens).catch(() => {});
  }, []);

  useEffect(() => {
    if (profile) {
      const names = (profile.full_name || "").split(" ");
      setForm({
        first_name: names[0] || "",
        last_name: names.slice(2).join(" ") || names[1] || "",
        middle_name: names.length > 2 ? names.slice(1, -1).join(" ") : "",
        phone: profile.phone || "",
        address: profile.address || "",
        city: profile.city || "",
        state: profile.state || "",
        postal_code: profile.postal_code || "",
        country: profile.country || "",
        linkedin_url: profile.linkedin_url || "",
        github_url: profile.github_url || "",
        portfolio_url: profile.portfolio_url || "",
        website: profile.website || "",
        headline: profile.headline || "",
        summary: profile.summary || "",
        authorized_to_work_in_us: profile.authorized_to_work_in_us,
        visa_sponsorship_needed: profile.visa_sponsorship_needed,
        currently_employed: profile.currently_employed,
        notice_period_days: profile.notice_period_days || "",
        desired_roles: profile.desired_roles?.join(", ") || "",
        desired_salary_min: profile.desired_salary_min || "",
        desired_salary_max: profile.desired_salary_max || "",
        preferred_locations: profile.preferred_locations?.join(", ") || "",
        remote_only: profile.remote_only,
        open_to_relocation: profile.open_to_relocation,
        open_to_contract: profile.open_to_contract,
        open_to_fulltime: profile.open_to_fulltime,
        how_did_you_hear: profile.how_did_you_hear || "",
        cover_letter_intro: profile.cover_letter_intro || "",
        gender: profile.gender || "",
        hispanic_latino: profile.hispanic_latino || "",
        veteran_status: profile.veteran_status || "",
        disability_status: profile.disability_status || "",
        custom_answers: profile.custom_answers ? Object.entries(profile.custom_answers).map(([k, v]) => `${k}: ${v}`).join("\n") : "",
      });
      setExperiences(profile.experiences || []);
      setEducation(profile.education || []);
    }
  }, [profile]);

  const saveMutation = useMutation({
    mutationFn: (data: any) => {
      const cleaned = { ...data };
      // Clean empty strings for integer fields
      for (const intField of ["notice_period_days", "desired_salary_min", "desired_salary_max"]) {
        if (cleaned[intField] === "" || cleaned[intField] === null) {
          cleaned[intField] = null;
        }
      }
      // Convert comma-separated strings to arrays
      for (const listField of ["desired_roles", "preferred_locations"]) {
        if (typeof cleaned[listField] === "string") {
          cleaned[listField] = cleaned[listField].split(",").map((s: string) => s.trim()).filter(Boolean);
        }
      }
      // Convert custom_answers textarea to JSON
      if (typeof cleaned.custom_answers === "string") {
        const lines = cleaned.custom_answers.split("\n").filter(Boolean);
        const obj: Record<string, string> = {};
        for (const line of lines) {
          const colonIdx = line.indexOf(":");
          if (colonIdx > 0) {
            obj[line.slice(0, colonIdx).trim()] = line.slice(colonIdx + 1).trim();
          } else {
            obj[line] = "";
          }
        }
        cleaned.custom_answers = Object.keys(obj).length ? obj : null;
      }
      return updateProfile(cleaned);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile", user?.id] });
    },
  });

  const addExpMutation = useMutation({
    mutationFn: (data: WorkExperience) => addExperience(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile", user?.id] });
      setShowNewExp(false);
      setNewExp(emptyExperience());
    },
  });

  const delExpMutation = useMutation({
    mutationFn: (id: number) => deleteExperience(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile", user?.id] }),
  });

  const addEduMutation = useMutation({
    mutationFn: (data: Education) => addEducation(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile", user?.id] });
      setShowNewEdu(false);
      setNewEdu(emptyEducation());
    },
  });

  const delEduMutation = useMutation({
    mutationFn: (id: number) => deleteEducation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile", user?.id] }),
  });

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  if (profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  const set = (key: string, value: any) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-4xl px-4 py-10">
        {/* Header */}
        <div className="mb-8 flex items-center gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 p-3 shadow-lg">
            <User className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Your Profile</h1>
            <p className="text-sm text-slate-500">Set up your details for one-click job applications</p>
          </div>
          <button
            onClick={() => saveMutation.mutate(form)}
            disabled={saveMutation.isPending}
            className="ml-auto flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save
          </button>
        </div>

        {saveMutation.isSuccess && (
          <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            Profile saved successfully
          </div>
        )}

        {saveMutation.isError && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {saveMutation.error?.message || "Failed to save profile"}
          </div>
        )}

        <div className="space-y-6">
          {/* Personal Info */}
          <Section icon={<User className="h-5 w-5" />} title="Personal Information">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="First Name" value={form.first_name ?? ""} onChange={(v) => set("first_name", v)} />
              <Field label="Last Name" value={form.last_name ?? ""} onChange={(v) => set("last_name", v)} />
              <Field label="Middle Name" value={form.middle_name ?? ""} onChange={(v) => set("middle_name", v)} />
              <Field label="Phone" value={form.phone ?? ""} onChange={(v) => set("phone", v)} />
              <Field label="Address" value={form.address ?? ""} onChange={(v) => set("address", v)} />
              <Field label="City" value={form.city ?? ""} onChange={(v) => set("city", v)} />
              <Field label="State" value={form.state ?? ""} onChange={(v) => set("state", v)} />
              <Field label="Postal Code" value={form.postal_code ?? ""} onChange={(v) => set("postal_code", v)} />
              <Field label="Country" value={form.country ?? ""} onChange={(v) => set("country", v)} />
              <Field label="LinkedIn URL" value={form.linkedin_url ?? ""} onChange={(v) => set("linkedin_url", v)} icon={<LinkIcon className="h-3.5 w-3.5 text-indigo-500" />} />
              <Field label="GitHub URL" value={form.github_url ?? ""} onChange={(v) => set("github_url", v)} />
              <Field label="Portfolio URL" value={form.portfolio_url ?? ""} onChange={(v) => set("portfolio_url", v)} />
              <Field label="Website" value={form.website ?? ""} onChange={(v) => set("website", v)} />
            </div>
          </Section>

          {/* Professional */}
          <Section icon={<Briefcase className="h-5 w-5" />} title="Professional">
            <div className="space-y-4">
              <Field label="Headline" value={form.headline ?? ""} onChange={(v) => set("headline", v)} placeholder="e.g. Senior Frontend Engineer" />
              <div>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Summary</label>
                <textarea
                  value={form.summary ?? ""}
                  onChange={(e) => set("summary", e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  placeholder="Brief professional summary..."
                />
              </div>
            </div>
          </Section>

          {/* Work Authorization & Preferences */}
          <Section icon={<Settings className="h-5 w-5" />} title="Work Authorization & Preferences">
            <div className="grid gap-4 sm:grid-cols-2">
              <Toggle label="Authorized to work in the US" checked={form.authorized_to_work_in_us} onChange={(v) => set("authorized_to_work_in_us", v)} />
              <Toggle label="Need visa sponsorship" checked={form.visa_sponsorship_needed} onChange={(v) => set("visa_sponsorship_needed", v)} />
              <Toggle label="Currently employed" checked={form.currently_employed} onChange={(v) => set("currently_employed", v)} />
              <Field label="Notice period (days)" value={form.notice_period_days ?? ""} onChange={(v) => set("notice_period_days", v)} type="number" />
              <Toggle label="Remote only" checked={form.remote_only} onChange={(v) => set("remote_only", v)} />
              <Toggle label="Open to relocation" checked={form.open_to_relocation} onChange={(v) => set("open_to_relocation", v)} />
              <Toggle label="Open to contract" checked={form.open_to_contract} onChange={(v) => set("open_to_contract", v)} />
              <Toggle label="Open to full-time" checked={form.open_to_fulltime} onChange={(v) => set("open_to_fulltime", v)} />
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field label="Desired roles (comma separated)" value={form.desired_roles ?? ""} onChange={(v) => set("desired_roles", v)} placeholder="e.g. Frontend, Full Stack" />
              <Field label="Preferred locations (comma separated)" value={form.preferred_locations ?? ""} onChange={(v) => set("preferred_locations", v)} placeholder="e.g. US, EU, Worldwide" />
              <Field label="Min salary" value={form.desired_salary_min ?? ""} onChange={(v) => set("desired_salary_min", v)} type="number" />
              <Field label="Max salary" value={form.desired_salary_max ?? ""} onChange={(v) => set("desired_salary_max", v)} type="number" />
              <Field label="How did you hear about us?" value={form.how_did_you_hear ?? ""} onChange={(v) => set("how_did_you_hear", v)} />
            </div>
            <div className="mt-4">
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Cover Letter Intro</label>
              <textarea
                value={form.cover_letter_intro ?? ""}
                onChange={(e) => set("cover_letter_intro", e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                placeholder="Write a brief cover letter intro that will be used as the default for applications..."
              />
            </div>
            <div className="mt-4">
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Custom Q&A Answers</label>
              <p className="mb-2 text-xs text-slate-400">One per line: <code>Question: Answer</code></p>
              <textarea
                value={form.custom_answers ?? ""}
                onChange={(e) => set("custom_answers", e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                placeholder="Why do you want to work here?: I'm passionate about...&#10;Hardest technical problem?: I once debugged..."
              />
            </div>
          </Section>

          {/* Equal Employment Opportunity */}
          <Section icon={<Settings className="h-5 w-5" />} title="Equal Employment Opportunity (EEO)">
            <p className="mb-3 text-xs text-slate-400">These are optional but commonly required on US job applications.</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Gender" value={form.gender ?? ""} onChange={(v) => set("gender", v)} placeholder="Male / Female / Non-binary / Prefer not to say" />
              <Field label="Hispanic/Latino" value={form.hispanic_latino ?? ""} onChange={(v) => set("hispanic_latino", v)} placeholder="Yes / No" />
              <Field label="Veteran Status" value={form.veteran_status ?? ""} onChange={(v) => set("veteran_status", v)} placeholder="I am not a protected veteran / I identify as one or more..." />
              <Field label="Disability Status" value={form.disability_status ?? ""} onChange={(v) => set("disability_status", v)} placeholder="Yes / No / Prefer not to say" />
            </div>
          </Section>

          {/* Work Experience */}
          <Section icon={<Building2 className="h-5 w-5" />} title="Work Experience">
            <div className="space-y-3">
              {experiences.map((exp, i) => (
                <div key={exp.id || i} className="flex items-start justify-between rounded-xl border border-slate-200 bg-white p-4">
                  <div>
                    <p className="font-medium text-slate-800">{exp.title}</p>
                    <p className="text-sm text-slate-500">{exp.company} &middot; {exp.location} &middot; {exp.start_date} &ndash; {exp.currently_working ? "Present" : exp.end_date}</p>
                    {exp.description && <p className="mt-1 text-sm text-slate-600">{exp.description}</p>}
                  </div>
                  <button onClick={() => delExpMutation.mutate(exp.id!)} className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            {showNewExp ? (
              <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Company" value={newExp.company} onChange={(v) => setNewExp((p) => ({ ...p, company: v }))} />
                  <Field label="Title" value={newExp.title} onChange={(v) => setNewExp((p) => ({ ...p, title: v }))} />
                  <Field label="Location" value={newExp.location || ""} onChange={(v) => setNewExp((p) => ({ ...p, location: v }))} />
                  <Field label="Start date" value={newExp.start_date} onChange={(v) => setNewExp((p) => ({ ...p, start_date: v }))} placeholder="e.g. 2021-03" />
                  {!newExp.currently_working && (
                    <Field label="End date" value={newExp.end_date || ""} onChange={(v) => setNewExp((p) => ({ ...p, end_date: v }))} placeholder="e.g. 2023-06" />
                  )}
                  <div className="flex items-center gap-2 sm:col-span-2">
                    <input type="checkbox" id="exp-current" checked={newExp.currently_working || false} onChange={(e) => setNewExp((p) => ({ ...p, currently_working: e.target.checked, end_date: e.target.checked ? undefined : p.end_date }))} className="rounded border-slate-300" />
                    <label htmlFor="exp-current" className="text-sm text-slate-600">I currently work here</label>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="mb-1 block text-xs font-semibold text-slate-500">Description</label>
                    <textarea value={newExp.description || ""} onChange={(e) => setNewExp((p) => ({ ...p, description: e.target.value }))} rows={2} className="w-full rounded-xl border border-slate-200 px-4 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <button onClick={() => addExpMutation.mutate(newExp)} disabled={addExpMutation.isPending || !newExp.company || !newExp.title} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
                    {addExpMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
                  </button>
                  <button onClick={() => setShowNewExp(false)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancel</button>
                </div>
              </div>
            ) : (
              <button onClick={() => setShowNewExp(true)} className="mt-3 flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700">
                <Plus className="h-4 w-4" /> Add experience
              </button>
            )}
          </Section>

          {/* Education */}
          <Section icon={<GraduationCap className="h-5 w-5" />} title="Education">
            <div className="space-y-3">
              {education.map((edu, i) => (
                <div key={edu.id || i} className="flex items-start justify-between rounded-xl border border-slate-200 bg-white p-4">
                  <div>
                    <p className="font-medium text-slate-800">{edu.degree} in {edu.field_of_study}</p>
                    <p className="text-sm text-slate-500">{edu.school} &middot; {edu.start_date} &ndash; {edu.currently_studying ? "Present" : edu.end_date}</p>
                    {edu.gpa && <p className="text-sm text-slate-500">GPA: {edu.gpa}</p>}
                  </div>
                  <button onClick={() => delEduMutation.mutate(edu.id!)} className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            {showNewEdu ? (
              <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="School" value={newEdu.school} onChange={(v) => setNewEdu((p) => ({ ...p, school: v }))} />
                  <Field label="Degree" value={newEdu.degree} onChange={(v) => setNewEdu((p) => ({ ...p, degree: v }))} />
                  <Field label="Field of study" value={newEdu.field_of_study || ""} onChange={(v) => setNewEdu((p) => ({ ...p, field_of_study: v }))} />
                  <Field label="Location" value={newEdu.location || ""} onChange={(v) => setNewEdu((p) => ({ ...p, location: v }))} />
                  <Field label="Start date" value={newEdu.start_date} onChange={(v) => setNewEdu((p) => ({ ...p, start_date: v }))} placeholder="e.g. 2017-09" />
                  {!newEdu.currently_studying && (
                    <Field label="End date" value={newEdu.end_date || ""} onChange={(v) => setNewEdu((p) => ({ ...p, end_date: v }))} placeholder="e.g. 2021-06" />
                  )}
                  <Field label="GPA" value={newEdu.gpa || ""} onChange={(v) => setNewEdu((p) => ({ ...p, gpa: v }))} />
                  <div className="flex items-center gap-2">
                    <input type="checkbox" id="edu-current" checked={newEdu.currently_studying || false} onChange={(e) => setNewEdu((p) => ({ ...p, currently_studying: e.target.checked, end_date: e.target.checked ? undefined : p.end_date }))} className="rounded border-slate-300" />
                    <label htmlFor="edu-current" className="text-sm text-slate-600">Currently studying</label>
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <button onClick={() => addEduMutation.mutate(newEdu)} disabled={addEduMutation.isPending || !newEdu.school || !newEdu.degree} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
                    {addEduMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
                  </button>
                  <button onClick={() => setShowNewEdu(false)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancel</button>
                </div>
              </div>
            ) : (
              <button onClick={() => setShowNewEdu(true)} className="mt-3 flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700">
                <Plus className="h-4 w-4" /> Add education
              </button>
            )}
          </Section>

          {/* API Tokens */}
          <Section icon={<Key className="h-5 w-5" />} title="Extension API Tokens">
            <p className="mb-4 text-sm text-slate-500">
              Use these tokens to authenticate the Remote Hunter browser extension.
            </p>

            {apiTokens.map((t) => (
              <div key={t.id} className="mb-2 flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{t.name}</p>
                  <p className="text-xs text-slate-400">
                    {t.token ? t.token.slice(0, 20) + "..." : ""}
                    {t.last_used_at ? ` · Last used: ${new Date(t.last_used_at).toLocaleDateString()}` : " · Never used"}
                  </p>
                </div>
                <button
                  onClick={async () => {
                    await revokeApiToken(t.id);
                    setApiTokens((prev) => prev.filter((x) => x.id !== t.id));
                  }}
                  className="rounded-lg px-3 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50"
                >
                  Revoke
                </button>
              </div>
            ))}

            {showNewToken ? (
              <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4">
                {newTokenValue ? (
                  <div>
                    <p className="mb-2 text-xs font-semibold text-emerald-600">Token created! Copy it now — you won&apos;t see it again.</p>
                    <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700">
                      <span className="flex-1 break-all">{newTokenValue}</span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(newTokenValue);
                          setCopiedToken(true);
                          setTimeout(() => setCopiedToken(false), 2000);
                        }}
                        className="shrink-0 rounded-md p-1.5 text-indigo-600 hover:bg-indigo-50"
                      >
                        {copiedToken ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      </button>
                    </div>
                    <button
                      onClick={() => {
                        setShowNewToken(false);
                        setNewTokenValue("");
                        setNewTokenName("");
                      }}
                      className="mt-3 text-sm text-slate-500 hover:text-slate-700"
                    >
                      Done
                    </button>
                  </div>
                ) : (
                  <div>
                    <input
                      value={newTokenName}
                      onChange={(e) => setNewTokenName(e.target.value)}
                      placeholder="Token name (e.g. Chrome Extension)"
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    />
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={async () => {
                          if (!newTokenName.trim()) return;
                          const token = await createApiToken(newTokenName.trim());
                          setNewTokenValue(token.token);
                          setApiTokens((prev) => [token, ...prev]);
                        }}
                        disabled={!newTokenName.trim()}
                        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        Generate Token
                      </button>
                      <button onClick={() => setShowNewToken(false)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => setShowNewToken(true)}
                className="mt-3 flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
              >
                <Plus className="h-4 w-4" /> Generate new token
              </button>
            )}

            <div className="mt-4 rounded-xl bg-indigo-50 px-4 py-3">
              <p className="text-xs text-indigo-700">
                <strong>How to use:</strong> Install the extension, click the icon, paste this token and connect. The extension will auto-fill your profile data on job application pages.
                <a href="/help" className="ml-1 inline-flex items-center gap-0.5 font-medium underline">
                  Learn more <ExternalLink className="h-3 w-3" />
                </a>
              </p>
            </div>
          </Section>
        </div>
      </div>
    </main>
  );
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2 border-b border-slate-100 pb-3">
        <span className="text-indigo-600">{icon}</span>
        <h2 className="text-base font-semibold text-slate-800">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder, icon }: {
  label: string;
  value: any;
  onChange: (v: any) => void;
  type?: string;
  placeholder?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">{icon} {label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(type === "number" ? (e.target.value ? Number(e.target.value) : "") : e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      />
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 transition hover:bg-slate-50">
      <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
      <span className="text-sm text-slate-700">{label}</span>
    </label>
  );
}
