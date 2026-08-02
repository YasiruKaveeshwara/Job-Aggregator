# Job Aggregator — Sri Lanka Software Engineering Job Engine

> A full-stack, multi-source job aggregation, normalization, deduplication, and AI relevance classification engine built for Sri Lanka's software engineering job market.

[![Release](https://img.shields.io/badge/Release-v1.2.1-blue.svg?logo=github)](https://github.com/YasiruKaveeshwara/Job-Aggregator/releases/tag/v1.2.1)
[![Download Windows Installer](https://img.shields.io/badge/Download-Windows%20Setup%20.exe-0078D4?logo=windows&logoColor=white)](https://github.com/YasiruKaveeshwara/Job-Aggregator/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](backend/README.md)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](frontend/README.md)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)](backend/README.md)
[![PyWebview](https://img.shields.io/badge/PyWebview-5.4-purple)](desktop/README.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

### 📦 Quick Download & Installation (Windows Desktop App)

> **[📥 Download Latest Windows Setup (`JobAggregatorSetup.exe`)](https://github.com/YasiruKaveeshwara/Job-Aggregator/releases/latest)**
>
> 1. Download **`JobAggregatorSetup.exe`** from the [Latest Release Page](https://github.com/YasiruKaveeshwara/Job-Aggregator/releases/latest).
> 2. Run the installer and follow the 3-step setup wizard.
> 3. Launch **Job Aggregator** directly from your Desktop or Start Menu!

---

## Executive Overview

**Job Aggregator** simplifies job hunting for software engineers in Sri Lanka by consolidating listings from major platforms into a single unified workspace.

Instead of endlessly checking multiple websites, Job Aggregator provides:

- **Multi-Source Aggregation**: Automated scraping from 10 job platforms using specialized adaptors tailored per site structure.
- **Intelligent Deduplication**: Merges duplicate listings posted across multiple sites or re-advertised postings.
- **Role-Based Normalization & Filtering**: Cleans titles, extracts experience levels, and filters for relevant engineering roles.
- **Gemini AI Classifier**: Uses Google Gemini LLM to evaluate borderline postings and eliminate non-tech jobs.
- **Application Tracker**: Track application states (`SAVED`, `APPLIED`, `INTERVIEWING`, `REMOVED`) directly from the dashboard.
- **Dual Operating Modes**: Run as a standard **Web Application** (Next.js + FastAPI) or as a native **Windows Desktop Application** (`JobAggregatorSetup.exe`).
- **Circuit Breaker & Pre-flight Probes**: Automatic detection of unreachable sites with instant skip — no wasted time on down servers.

---

## Supported Job Platforms

| Platform                                     | Type                 | Scraper Method                      |
| :------------------------------------------- | :------------------- | :---------------------------------- |
| [itpro.lk](https://itpro.lk)                 | IT Jobs              | HTML keyword search                 |
| [anyjobok.com](https://anyjobok.com)         | General + IT Jobs    | HTML listing pages                  |
| [governmentjob.lk](https://governmentjob.lk) | Government Vacancies | Playwright + WP API + HTML fallback |
| [jobenvoy.com](https://jobenvoy.com)         | General Jobs         | HTML search with pagination         |
| [rooster.jobs](https://rooster.jobs)         | IT Jobs              | JSON API                            |
| [topjobs.lk](https://topjobs.lk)             | General + IT Jobs    | POST-based HTML search              |
| [xpress.jobs](https://xpress.jobs)           | General + IT Jobs    | JSON API                            |
| [findmyjob.lk](https://findmyjob.lk)         | IT Jobs              | WordPress REST API                  |
| [hire.lk](https://hire.lk)                   | IT Jobs              | HTML search + industry filter       |
| [jobseeker.lk](https://jobseeker.lk)         | General + IT Jobs    | HTML keyword search                 |

---

## Master Architecture & Sub-projects

Job Aggregator is architected into three interconnected sub-projects:

```mermaid
flowchart TD
    subgraph Desktop ["Desktop Distribution (PyWebview / PyInstaller)"]
        Installer["JobAggregatorSetup.exe / Setup Wizard"]
        NativeWindow["PyWebview Window Container"]
        Uninstaller["uninstall.exe / Uninstall Wizard"]
    end

    subgraph Frontend ["Frontend UI (Next.js 16 / React / TypeScript)"]
        Dashboard["Job Dashboard (/)"]
        AdminPortal["Admin Portal (/admin)"]
        ScrapeHUD["Live Fetch Operations HUD"]
        SettingsUI["Gemini Key & Keywords Manager"]
    end

    subgraph Backend ["Backend Engine (FastAPI / SQLModel / Python)"]
        API["FastAPI REST Endpoints"]
        Orchestrator["Scrape Orchestrator & Scraper Adaptors"]
        DedupEngine["Deduplication & Normalizer"]
        GeminiAI["Gemini AI Classifier"]
    end

    subgraph Storage ["Persistence Layer"]
        DB[("SQLite Database\n(jobs.db)")]
    end

    Installer -->|Extracts Payload| NativeWindow
    NativeWindow -->|Renders Static Export| Dashboard
    NativeWindow -->|Renders Static Export| AdminPortal
    Dashboard -->|REST API Requests| API
    AdminPortal -->|REST API Requests| API
    AdminPortal -->|Trigger Run| Orchestrator
    Orchestrator -->|Raw Postings| DedupEngine
    DedupEngine -->|Unique Postings| GeminiAI
    GeminiAI -->|Classified Jobs| DB
    API <-->|Read / Write| DB
    Uninstaller -->|Removes Reg / Files| Installer
```

---

## Repository Structure & Sub-project Documentation

Click into any sub-project below for in-depth technical documentation:

### 📁 [1. Backend Engine (`backend/ README.md`)](backend/README.md)

_Contains the FastAPI server, 10 scraper adaptors (`httpx`, `BeautifulSoup4`, `curl_cffi`, `Playwright`), database models (`jobs.db`), deduplication logic, circuit breaker resilience, and Gemini AI integration._

### 📁 [2. Frontend Web Application (`frontend/ README.md`)](frontend/README.md)

_Contains the Next.js 16 App Router interface, React components, dark glassmorphism styling, Kanban application state controls, real-time fetch HUD, and Gemini settings UI._

### 📁 [3. Desktop Distribution (`desktop/ README.md`)](desktop/README.md)

_Contains the PyWebview desktop wrapper, PyInstaller specs, LZMA payload compression, setup installer GUI (`installer_gui.py`), uninstaller GUI (`uninstaller_gui.py`), and binary packaging tools._

---

## Tech Stack Summary

| Layer                 | Technology                                   | Details                                                                         |
| :-------------------- | :------------------------------------------- | :------------------------------------------------------------------------------ |
| **Frontend UI**       | Next.js 16, React 19, TypeScript             | App Router, static export (`output: "export"`)                                  |
| **Styling**           | Vanilla CSS Tokens                           | Dark glassmorphic design system in `globals.css`                                |
| **Backend API**       | FastAPI, Uvicorn, SQLModel                   | Async REST endpoints, Pydantic data validation                                  |
| **Scrapers**          | HTTPX, BeautifulSoup4, curl_cffi, Playwright | 10 site adaptors, rate-limiting, retries, circuit breaker, pre-flight probes    |
| **AI Classification** | Google Gemini 3.1 Flash Lite                 | Structured JSON prompt classification for role relevance                        |
| **Database**          | SQLite                                       | Saved at `backend/jobs.db` (dev) or `%APPDATA%\JobAggregator\jobs.db` (desktop) |
| **Desktop Wrapper**   | PyWebview 5.4, PyInstaller                   | Native Windows GUI application with installer & uninstaller wizards             |

---

## Getting Started

### Mode A: Web Development Setup

#### 1. Backend Server

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

_Backend runs at `http://127.0.0.1:8000` (Swagger UI at `http://127.0.0.1:8000/docs`)._

#### 2. Frontend Web Server

```bash
cd frontend
npm install
npm run dev
```

_Dashboard served at `http://localhost:3000` (Admin Portal at `http://localhost:3000/admin`)._

---

### Mode B: Native Windows Desktop Setup

#### 1. Build Desktop Package from Source

```powershell
# Build frontend static export first
cd frontend
npm run build

# Build desktop package
cd ..\desktop
pip install -r requirements.txt

# Step 1: Build the main application payload
python -m PyInstaller -y build.spec

# Step 2: Compress payload with LZMA
python make_payload.py

# Step 3: Build the single setup installer
python -m PyInstaller -y installer_build.spec
```

#### 2. Install & Run

- Double-click **`desktop/dist/JobAggregatorSetup.exe`** to launch the 3-step installer GUI.
- Follow the setup wizard to create Desktop/Start Menu shortcuts and configure Developer Mode.
- Open **Job Aggregator** from your Desktop or Start Menu!

---

## Environment Configuration

When running in web dev mode, create a `backend/.env` file:

```ini
GEMINI_API_KEY=your_google_gemini_api_key
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

> 💡 **Desktop Note**: When using the desktop app, you do **not** need a `.env` file. Simply enter your Gemini API key inside the **Admin Portal → Application Settings** page; it is stored securely in your local `%APPDATA%\JobAggregator\jobs.db` database.

---

## License & Responsible Usage

Distributed under the MIT License. Scrape operations are designed for personal job monitoring and include configurable rate-limiting, circuit breakers, and user-agent settings. Please respect the terms of service of individual job platforms when running scrape pipelines.
