# Job Aggregator

A personal job-search dashboard that pulls software engineering / web developer
/ SE intern listings from multiple Sri Lankan job sites, deduplicates postings
that appear on more than one site, and lets you track each job through a
pipeline (Discovered → Reviewing → Applied → Interviewing → Archived).

## Stack

| Layer    | Technology                      |
| -------- | ------------------------------- |
| Frontend | Next.js (App Router) + Tailwind |
| Backend  | Python + FastAPI                |
| Database | SQLite via SQLModel             |
| Scrapers | httpx + BeautifulSoup4          |

## Quick Start

```powershell
# 1. Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1    # PowerShell on Windows
pip install -r requirements.txt
copy ..\\.env.example .env     # edit if needed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
copy .env.local.example .env.local  # edit if needed
npm run dev
```

Open **http://localhost:3000** for the dashboard,
**http://localhost:3000/admin** for the admin portal.

## Backend Server

If you only want the API server, start it from the `backend` directory:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`, and the health check is
at `http://127.0.0.1:8000/health`.

## Sources

| Site             | Method          | Status |
| ---------------- | --------------- | ------ |
| itpro.lk         | REST API        | ✅     |
| anyjobok.com     | HTML scrape     | ✅     |
| governmentjob.lk | WP API / HTML   | ✅     |
| jobenvoy.com     | HTML scrape     | ✅     |
| rooster.jobs     | JSON search API | ✅     |

## Usage

1. Open `/admin`
2. Click **Start Fetching** (or trigger just one site)
3. Watch per-site progress until it completes
4. Switch to `/` — new postings land in the **Discovered** column
5. Triage: move jobs between columns as you review/apply

No cron or background scheduling — every fetch is started manually.
