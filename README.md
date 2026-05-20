# Remote Job Hunter

A production-ready personal job hunter for entry-level and junior remote roles that are global or India-eligible.

## What It Does

- Fetches jobs from Remotive, Remote OK, We Work Remotely RSS, Working Nomads RSS, Himalayas RSS, Jobicy RSS, Jobspresso RSS, public Greenhouse boards, and optional user-supplied LinkedIn search URLs.
- Runtime scrape form lets you choose job title/keywords, min/max years of experience, posted-within days, source list, LinkedIn search URLs, and strictness toggles.
- Filters can be strict for junior roles or relaxed for broader searches such as `DevOps Engineer`, `Senior DevOps Engineer`, `SRE`, or `Cloud Engineer`.
- Stores unique jobs in SQLite locally or PostgreSQL in production.
- Categorizes tech stack, company size, experience level, posted date, and region eligibility.
- Runs automatically every 4-6 hours via APScheduler.
- Sends Slack and email alerts for new matches.
- Provides a Next.js dashboard with filters, charts, apply links, mark-as-applied tracking, and cover letter templates.

## Project Structure

```text
remote-devops-hunter/
  backend/
    app/
      api/              FastAPI routers
      models/           SQLAlchemy models
      schemas/          Pydantic schemas
      services/         ingestion, stats, notifications
      tasks/            scheduler
      main.py           FastAPI app
    scrapers/           source adapters and smart filters
    scripts/            manual scraper runner
  frontend/
    app/                Next.js app router dashboard
    components/         dashboard components
    lib/                API client
    types/              shared frontend types
  docker-compose.yml
  .env.example
```

## Local Setup

```bash
cd /Users/apple/new/remote-devops-hunter
cp .env.example .env
```

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The API runs at `http://localhost:8000`, and docs are available at `http://localhost:8000/docs`.

## Run A Manual Scrape

```bash
cd backend
source .venv/bin/activate
python scripts/run_scraper.py
```

You can also configure and click **Run Scraper** in the dashboard or call:

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DevOps Engineer",
    "min_experience": 0,
    "max_experience": 2,
    "posted_within_days": 14,
    "remote_only": true,
    "global_or_india": true,
    "strict_experience": false,
    "strict_title": true,
    "strict_junior": false,
    "sources": ["remotive", "remoteok", "weworkremotely", "workingnomads", "himalayas", "jobicy", "jobspresso", "linkedin", "arbeitnow"],
    "linkedin_urls": []
  }'
```

For senior searches, set `"query": "Senior DevOps Engineer"` and a range such as `"min_experience": 5, "max_experience": 10`. For broad discovery, set `"strict_title": false` and `"strict_experience": false`.

## Docker Compose 

```bash 
cd /Users/apple/new/remote-devops-hunter
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, FastAPI, and the Next.js dashboard.

## Environment Variables

Important settings live in `.env`:

- `DATABASE_URL`: `sqlite:///./data/jobs.db` locally, or `postgresql+psycopg://...` in production.
- `SCRAPE_INTERVAL_HOURS`: defaults to `5`.
- `REQUEST_DELAY_SECONDS`: polite delay between source requests.
- `SLACK_WEBHOOK_URL`: optional Slack alerts.
- `SMTP_*` and `ALERT_EMAIL_TO`: optional email alerts.
- `GREENHOUSE_BOARD_TOKENS`: comma-separated Greenhouse boards to scan.
- `LINKEDIN_SEARCH_URLS`: optional comma-separated public LinkedIn job search URLs that you are allowed to fetch.
- `NEXT_PUBLIC_API_BASE_URL`: frontend API URL.

## Adding A New Source

1. Add a scraper class in `backend/scrapers/` that inherits `BaseScraper`.
2. Return a list of `RawJob` objects.
3. Register the class in `backend/scrapers/registry.py`.

The shared `passes_all_filters` logic handles niche filtering, remote eligibility, seniority exclusion, Indian-HQ exclusions, and categorization helpers.

## Deployment Notes

- Railway/Render: deploy `backend` and `frontend` as separate services, attach managed PostgreSQL, and set `DATABASE_URL`.
- VPS: use `docker compose up -d --build` behind Caddy, Nginx, or Traefik.
- Scheduler runs inside the backend process. For multi-replica production, run only one scheduler instance by setting `SCRAPE_ENABLED=false` on web replicas and running one worker replica with it enabled.

## Ethical Scraping

The app prefers APIs and RSS feeds. HTTP requests include delays, timeouts, retries, and rotating user agents. For sources without reliable public APIs, add adapters conservatively and respect each site’s terms and robots guidance.
