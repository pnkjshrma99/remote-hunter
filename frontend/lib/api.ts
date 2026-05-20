import { CoverLetterTemplate, Job, JobStats } from "@/types/job";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type JobQuery = {
  search?: string;
  source?: string;
  tech_stack?: string;
  company_size?: string;
  is_applied?: string;
};

export type ScrapeConfig = {
  query: string;
  min_experience?: number | null;
  max_experience?: number | null;
  posted_within_days?: number | null;
  remote_only: boolean;
  global_or_india: boolean;
  exclude_indian_hq: boolean;
  strict_experience: boolean;
  strict_title: boolean;
  strict_junior: boolean;
  send_alerts: boolean;
  sources: string[];
  linkedin_urls: string[];
};

export function getJobs(query: JobQuery) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, value);
  });
  params.set("limit", "250");
  return request<Job[]>(`/jobs?${params.toString()}`);
}

export function getStats() {
  return request<JobStats>("/jobs/stats");
}

export function markApplied(id: number, isApplied: boolean) {
  return request<Job>(`/jobs/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ is_applied: isApplied })
  });
}

export function runScrape(config: ScrapeConfig) {
  return request<{ status: string; jobs_found?: number; jobs_new?: number }>("/jobs/scrape", {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function getCoverLetters() {
  return request<CoverLetterTemplate[]>("/cover-letters");
}

export function createCoverLetter(payload: { name: string; content: string; company_type?: string }) {
  return request<CoverLetterTemplate>("/cover-letters", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function deleteCoverLetter(templateId: number) {
  return request<{ status: string }>(`/cover-letters/${templateId}`, {
    method: "DELETE"
  });
}
