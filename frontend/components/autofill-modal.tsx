"use client";

import { ExternalLink, X, Copy, Check, FileText } from "lucide-react";
import { useState } from "react";

import type { AutofillData } from "@/lib/api";

export function AutofillModal({
  data,
  onClose,
}: {
  data: AutofillData;
  onClose: () => void;
}) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyValue = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const copyAll = async () => {
    const lines: string[] = [];
    for (const section of data.sections) {
      lines.push(`\n── ${section.title} ──`);
      for (const field of section.fields) {
        lines.push(`${field.label}: ${field.value}`);
      }
    }
    await navigator.clipboard.writeText(lines.join("\n").trim());
    setCopiedKey("__all__");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 pt-10 backdrop-blur-sm">
      <div className="relative mx-4 mb-10 w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 z-10 rounded-t-2xl border-b border-slate-100 bg-white px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Quick Apply Assistant</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                {data.job_title} @ {data.company}
              </p>
            </div>
            <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Job link */}
        <div className="border-b border-slate-100 bg-indigo-50/50 px-6 py-3">
          <div className="flex items-center justify-between">
            <a
              href={data.job_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-indigo-700 hover:text-indigo-900"
            >
              <ExternalLink className="h-4 w-4" />
              Open job posting in new tab
            </a>
            {data.resume_url && (
              <a
                href={data.resume_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-200"
              >
                <FileText className="h-3.5 w-3.5" />
                {data.resume_name || "Download Resume"}
              </a>
            )}
          </div>
        </div>

        {/* Profile data sections */}
        <div className="space-y-4 px-6 py-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Copy your profile data into the application form
            </p>
            <button
              onClick={copyAll}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              {copiedKey === "__all__" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              {copiedKey === "__all__" ? "Copied!" : "Copy All"}
            </button>
          </div>

          {data.sections.map((section, si) => (
            <div key={si} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">
                {section.title}
              </h3>
              <div className="space-y-2">
                {section.fields.map((field, fi) => {
                  const key = `${si}-${fi}`;
                  return (
                    <div
                      key={fi}
                      className="group flex items-start justify-between rounded-lg bg-white px-3 py-2.5 ring-1 ring-slate-200/60 transition hover:ring-indigo-300"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                          {field.label}
                        </p>
                        <p className="mt-0.5 break-words text-sm text-slate-800">
                          {field.value}
                        </p>
                      </div>
                      <button
                        onClick={() => copyValue(field.value, key)}
                        className="ml-3 shrink-0 rounded-md p-1.5 text-slate-400 opacity-0 transition hover:bg-indigo-50 hover:text-indigo-600 group-hover:opacity-100"
                        title="Copy value"
                      >
                        {copiedKey === key ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 rounded-b-2xl border-t border-slate-100 bg-slate-50 px-6 py-3 text-center text-xs text-slate-400">
          Paste your data into the form fields on the job site, then submit manually.
        </div>
      </div>
    </div>
  );
}
