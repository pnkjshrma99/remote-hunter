export type Job = {
  id: number;
  external_id: string;
  source: string;
  title: string;
  company: string;
  url: string;
  description?: string | null;
  location?: string | null;
  salary?: string | null;
  tech_stack?: string | null;
  company_size?: string | null;
  experience_level?: string | null;
  region_eligibility?: string | null;
  posted_at?: string | null;
  scraped_at: string;
  is_applied: boolean;
  is_active: boolean;
};

export type JobStats = {
  total_jobs: number;
  applied_count: number;
  new_today: number;
  by_tech_stack: Record<string, number>;
  by_company_size: Record<string, number>;
  by_day: Record<string, number>;
  by_source: Record<string, number>;
};

export type CoverLetterTemplate = {
  id: number;
  name: string;
  content: string;
  company_type?: string | null;
  created_at: string;
  updated_at: string;
};
