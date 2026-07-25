# Job Aggregator — Backend API Engine

FastAPI-powered backend engine for the **Job Aggregator** application. It handles automated scraping across Sri Lankan software job platforms, data normalization, deduplication, Gemini 1.5 Flash AI relevance classification, and SQLite database persistence.

---

## Architecture & Features

- **FastAPI Core**: Async REST API serving job listings, scrape orchestration, keywords, locations, and settings.
- **Scraper Pipeline**: Dedicated scraper modules using `httpx`, `BeautifulSoup4`, `curl_cffi`, and `Playwright` for dynamic sites (`rooster.jobs`, `topjobs.lk`, `itpro.lk`, etc.).
- **Deduplication Engine**: Matches job titles and company names to eliminate duplicate listings across platforms.
- **AI Relevance Classifier**: Uses Google Gemini 1.5 Flash to automatically filter out non-software job postings based on target keywords.
- **Dual Data Persistence**:
  - **Web Development Mode**: Database saved at `backend/jobs.db`.
  - **Packaged Desktop Mode**: Database automatically mapped to `%APPDATA%\JobAggregator\jobs.db`.

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
DEFAULT_RATE_LIMIT_SECONDS=1.0
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

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/jobs` | Paginated job list with state, source, keyword & date filtering |
| `PATCH` | `/api/jobs/{id}/state` | Update job state (`SAVED`, `APPLIED`, `INTERVIEWING`, `REMOVED`) |
| `POST` | `/api/scrape/run` | Trigger a manual scrape run across sources |
| `GET` | `/api/scrape/runs` | Retrieve scrape audit log history |
| `GET` | `/api/sources` | List configured scrapers and toggle status |
| `GET` / `POST` | `/api/settings` | Retrieve or update Gemini API keys and settings |
| `GET` / `POST` | `/api/keywords` | Manage role matching and negative exclude terms |
| `GET` / `POST` | `/api/locations` | Manage target geographic locations |

---

## Integration with Sub-projects

- **[Frontend (Web App)](../frontend/README.md)**: Serves Next.js UI on port `3000` consuming this backend via REST API.
- **[Desktop App](../desktop/README.md)**: Bundles this FastAPI backend into PyWebview native desktop executable.
- **[Root Documentation](../README.md)**: Master architecture overview connecting all modules.
