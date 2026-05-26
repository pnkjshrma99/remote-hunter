"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, logout, isAuthenticated, isLoading: authLoading } = useAuth();

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-gradient-to-r from-white to-slate-50">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-5 py-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="relative flex-shrink-0">
              <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 opacity-20 blur-sm"></div>
              <img src="/logo.svg" alt="Remote Job Hunter Logo" className="relative h-16 w-16" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">Remote Job Hunter</h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
                The remote hiring command center for candidates, consultants, and talent teams who want
                data-driven job discovery, source intelligence, and faster applications — without manual tracking.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {authLoading ? (
              <div className="h-9 w-24 animate-pulse rounded bg-slate-200" />
            ) : isAuthenticated && user ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-sm text-slate-700">
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-slate-700 text-xs font-semibold text-white">
                    {user.full_name?.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
                  </span>
                  <span>{user.full_name || user.email.split("@")[0]}</span>
                </div>
                <button
                  type="button"
                  onClick={() => logout()}
                  className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                >
                  Logout
                </button>
              </div>
            ) : (
              <>
                <Link href="/login" className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100">
                  Sign in
                </Link>
                <Link href="/register" className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-[1400px] px-5 py-16 lg:py-24">
        <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div className="space-y-7">
            <span className="inline-flex rounded-full bg-indigo-100 px-4 py-1 text-xs font-semibold uppercase tracking-[0.28em] text-indigo-700">
              Built for remote career growth
            </span>
            <h2 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">
              Discover remote work with more clarity, speed, and confidence.
            </h2>
            <p className="max-w-2xl text-lg leading-8 text-slate-600">
              Remote Job Hunter gives you a single place to discover remote opportunities, tune your search across sources,
              analyze job market signals, and turn opportunities into applications with smart outreach support.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-semibold text-slate-900">CV-based matching</p>
                <p className="mt-3 text-sm text-slate-600">
                  Upload your CV to get AI-powered job matching based on your skills, experience, and job roles.
                </p>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <p className="text-sm font-semibold text-slate-900">Smart sourcing</p>
                <p className="mt-3 text-sm text-slate-600">
                  Scrape the best job boards, compare source performance, and focus on the companies where remote talent wins.
                </p>
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link href="/scraper" className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">
                Launch scraper
              </Link>
              <Link href="/cv-upload" className="inline-flex items-center justify-center rounded-full border border-indigo-600 bg-indigo-50 px-6 py-3 text-sm font-semibold text-indigo-700 hover:bg-indigo-100">
                CV-based matching
              </Link>
              <button
                type="button"
                onClick={() => {
                  document.getElementById("why")?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
                className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Learn how it works
              </button>
            </div>
          </div>

          <div className="overflow-hidden rounded-[2rem] bg-gradient-to-br from-indigo-600 via-sky-600 to-purple-600 p-1 shadow-xl">
            <div className="h-full rounded-[1.75rem] bg-slate-950 p-8 text-white">
              <div className="mb-8 space-y-6">
                <div className="rounded-3xl bg-white/10 p-5 backdrop-blur-sm">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-200">Remote workspace preview</p>
                  <h3 className="mt-3 text-3xl font-bold">Launch your search cockpit</h3>
                  <p className="mt-4 text-sm leading-7 text-slate-300">
                    Use a dedicated scraper workspace to compare sources, refine filters, and turn remote job signals into actionable opportunities.
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-3xl bg-white/10 p-5 backdrop-blur-sm">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Source intelligence</p>
                    <p className="mt-2 text-xl font-bold">Board rankings</p>
                  </div>
                  <div className="rounded-3xl bg-white/10 p-5 backdrop-blur-sm">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Search cadence</p>
                    <p className="mt-2 text-xl font-bold">Daily refresh</p>
                  </div>
                </div>
              </div>
              <div className="rounded-3xl bg-white/5 p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Why it matters</p>
                <div className="mt-4 space-y-4 text-sm text-slate-300">
                  <div>
                    <p className="font-semibold text-white">Stay ahead of the market</p>
                    <p>See emerging remote roles, top boards, and source signals before other candidates.</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white">Focus on the right opportunities</p>
                    <p>Filter by remote eligibility, company fit, and stack to make every scrape count.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <section id="why" className="mt-16 rounded-[2rem] border border-slate-200 bg-white p-10 shadow-sm">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">Why Remote Job Hunter</p>
              <h3 className="mt-4 text-3xl font-bold tracking-tight text-slate-950">A product designed to make remote job search clear and effective.</h3>
              <p className="mt-4 text-base leading-8 text-slate-600">
                We help users understand the market, spot the best boards, and take action with a single workspace that combines scraping, analytics, and applied-job tracking.
              </p>
            </div>
            <div className="space-y-4">
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                <p className="text-sm font-semibold text-slate-900">CV Analysis</p>
                <p className="mt-2 text-sm text-slate-600">Upload your CV to get AI-powered analysis of your skills, experience, and job roles with personalized job matching.</p>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                <p className="text-sm font-semibold text-slate-900">Focused search</p>
                <p className="mt-2 text-sm text-slate-600">No homepage scraping UI. The scraper page is the place for actual search configuration, run history, and job analytics.</p>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
                <p className="text-sm font-semibold text-slate-900">Actionable output</p>
                <p className="mt-2 text-sm text-slate-600">View job matches, filter by stack and company size, and apply directly using smart templates and source analytics.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-16 grid gap-6 lg:grid-cols-3">
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h4 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">What we do</h4>
            <p className="mt-4 text-sm text-slate-600">Aggregate remote roles, provide market intelligence, and help you apply faster with a modern remote job workflow.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h4 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">Who it is for</h4>
            <p className="mt-4 text-sm text-slate-600">Remote-first professionals, job seekers, and talent teams who need visibility into remote roles and source health.</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
            <h4 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">How it helps</h4>
            <p className="mt-4 text-sm text-slate-600">Use the dedicated scraper workspace to tune searches, compare results, and measure the best channels for remote hiring.</p>
          </div>
        </section>

        <section className="mt-16 rounded-[2rem] bg-gradient-to-r from-slate-900 via-indigo-900 to-slate-950 p-10 text-white shadow-2xl">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-300">Ready to build a better remote job workflow?</p>
              <h3 className="mt-4 text-3xl font-bold tracking-tight">Start on the scraper page and let the product guide your search.</h3>
              <p className="mt-5 max-w-xl text-sm leading-7 text-slate-200">
                The home page is your product story and understanding center — the scraper page is where the real search and analytics happen.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-3xl bg-slate-900/90 p-6">
                <p className="text-sm font-semibold text-sky-300">Remote market view</p>
                <p className="mt-3 text-sm text-slate-200">Know where remote roles are trending and which companies are hiring.</p>
              </div>
              <div className="rounded-3xl bg-slate-900/90 p-6">
                <p className="text-sm font-semibold text-sky-300">Focused experience</p>
                <p className="mt-3 text-sm text-slate-200">Keep product context on the homepage and search controls in the scraper workspace.</p>
              </div>
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
