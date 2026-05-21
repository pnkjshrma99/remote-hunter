import { CoverLetterTemplate, Job, JobStats } from "@/types/job";

export type JobProfile = {
  id: string;
  name: string;
  keywords: string[];
  description: string;
  min_experience: number;
  max_experience: number;
  role_category: string;
};

export type CategoryResponse = {
  categories: string[];
};

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
  job_profile_id?: string | null;
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

export type ScrapeResult = {
  status: string;
  jobs_found?: number;
  jobs_new?: number;
  duplicate_jobs?: number;
  verified_remote_jobs?: number;
  total_sources?: number;
  sources_run?: string[];
  query?: string;
  duration_seconds?: number;
};

export function runScrape(config: ScrapeConfig) {
  return request<ScrapeResult>("/jobs/scrape", {
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

// Job Profile APIs
export function getJobProfiles() {
  return request<JobProfile[]>("/jobs/profiles/list");
}

export function getJobProfile(profileId: string) {
  return request<JobProfile>(`/jobs/profiles/${profileId}`);
}

export function getJobCategories() {
  return request<CategoryResponse>("/jobs/profiles/categories/list");
}

// Analytics APIs
export function getAnalyticsDashboard() {
  return request<any>("/analytics/dashboard");
}

export function getSourcePerformance() {
  return request<any>("/analytics/source-performance");
}

export function getMarketHeatmap() {
  return request<any>("/analytics/market-heatmap");
}

export function getSalaryInsights() {
  return request<any>("/analytics/salary-insights");
}

export function getHiringTrends(days: number = 30) {
  return request<any>(`/analytics/hiring-trends?days=${days}`);
}

// Company APIs
export function getCompanies(search?: string) {
  const params = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<any>(`/companies${params}`);
}

export function getCompany(companyName: string) {
  return request<any>(`/companies/${encodeURIComponent(companyName)}`);
}

// Saved Searches APIs
export function getSavedSearches(userEmail: string) {
  return request<any>(`/saved-searches?user_email=${encodeURIComponent(userEmail)}`);
}

export function createSavedSearch(userEmail: string, name: string, config: ScrapeConfig) {
  return request<any>(`/saved-searches?user_email=${encodeURIComponent(userEmail)}&name=${encodeURIComponent(name)}`, {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function runSavedSearch(searchId: number) {
  return request<any>(`/saved-searches/${searchId}/run`, {
    method: "POST"
  });
}

// Subscription APIs
export function getSubscriptionStatus(userEmail: string) {
  return request<any>(`/subscriptions/status?user_email=${encodeURIComponent(userEmail)}`);
}

export function upgradeSubscription(userEmail: string, tier: string) {
  return request<any>(`/subscriptions/upgrade?user_email=${encodeURIComponent(userEmail)}&tier=${tier}`, {
    method: "POST"
  });
}

// Learning Paths APIs
export function getLearningPaths(featuredOnly: boolean = false) {
  return request<any>(`/learning-paths?featured_only=${featuredOnly}`);
}

export function getLearningPath(profileId: string) {
  return request<any>(`/learning-paths/${profileId}`);
}

// Job Bundles APIs
export function getJobBundles(category?: string, featuredOnly: boolean = false) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (featuredOnly) params.set("featured_only", "true");
  return request<any>(`/job-bundles?${params.toString()}`);
}

export function getJobBundle(bundleId: number) {
  return request<any>(`/job-bundles/${bundleId}`);
}

// Hot Jobs API
export function getHotJobs(limit: number = 10) {
  return request<Job[]>(`/jobs/hot?limit=${limit}`);
}
