// TypeScript types mirroring the FastAPI backend schemas.
// Keep in sync with backend/app/routers/jobs.py (JobOut, JobSourceOut)
// and backend/app/routers/scrape.py (ScrapeRunOut).

export type ApplicationState =
  | "NEW"
  | "APPLIED";

export const APPLICATION_STATES: ApplicationState[] = [
  "NEW",
  "APPLIED",
];

export interface JobSource {
  id: number;
  platform: string;
  url: string;
  scraped_date: string; // ISO 8601
}

export interface Job {
  id: number;
  job_hash: string;
  job_title: string;
  company_name: string;
  location_raw: string | null;
  location_normalized: string | null;
  role_match: string;
  salary_disclosed: boolean;
  salary_min: number | null;
  salary_max: number | null;
  description_clean: string | null;
  image_url: string | null;
  posted_date: string | null; // ISO 8601
  application_state: ApplicationState;
  state_updated_date: string; // ISO 8601
  created_at: string; // ISO 8601
  sources: JobSource[];
}

export interface Source {
  id: number;
  name: string;
  enabled: boolean;
  last_scraped_at: string | null; // ISO 8601
}

export interface KeywordConfig {
  include: string[];
  intern_modifiers: string[];
  exclude: string[];
}

export interface SiteResult {
  found: number;
  new: number;
  duplicates: number;
  error: string | null;
}

export interface ScrapeRun {
  id: number;
  started_at: string; // ISO 8601
  finished_at: string | null; // ISO 8601
  status: "RUNNING" | "COMPLETED" | "FAILED";
  triggered_by: string;
  site_results: Record<string, SiteResult>;
}
