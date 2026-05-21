# Architecture & System Design

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    REMOTE JOB HUNTER v2.0                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Scrape Config Panel                                     │  │
│  │  ┌─────────────────────────────────────────────────────┐│  │
│  │  │ Job Profile Dropdown [Select DevOps Engineer]        ││  │
│  │  │ - DevOps Engineer (Junior)                           ││  │
│  │  │ - DevOps Engineer (Mid-Level)                        ││  │
│  │  │ - Full Stack Developer (Junior)                      ││  │
│  │  │ - ... (14 total profiles)                            ││  │
│  │  ├─────────────────────────────────────────────────────┤│  │
│  │  │ Manual Keywords Input [or use dropdown]              ││  │
│  │  │ Min Years: [_] Max Years: [_] Days: [__]             ││  │
│  │  ├─────────────────────────────────────────────────────┤│  │
│  │  │ Source Selection (checkboxes)                        ││  │
│  │  │ ☑ Remotive  ☑ Remote OK  ☑ WWR  ☑ Stack Overflow   ││  │
│  │  │ ☑ AngelList ☑ JustRemote ☑ NoFluffJobs ...         ││  │
│  │  │                                                       ││  │
│  │  │ [RUN SCRAPER] → POST /api/v1/jobs/scrape            ││  │
│  │  └─────────────────────────────────────────────────────┘│  │
│  │                                                          │  │
│  │  API Calls:                                              │  │
│  │  • GET /api/v1/jobs/profiles/list (on load)             │  │
│  │  • POST /api/v1/jobs/scrape (on submit)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                     API LAYER (FastAPI)                          │
│                                                                  │
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║ Job Profile Endpoints (NEW)                              ║  │
│  ║ • GET /jobs/profiles/list                                ║  │
│  ║ • GET /jobs/profiles/{id}                                ║  │
│  ║ • GET /jobs/profiles/categories/list                     ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│                                                                  │
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║ Job Scraping Endpoints (UPDATED)                         ║  │
│  ║ • POST /jobs/scrape (now with job_profile_id support)   ║  │
│  ║ • GET /jobs (list with filters)                          ║  │
│  ║ • GET /jobs/stats                                        ║  │
│  ║ • PATCH /jobs/{id}                                       ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│                                                                  │
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║ Services Layer                                           ║  │
│  ║ • _criteria_from_request()  [UPDATED with profiles]     ║  │
│  ║ • run_scrape()                                           ║  │
│  ║ • list_jobs()                                            ║  │
│  ║ • update_job()                                           ║  │
│  ║ • get_stats()                                            ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    DOMAIN LOGIC LAYER                            │
│                                                                  │
│  ┌─ Job Profiles (NEW) ──────────────────────────────────────┐  │
│  │ • job_profiles.py                                         │  │
│  │   - 14 JobProfile objects                                 │  │
│  │   - Functions: get_profile_by_id(), list_all_profiles()  │  │
│  │   - 9 job categories                                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ Search Criteria (UPDATED) ───────────────────────────────┐  │
│  │ • filters.py - SearchCriteria                             │  │
│  │   - Added: job_profile_id field                           │  │
│  │   - Maintains backward compatibility                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ Schema Definitions (UPDATED) ────────────────────────────┐  │
│  │ • schemas/job.py - ScrapeRequest                          │  │
│  │   - Added: job_profile_id field                           │  │
│  │   - Response models: JobProfileResponse, CategoryResponse │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   SCRAPER ORCHESTRATION                          │
│                                                                  │
│  ┌─ Scraper Registry ────────────────────────────────────────┐  │
│  │ • registry.py                                             │  │
│  │   SCRAPER_REGISTRY = {                                    │  │
│  │     "remotive": RemotiveScraper,                          │  │
│  │     "remoteok": RemoteOKScraper,                          │  │
│  │     "weworkremotely": WeWorkRemotelyScraper,              │  │
│  │     ...                                                   │  │
│  │     "stackoverflow": StackOverflowScraper,        [NEW]   │  │
│  │     "angellist": AngelListScraper,                [NEW]   │  │
│  │     "justremote": JustRemoteScraper,              [NEW]   │  │
│  │     "nofluffjobs": NoFluffJobsScraper             [NEW]   │  │
│  │   }  [15 total scrapers]                                  │  │
│  │                                                            │  │
│  │   run_all_scrapers(criteria) →                            │  │
│  │   Executes selected scrapers in parallel                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    SCRAPER INSTANCES (15)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Original Scrapers (10)          New Scrapers (5)        │   │
│  │ • Remotive         (API)        • Stack Overflow (RSS) │   │
│  │ • Remote OK        (API)        • AngelList     (RSS) │   │
│  │ • We Work Remotely (RSS)        • WWR Advanced  (RSS) │   │
│  │ • Working Nomads   (RSS)        • JustRemote    (RSS) │   │
│  │ • Himalayas        (RSS)        • NoFluffJobs   (RSS) │   │
│  │ • Jobicy           (RSS)                              │   │
│  │ • Jobspresso       (RSS)                              │   │
│  │ • Greenhouse       (API)                              │   │
│  │ • LinkedIn         (API)                              │   │
│  │ • Arbeitnow        (API)                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Base Scraper (base.py) ──────────────────────────────────┐  │
│  │ • Rate limiting (1.5s default)                            │  │
│  │ • Retry logic (exponential backoff)                       │  │
│  │ • User agent rotation                                     │  │
│  │ • External ID generation                                 │  │
│  │ • Error handling                                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   FILTERING & DEDUPLICATION                      │
│                                                                  │
│  ┌─ RawJob Filtering (filters.py) ───────────────────────────┐  │
│  │ • passes_all_filters(job, criteria)                       │  │
│  │ • _matches_any(text, patterns)                            │  │
│  │ • ROLE_KEYWORDS (DevOps, SRE, etc.)                       │  │
│  │ • JUNIOR_KEYWORDS (entry-level filters)                  │  │
│  │ • SENIOR_EXCLUDE (senior position filters)               │  │
│  │ • REMOTE_POSITIVE / REMOTE_NEGATIVE (location)           │  │
│  │ • INDIAN_HQ_COMPANIES (company filtering)                │  │
│  │ • TECH_STACK_MAP (Extract tech: AWS, GCP, etc.)          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Deduplication by external_id (within batch)                   │
│                                                                  │
│  Deduplication by source (across scrapers)                      │  
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                            │
│                                                                  │
│  ┌─ Job Model ───────────────────────────────────────────────┐  │
│  │ • external_id (unique)                                    │  │
│  │ • title, company, url                                     │  │
│  │ • description, location, salary                           │  │
│  │ • tech_stack (extracted)                                  │  │
│  │ • company_size (inferred)                                 │  │
│  │ • experience_level (inferred)                             │  │
│  │ • region_eligibility (inferred)                           │  │
│  │ • is_applied, is_active (user state)                      │  │
│  │ • posted_at, scraped_at (timestamps)                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ ScrapeRun Model ─────────────────────────────────────────┐  │
│  │ • status (running/completed/failed)                       │  │
│  │ • started_at, completed_at                                │  │
│  │ • jobs_found, jobs_new                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  SQLite Database (./data/jobs.db)                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example: User Selects "DevOps Engineer (Junior)"

```
1. Frontend Initialization
   └─ useQuery("job-profiles") → GET /jobs/profiles/list
      └─ Returns: [JobProfile, JobProfile, ...]

2. User Interaction
   └─ Selects "devops-junior" from dropdown
      └─ Triggers setScrapeConfig({
         job_profile_id: "devops-junior",
         query: "DevOps Engineer (Junior)",
         min_experience: 0,
         max_experience: 2
      })

3. User Clicks "Run Scraper"
   └─ Sends POST /jobs/scrape with ScrapeRequest:
      {
        "query": "DevOps Engineer (Junior)",
        "job_profile_id": "devops-junior",
        "min_experience": 0,
        "max_experience": 2,
        "sources": ["remotive", "remoteok", ...],
        ...
      }

4. Backend Processing
   └─ run_scrape(request)
      └─ _criteria_from_request(request)
         └─ Detects job_profile_id
         └─ Fetches profile from job_profiles.py
         └─ Returns SearchCriteria with:
            - query: "DevOps Engineer (Junior)"
            - min_experience: 0
            - max_experience: 2
            - keywords from profile

5. Scraper Execution
   └─ run_all_scrapers(criteria, sources=selected_sources)
      └─ For each selected scraper:
         1. Scraper.scrape(criteria)
            - Hits job board API/RSS
            - Returns RawJob list
         2. Scraper.run(criteria)
            - Filters by SearchCriteria
            - Applies junior/senior/remote filters
            - Returns filtered RawJob list

6. Deduplication & Storage
   └─ Combine results from all scrapers
   └─ Deduplicate by external_id
   └─ raw_job_to_create() → extracts tech stack, company size, etc.
   └─ upsert_job() → stores in database

7. Response to Frontend
   └─ Returns: { "status": "completed", "jobs_found": 234, "jobs_new": 45 }

8. Frontend Updates
   └─ queryClient.invalidateQueries() 
   └─ Refetches /jobs, /stats
   └─ Updates dashboard with new results
```

---

## Job Profile Flow

```
Job Profiles In Memory
└─ job_profiles.py: JOB_PROFILES dict
   {
     "devops-junior": JobProfile(
       id="devops-junior",
       name="DevOps Engineer (Junior)",
       keywords=["devops", "sre", "site reliability", ...],
       min_experience=0,
       max_experience=2,
       role_category="DevOps/Infrastructure"
     ),
     "fullstack-mid": JobProfile(...),
     ...
   }

API Endpoints
├─ GET /jobs/profiles/list
│  └─ Returns: List[JobProfile]
│     Used for: Frontend dropdown population
│
├─ GET /jobs/profiles/{profile_id}
│  └─ Returns: JobProfile (single)
│     Used for: Detail view (optional future feature)
│
└─ GET /jobs/profiles/categories/list
   └─ Returns: {"categories": ["DevOps/Infrastructure", ...]}
      Used for: Category filtering (optional future feature)

Search Criteria Integration
└─ When job_profile_id is set:
   ├─ Fetch profile from get_profile_by_id()
   ├─ Extract experience range
   ├─ Use profile name as query
   └─ Apply profile keywords to filters

Backward Compatibility
└─ If job_profile_id is None:
   └─ Use manual query string
   └─ Works exactly as before
```

---

## Scraper Selection Architecture

```
User Interface
└─ Checkbox for each scraper
   ├─ Remotive ☑
   ├─ Remote OK ☑
   ├─ Stack Overflow ☑
   └─ ... (15 total)

Frontend State
└─ scrapeConfig.sources: string[]
   └─ ["remotive", "remoteok", "stackoverflow", ...]

API Request
└─ ScrapeRequest.sources: string[]
   └─ Passed to run_scrape()

Backend Processing
└─ run_scrape()
   └─ run_all_scrapers(criteria, source_names=request.sources)
      └─ get_all_scrapers(source_names)
         └─ For each source_name:
            └─ SCRAPER_REGISTRY.get(source_name)
            └─ Instantiate and append to list
      └─ Execute selected scrapers
      └─ Combine & deduplicate results

Database Storage
└─ All results stored with source field
└─ Enables filtering by source later
```

---

## Performance Optimization

```
Parallel Scraping
├─ Scrapers run concurrently (within rate limits)
├─ Each scraper respects 1.5s delay between requests
└─ Typical run time: 30-60 seconds for 15 scrapers

Deduplication Strategy
├─ Within scraper: Check seen external_id set
├─ Across scrapers: Check global seen_ids set
└─ Result: No duplicate jobs in database

Filtering Performance
├─ Apply filters during scraping (real-time)
├─ Reduce database insertions
├─ Pre-compute expensive operations (tech stack, company size)
└─ Result: Faster processing, smaller database

Caching
├─ Frontend: React Query caches profiles
├─ Frontend: React Query caches jobs & stats
└─ Backend: In-memory job profiles (no DB query)
```

---

## Error Handling

```
Scraper Level
├─ Retry with exponential backoff (up to 3 attempts)
├─ Log exceptions
├─ Return empty list on complete failure
└─ System continues with other scrapers

Filtering Level
├─ Safe regex pattern matching
├─ Handle missing/null fields gracefully
└─ Type checking on extractions

API Level
├─ Validate ScrapeRequest schema
├─ 404 for missing profiles
├─ 500 with error message for failures
└─ Consistent error format

Frontend Level
├─ Error boundaries
├─ Fallback UI states
└─ User-friendly error messages
```

---

**Architecture designed for**: Scalability, Maintainability, and User Experience
