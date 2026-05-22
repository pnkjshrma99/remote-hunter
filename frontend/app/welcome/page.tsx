"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

export default function WelcomePage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 to-white">
      <header className="max-w-6xl mx-auto flex w-full items-center justify-between gap-4 px-6 py-6 md:py-8">
        <h1 className="text-2xl font-extrabold text-indigo-700">Remote Job Hunter</h1>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Link href="/login" className="text-sm font-medium text-stone-700">Sign in</Link>
          <Link href="/scraper" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow">Run scraper</Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <section className="bg-white rounded-2xl p-10 shadow-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-3xl font-bold text-stone-900 mb-4">Welcome — you're all set</h2>
              <p className="text-stone-600 mb-6">Thanks for signing up. Remote Job Hunter helps you discover remote jobs, run scheduled scrapes, and view analytics for your searches. Get started by running your first search or exploring the dashboard.</p>
              <div className="flex gap-3">
                <Link href="/scraper" className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow">Run your first search</Link>
                <Link href="/register" className="rounded border border-stone-300 px-4 py-2 text-sm font-semibold">Complete profile</Link>
              </div>
              <p className="mt-4 text-xs text-stone-500">You can always return to the scraper from the header or the home page.</p>
            </div>

            <div className="space-y-4">
              <div className="rounded-lg bg-gradient-to-r from-indigo-100 to-white p-4 border border-stone-100">
                <h3 className="font-semibold text-stone-900 mb-2">One-click scrapes</h3>
                <p className="text-sm text-stone-600">Run searches across multiple sources and surface fresh remote roles.</p>
              </div>

              <div className="rounded-lg bg-gradient-to-r from-rose-50 to-white p-4 border border-stone-100">
                <h3 className="font-semibold text-stone-900 mb-2">Save & apply</h3>
                <p className="text-sm text-stone-600">Save matches and keep track of applications from one place.</p>
              </div>

              <div className="rounded-lg bg-gradient-to-r from-emerald-50 to-white p-4 border border-stone-100">
                <h3 className="font-semibold text-stone-900 mb-2">Analytics</h3>
                <p className="text-sm text-stone-600">See trends across your searches and optimize filters over time.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-stone-100">
            <h4 className="font-semibold text-stone-900 mb-2">Step 1</h4>
            <p className="text-sm text-stone-600">Create a saved search for your target keywords and locations.</p>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-stone-100">
            <h4 className="font-semibold text-stone-900 mb-2">Step 2</h4>
            <p className="text-sm text-stone-600">Run a scrape or schedule automatic scrapes.</p>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-stone-100">
            <h4 className="font-semibold text-stone-900 mb-2">Step 3</h4>
            <p className="text-sm text-stone-600">Review results, save favorites, and apply.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
