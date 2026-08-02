# Job Aggregator — Backend API Engine

FastAPI-powered backend engine for the **Job Aggregator** application. It handles automated scraping across 10 Sri Lankan job platforms, data normalization, deduplication, Gemini AI relevance classification, and SQLite database persistence.

---

## Architecture & Features

- **FastAPI Core**: Async REST API serving job listings, scrape orchestration, keywords, locations, and settings.
- **10-Site Scraper Pipeline**: Dedicated scraper modules using `httpx`, `BeautifulSoup4`, `curl_cffi`, and `Playwright` — each site has a tailored adaptor.
- **Circuit Breaker & Pre-flight Probes**: Every scraper performs a 5-second connectivity check before entering its keyword loop. If a site is unreachable, the circuit breaker opens instantly and all remaining requests are skipped — no wasted time on down servers.
- **Split HTTP Timeouts**: Separate connect timeout (5s) for fast detection of unreachable hosts, and read timeout (15s) for slow-but-alive servers.
- **Deduplication Engine**: Matches job titles and company names to eliminate duplicate listings across platforms.
- **AI Relevance Classifier**: Uses Google Gemini 3.1 Flash Lite to automatically filter out non-software job postings based on target keywords.
- **Dual Data Persistence**:
  - **Web Development Mode**: Database saved at `backend/jobs.db`.
  - **Packaged Desktop Mode**: Database automatically mapped to `%APPDATA%\JobAggregator\jobs.db`.

---

## Scraper Adaptors

| Scraper Module     | Platform         | Method                     | Notes                                 |
| :----------------- | :--------------- | :------------------------- | :------------------------------------ |
| `itpro.py`         | itpro.lk         | HTML keyword search        | Paginated article cards               |
| `anyjobok.py`      | anyjobok.com     | HTML listing pages         | Multiple category entrypoints         |
| `governmentjob.py` | governmentjob.lk | Playwright + WP API + HTML | 3-tier fallback strategy              |
| `jobenvoy.py`      | jobenvoy.com     | HTML search                | Cloudflare-hosted, CDN-down detection |
| `rooster.py`       | rooster.jobs     | JSON API                   | `api.rooster.jobs` search endpoint    |
| `topjobs.py`       | topjobs.lk       | POST-based HTML            | Browser-like headers required         |
| `xpressjobs.py`    | xpress.jobs      | JSON API                   | `/api/jobs/searchJobs` endpoint       |
| `findmyjob.py`     | findmyjob.lk     | WordPress REST API         | `wp-json/wp/v2/awsm_job_openings`     |
| `hirelk.py`        | hire.lk          | HTML search + industry     | Keyword search + IT industry filter   |
| `jobseekerlk.py`   | jobseeker.lk     | HTML keyword search        | WordPress-based pagination            |

All scrapers inherit from `BaseScraper` which provides: HTTP client setup, robots.txt compliance, rate limiting, retry with exponential backoff, circuit breaker, and pre-flight connectivity probes.

---

## Quick Start & Setup

### Prerequisites

- Python 3.11+
- virtualenv

### 1. Environment Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
# source venv/bin/activate    # Linux / macOS

pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Copy `.env.example` to `.env` and set your credentials:

```ini
GEMINI_API_KEY=your_gemini_api_key_here
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Run Development Server

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Health Check**: `http://127.0.0.1:8000/health`
- **Swagger Documentation**: `http://127.0.0.1:8000/docs`

---

## API Endpoints Overview

| Method         | Endpoint                       | Description                                                      |
| :------------- | :----------------------------- | :--------------------------------------------------------------- |
| `GET`          | `/api/jobs`                    | Paginated job list with state, source, keyword & date filtering  |
| `PATCH`        | `/api/jobs/{id}/state`         | Update job state (`SAVED`, `APPLIED`, `INTERVIEWING`, `REMOVED`) |
| `POST`         | `/api/scrape/run`              | Trigger a manual scrape run across sources                       |
| `DELETE`       | `/api/scrape/runs/{id}/cancel` | Cancel a running scrape                                          |
| `GET`          | `/api/scrape/runs`             | Retrieve scrape audit log history                                |
| `GET`          | `/api/sources`                 | List configured scrapers and toggle status                       |
| `GET` / `POST` | `/api/settings`                | Retrieve or update Gemini API keys and settings                  |
| `GET` / `POST` | `/api/keywords`                | Manage role matching and negative exclude terms                  |
| `GET` / `POST` | `/api/locations`               | Manage target geographic locations                               |

---

## Configuration Reference

| Setting                      | Default | Description                                          |
| :--------------------------- | :------ | :--------------------------------------------------- |
| `CONNECT_TIMEOUT_SECONDS`    | `5.0`   | TCP handshake timeout — fast-fails unreachable hosts |
| `READ_TIMEOUT_SECONDS`       | `15.0`  | Data read timeout for slow servers                   |
| `DEFAULT_RATE_LIMIT_SECONDS` | `0.25`  | Minimum interval between requests to the same host   |
| `MAX_RETRIES`                | `3`     | Total retry attempts per request                     |
| `RETRY_BACKOFF_FACTOR`       | `1.0`   | Exponential backoff multiplier (1s, 2s, 4s …)        |
| `SCRAPER_MAX_PAGES`          | `2`     | Maximum pages fetched per keyword                    |
| `SCRAPER_PAGE_SIZE`          | `20`    | Results per page for paginated APIs                  |
| `DEDUP_WINDOW_DAYS`          | `45`    | Re-allow same posting hash after N days              |

---

## Integration with Sub-projects

- **[Frontend (Web App)](../frontend/README.md)**: Serves Next.js UI on port `3000` consuming this backend via REST API.
- **[Desktop App](../desktop/README.md)**: Bundles this FastAPI backend into PyWebview native desktop executable.
- **[Root Documentation](../README.md)**: Master architecture overview connecting all modules.
