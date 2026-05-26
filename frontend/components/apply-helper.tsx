"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createCoverLetter, deleteCoverLetter, getCoverLetters } from "@/lib/api";
import type { CoverLetterTemplate } from "@/types/job";
import { X, Copy, Edit2, Check } from "lucide-react";

const DEFAULT_TEMPLATE_CONTENT = `Hi {{company}} team,

I am excited about the {{title}} role. I have hands-on exposure to Linux, Docker, Kubernetes, Terraform, CI/CD, and cloud operations, and I am looking for a junior remote DevOps/SRE role where I can grow while contributing reliably from India.

Best,`;

function defaultTemplateName() {
  return `Template ${new Date().toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`;
}

type ApplyHelperProps = {
  userId: number;
  userEmail?: string;
};

export function ApplyHelper({ userId, userEmail }: ApplyHelperProps) {
  const queryClient = useQueryClient();
  const nameRef = useRef<HTMLInputElement>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);

  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<CoverLetterTemplate | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editContent, setEditContent] = useState("");
  const [copied, setCopied] = useState(false);

  const coverLettersQuery = useQuery<CoverLetterTemplate[], Error>({
    queryKey: ["cover-letters", userId],
    queryFn: getCoverLetters
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCoverLetter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cover-letters"] });
      setSaveSuccess("Template deleted.");
      setSaveError(null);
      setSelectedTemplate(null);
    },
    onError: (err: Error) => setSaveError(err.message || "Failed to delete template")
  });

  const updateMutation = useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      createCoverLetter({ name, content }),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["cover-letters"] });
      setSaveSuccess("Template updated.");
      setSaveError(null);
      setIsEditing(false);
      if (selectedTemplate) {
        deleteMutation.mutate(selectedTemplate.id);
      }
    },
    onError: (err: Error) => setSaveError(err.message || "Failed to update template")
  });

  const handleViewTemplate = (template: CoverLetterTemplate) => {
    setSelectedTemplate(template);
    setEditName(template.name);
    setEditContent(template.content);
    setIsEditing(false);
    setCopied(false);
  };

  const handleCopyTemplate = () => {
    if (selectedTemplate) {
      navigator.clipboard.writeText(selectedTemplate.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleEditTemplate = () => {
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    updateMutation.mutate({
      name: editName,
      content: editContent
    });
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    if (selectedTemplate) {
      setEditName(selectedTemplate.name);
      setEditContent(selectedTemplate.content);
    }
  };

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    e.stopPropagation();

    setSaveError(null);
    setSaveSuccess(null);

    const content = (contentRef.current?.value ?? "").trim();
    const name = (nameRef.current?.value ?? "").trim() || defaultTemplateName();

    if (!content) {
      setSaveError("Template content cannot be empty.");
      return;
    }

    setIsSaving(true);
    try {
      const saved = await createCoverLetter({ name, content });
      queryClient.setQueryData<CoverLetterTemplate[]>(
        ["cover-letters", userId],
        (prev) => [saved, ...(prev ?? []).filter((t) => t.id !== saved.id)]
      );
      queryClient.invalidateQueries({ queryKey: ["cover-letters"] });

      if (nameRef.current) nameRef.current.value = "";
      if (contentRef.current) contentRef.current.value = DEFAULT_TEMPLATE_CONTENT;

      setSaveSuccess(`Saved "${saved.name}" to your account.`);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save template");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="relative z-10 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">Apply Helper</h2>
      <p className="mt-2 text-sm text-slate-600">Quick template snippets to speed up your applications.</p>

      <div className="mt-5 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          Saved templates
        </p>
        {coverLettersQuery.isLoading && (
          <p className="text-sm text-slate-500">Loading your templates...</p>
        )}
        {coverLettersQuery.isError && (
          <p className="text-sm text-rose-600">Could not load templates. Try signing in again.</p>
        )}
        {!coverLettersQuery.isLoading &&
          !coverLettersQuery.isError &&
          (coverLettersQuery.data?.length ?? 0) === 0 && (
            <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              No saved templates yet. Add a name (optional) and click Save Templates.
            </p>
          )}
        {coverLettersQuery.data?.map((tpl) => (
          <div
            key={tpl.id}
            onClick={() => handleViewTemplate(tpl)}
            className="w-full cursor-pointer rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left text-xs text-slate-700 hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-slate-900">{tpl.name}</p>
                <p className="mt-1 line-clamp-3 whitespace-pre-wrap">{tpl.content}</p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteMutation.mutate(tpl.id);
                }}
                disabled={deleteMutation.isPending}
                className="shrink-0 rounded-full bg-white p-1.5 text-slate-500 shadow-sm hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                title="Delete template"
              >
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                  <path
                    fillRule="evenodd"
                    d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c-.84 0-1.673.025-2.5.075V3.75c0-.69.56-1.25 1.25-1.25h2.5c.69 0 1.25.56 1.25 1.25v.325C11.673 4.025 10.84 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      <form className="mt-5 space-y-4" onSubmit={handleSave} noValidate>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Create new template</p>
        <input
          ref={nameRef}
          type="text"
          name="template_name"
          defaultValue=""
          placeholder="e.g. Junior DevOps - concise (optional)"
          className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
        <textarea
          ref={contentRef}
          name="template_content"
          defaultValue={DEFAULT_TEMPLATE_CONTENT}
          rows={6}
          placeholder="Write your template using {{company}}, {{title}} placeholders..."
          className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
        {saveError && <p className="text-sm font-medium text-rose-600">{saveError}</p>}
        {saveSuccess && <p className="text-sm font-medium text-emerald-600">{saveSuccess}</p>}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-70"
          >
            {isSaving ? "Saving..." : "Save Template"}
          </button>
          <button
            type="button"
            disabled={isSaving}
            onClick={() => {
              if (nameRef.current) nameRef.current.value = "";
              if (contentRef.current) contentRef.current.value = DEFAULT_TEMPLATE_CONTENT;
              setSaveError(null);
              setSaveSuccess(null);
            }}
            className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Reset
          </button>
        </div>
        <p className="text-xs text-slate-400">
          Only you see templates saved while signed in. Name is optional — we auto-name if left blank.
        </p>
      </form>

      {/* Template View/Edit Modal */}
      {selectedTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-start justify-between">
              <div className="flex-1">
                {isEditing ? (
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-lg font-semibold text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                ) : (
                  <h3 className="text-lg font-semibold text-slate-900">{selectedTemplate.name}</h3>
                )}
              </div>
              <button
                onClick={() => setSelectedTemplate(null)}
                className="ml-4 rounded-full p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={20} />
              </button>
            </div>

            {isEditing ? (
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={12}
                className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            ) : (
              <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-4">
                <pre className="whitespace-pre-wrap text-sm text-slate-700">{selectedTemplate.content}</pre>
              </div>
            )}

            <div className="mt-4 flex items-center justify-between">
              <div className="flex gap-2">
                {!isEditing && (
                  <>
                    <button
                      onClick={handleCopyTemplate}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      {copied ? (
                        <>
                          <Check size={16} className="text-green-600" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy size={16} />
                          Copy
                        </>
                      )}
                    </button>
                    <button
                      onClick={handleEditTemplate}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      <Edit2 size={16} />
                      Edit
                    </button>
                  </>
                )}
                {isEditing && (
                  <>
                    <button
                      onClick={handleSaveEdit}
                      disabled={updateMutation.isPending}
                      className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {updateMutation.isPending ? "Saving..." : "Save Changes"}
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
              {!isEditing && (
                <button
                  onClick={() => {
                    deleteMutation.mutate(selectedTemplate.id);
                  }}
                  disabled={deleteMutation.isPending}
                  className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
