# Job Aggregator

A personal job-search dashboard that pulls software engineering / web developer
/ SE intern listings from multiple Sri Lankan job sites, deduplicates postings
that appear on more than one site, and lets you track each job through a
pipeline (Discovered → Reviewing → Applied → Interviewing → Archived).

## Stack

| Layer     | Technology                       |
| --------- | -------------------------------- |
| Frontend  | Next.js (App Router) + Tailwind  |
| Backend   | Python + FastAPI                 |
| Database  | SQLite via SQLModel              |
| Scrapers  | httpx + BeautifulSoup4           |

## Quick Start

```bash
# 1. Backend
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env           # edit if needed
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local  # edit if needed
npm run dev
```

Open **http://localhost:3000** for the dashboard,
**http://localhost:3000/admin** for the admin portal.

## Sources

| Site             | Method          | Status |
| ---------------- | --------------- | ------ |
| itpro.lk         | REST API        | ✅      |
| anyjobok.com     | HTML scrape     | ✅      |
| governmentjob.lk | WP API / HTML   | ✅      |
| jobenvoy.com     | HTML scrape     | ✅      |
| rooster.jobs     | JSON search API | ✅      |

## Usage

1. Open `/admin`
2. Click **Start Fetching** (or trigger just one site)
3. Watch per-site progress until it completes
4. Switch to `/` — new postings land in the **Discovered** column
5. Triage: move jobs between columns as you review/apply

No cron or background scheduling — every fetch is started manually.