import { CoverLetterTemplate, Job, JobProfile, JobStats } from "@/types/job";

export type { JobProfile };

export type CategoryResponse = {
  categories: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

async function tryRefreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    if (!response.ok) return false;

    const tokens = (await response.json()) as {
      access_token: string;
      refresh_token: string;
    };
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function parseApiError(text: string, status: number): Error {
  try {
    const parsed = JSON.parse(text) as { detail?: string | { msg: string }[] };
    if (typeof parsed.detail === "string") {
      return new Error(parsed.detail);
    }
    if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) {
      return new Error(parsed.detail[0].msg);
    }
  } catch (err) {
    if (err instanceof Error && !(err instanceof SyntaxError)) {
      return err;
    }
  }
  return new Error(text || `Request failed: ${status}`);
}

async function request<T>(path: string, options?: RequestInit, retried = false): Promise<T> {
  const accessToken = getAccessToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
      ...(options?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/refresh" && !retried) {
      const refreshed = await tryRefreshAccessToken();
      if (refreshed) {
        return request<T>(path, options, true);
      }
    }

    const text = await response.text();
    throw parseApiError(text, response.status);
  }

  // 204 No Content or empty body
  const text = await response.text();
  if (response.status === 204 || !text) {
    return undefined as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Invalid JSON response: ${text.slice(0, 100)}`);
  }
}

export function hasAccessToken(): boolean {
  return !!getAccessToken();
}

export type JobQuery = {
  search?: string;
  source?: string;
  tech_stack?: string;
  company_size?: string;
  experience_level?: string;
  region_eligibility?: string;
  is_verified_remote?: string;
  seniority_tag?: string;
  is_duplicate?: string;
  is_sponsored?: string;
  is_hot_job?: string;
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

export function getLatestScrapeRun() {
  return request<any>("/jobs/scrape-runs/latest");
}

export function getScrapeRun(runId: number) {
  return request<any>(`/jobs/scrape-runs/${runId}`);
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
  error_message?: string;
};

export function runScrape(config: ScrapeConfig) {
  return request<any>("/jobs/scrape", {
    method: "POST",
    body: JSON.stringify(config)
  }).then(async (queued: any) => {
    // Background scrape — poll until complete
    if (queued.status === "queued" && queued.scrape_run_id) {
      const runId = queued.scrape_run_id;
      return new Promise<ScrapeResult>((resolve, reject) => {
        const poll = setInterval(async () => {
          try {
            const run = await getScrapeRun(runId);
            if (run.status === "success" || run.status === "failed") {
              clearInterval(poll);
              resolve({
                status: run.status,
                jobs_found: run.jobs_found || 0,
                jobs_new: run.jobs_new || 0,
                sources_run: run.sources_run ? run.sources_run.split(", ") : [],
                error_message: run.error_message,
              });
            }
          } catch (e) {
            clearInterval(poll);
            reject(e);
          }
        }, 2000);
        // Timeout after 5 minutes
        setTimeout(() => {
          clearInterval(poll);
          reject(new Error("Scrape timed out"));
        }, 300000);
      });
    }
    return queued;
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

// CV APIs
export function uploadCV(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  
  return fetch(`${API_BASE}/cv/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAccessToken()}`,
    },
    body: formData,
  }).then(async (response) => {
    if (!response.ok) {
      const text = await response.text();
      throw parseApiError(text, response.status);
    }
    return response.json();
  });
}

export function getMyCVs() {
  return request<any[]>("/cv/my-cvs");
}

export function getCV(cvId: number) {
  return request<any>(`/cv/${cvId}`);
}

export function updateCV(cvId: number, data: {
  skills?: string[];
  tech_stack?: string[];
  job_roles?: string[];
  keywords?: string[];
  experience_years?: number | null;
}) {
  return request<any>(`/cv/${cvId}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  });
}

export function deleteCV(cvId: number) {
  return request<{ message: string }>(`/cv/${cvId}`, {
    method: "DELETE"
  });
}

export function matchJobsForCV(cvId: number) {
  return request<{ message: string; matches_count: number; scraped_jobs: number }>(`/cv/${cvId}/match-jobs`, {
    method: "POST"
  });
}

export function getMatchedJobs(cvId: number, postedWithinDays?: number) {
  const params = postedWithinDays ? `?posted_within_days=${postedWithinDays}` : "";
  return request<any[]>(`/cv/${cvId}/matched-jobs${params}`);
}

// ============================================================================
// User Profile APIs
// ============================================================================

export type WorkExperience = {
  id?: number;
  profile_id?: number;
  company: string;
  title: string;
  location?: string | null;
  start_date: string;
  end_date?: string | null;
  currently_working?: boolean;
  description?: string | null;
  tech_used?: string[] | null;
  achievements?: string[] | null;
};

export type Education = {
  id?: number;
  profile_id?: number;
  school: string;
  degree: string;
  field_of_study?: string | null;
  location?: string | null;
  start_date: string;
  end_date?: string | null;
  currently_studying?: boolean;
  gpa?: string | null;
  achievements?: string[] | null;
};

export type UserProfile = {
  id: number;
  user_id: number;
  full_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  middle_name?: string | null;
  phone?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  website?: string | null;
  headline?: string | null;
  summary?: string | null;
  authorized_to_work_in_us: boolean;
  visa_sponsorship_needed: boolean;
  currently_employed: boolean;
  notice_period_days?: number | null;
  desired_roles?: string[] | null;
  desired_salary_min?: number | null;
  desired_salary_max?: number | null;
  desired_salary_currency: string;
  preferred_locations?: string[] | null;
  remote_only: boolean;
  open_to_relocation: boolean;
  open_to_contract: boolean;
  open_to_fulltime: boolean;
  how_did_you_hear?: string | null;
  cover_letter_intro?: string | null;
  additional_notes?: string | null;
  gender?: string | null;
  hispanic_latino?: string | null;
  veteran_status?: string | null;
  disability_status?: string | null;
  custom_answers?: Record<string, string> | null;
  experiences: WorkExperience[];
  education: Education[];
  created_at?: string;
  updated_at?: string;
};

export type ProfileUpdate = Partial<Omit<UserProfile, "id" | "user_id" | "experiences" | "education" | "created_at" | "updated_at">>;

export function getProfile() {
  return request<UserProfile>("/profile");
}

export function updateProfile(data: ProfileUpdate) {
  return request<UserProfile>("/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function addExperience(data: WorkExperience) {
  return request<WorkExperience>("/profile/experiences", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateExperience(id: number, data: WorkExperience) {
  return request<WorkExperience>(`/profile/experiences/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteExperience(id: number) {
  return request<void>(`/profile/experiences/${id}`, {
    method: "DELETE",
  });
}

export function addEducation(data: Education) {
  return request<Education>("/profile/education", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateEducation(id: number, data: Education) {
  return request<Education>(`/profile/education/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteEducation(id: number) {
  return request<void>(`/profile/education/${id}`, {
    method: "DELETE",
  });
}

// ============================================================================
// Apply APIs
// ============================================================================

export type ApplyResult = {
  success: boolean;
  message: string;
  ats_type: string;
};

export function applyToJob(jobId: number) {
  return request<ApplyResult>(`/jobs/${jobId}/apply`, {
    method: "POST",
  });
}

export type AutofillField = {
  label: string;
  value: string;
  field_type: string;
};

export type AutofillSection = {
  title: string;
  fields: AutofillField[];
};

export type AutofillData = {
  job_url: string;
  job_title: string;
  company: string;
  sections: AutofillSection[];
  resume_url: string;
  resume_name: string;
};

export function autofillJob(jobId: number) {
  return request<AutofillData>(`/jobs/${jobId}/autofill`, {
    method: "POST",
  });
}

/* ─── API Tokens for Extension ─────────────────────────────── */

export type ApiToken = {
  id: number;
  name: string;
  token: string;
  last_used_at: string | null;
  created_at: string;
};

export function createApiToken(name: string) {
  return request<ApiToken>("/auth/tokens", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listApiTokens() {
  return request<ApiToken[]>("/auth/tokens");
}

export function revokeApiToken(tokenId: number) {
  return request<void>(`/auth/tokens/${tokenId}`, {
    method: "DELETE",
  });
}
