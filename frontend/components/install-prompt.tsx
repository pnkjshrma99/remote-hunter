"use client";

import { useState } from "react";
import { Chrome, ExternalLink, Check, Loader2, Copy, Key } from "lucide-react";

import { createApiToken } from "@/lib/api";

const EDGE_STORE_URL = process.env.NEXT_PUBLIC_EDGE_EXTENSION_URL || "https://microsoftedge.microsoft.com/addons/detail/remote-hunter-autofill/0RDCKG9N97QH";

export function InstallPrompt({
  jobUrl,
  jobTitle,
  company,
  onClose,
}: {
  jobUrl: string;
  jobTitle: string;
  company: string;
  onClose: () => void;
}) {
  const [generatedToken, setGeneratedToken] = useState("");
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleGenerateToken = async () => {
    setGenerating(true);
    try {
      const token = await createApiToken("Chrome Extension");
      setGeneratedToken(token.token);
    } catch (err: any) {
      alert(err.message || "Failed to generate token");
    }
    setGenerating(false);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 pt-10 backdrop-blur-sm">
      <div className="relative mx-4 mb-10 w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-2xl">
        {/* Header */}
        <div className="rounded-t-2xl border-b border-slate-100 bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-5 text-white">
          <div className="mb-1 flex items-center gap-2">
            <Chrome className="h-5 w-5" />
            <h2 className="text-lg font-bold">Auto-fill with Extension</h2>
          </div>
          <p className="text-sm text-indigo-100">
            {jobTitle} @ {company}
          </p>
        </div>

        <div className="px-6 py-5">
          {!generatedToken ? (
            <div className="space-y-4">
              <p className="text-sm text-slate-600">
                Install the extension, generate a token, paste it in the popup — then open the job page and it auto-fills.
              </p>

              <div className="space-y-3 rounded-xl bg-slate-50 p-4">
                <div className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">1</span>
                  <div>
                    <p className="text-sm font-medium text-slate-800">Install extension</p>
                    <p className="text-xs text-slate-500">
                      <a href={EDGE_STORE_URL} target="_blank" rel="noreferrer" className="font-medium text-indigo-600 underline">
                        Add to Browser
                      </a>
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      ⚡ Manual:{" "}
                      <a href="/api/extension/download" download className="font-medium text-indigo-600 underline">
                        download zip
                      </a>
                      {" "}→ unzip →{" "}
                      <code className="rounded bg-slate-200 px-1 text-[11px]">chrome://extensions</code>
                      {" "}→ Developer mode → Load unpacked
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">2</span>
                  <div>
                    <p className="text-sm font-medium text-slate-800">Generate token</p>
                    <p className="text-xs text-slate-500">Click the button below.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">3</span>
                  <div>
                    <p className="text-sm font-medium text-slate-800">Connect &amp; open job</p>
                    <p className="text-xs text-slate-500">Open extension popup → paste token → click "Open Job Application" → auto-fills.</p>
                  </div>
                </div>
              </div>

              <button
                onClick={handleGenerateToken}
                disabled={generating}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Key className="h-4 w-4" />
                )}
                {generating ? "Generating..." : "Generate API Token"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <div className="mb-1 flex items-center gap-2">
                  <Key className="h-4 w-4 text-emerald-600" />
                  <p className="text-sm font-semibold text-emerald-800">Token generated!</p>
                </div>
                <p className="mb-3 text-xs text-emerald-600">Copy it → open extension popup → paste → connect.</p>
                <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-2.5 font-mono text-xs text-slate-700 ring-1 ring-emerald-200">
                  <span className="flex-1 break-all">{generatedToken}</span>
                  <button
                    onClick={handleCopy}
                    className="shrink-0 rounded-md p-1.5 text-emerald-600 hover:bg-emerald-100"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
                {copied && <p className="mt-1.5 text-xs font-medium text-emerald-600">✓ Copied! Now paste it in the extension popup.</p>}
              </div>

              <a
                href={jobUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                <ExternalLink className="h-4 w-4" />
                Open Job Application
              </a>
            </div>
          )}
        </div>

        <div className="rounded-b-2xl border-t border-slate-100 bg-slate-50 px-6 py-3">
          <button onClick={onClose} className="w-full text-center text-xs text-slate-400 hover:text-slate-600">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
