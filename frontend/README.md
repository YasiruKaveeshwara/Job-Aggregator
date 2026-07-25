# Job Aggregator — Frontend Web Application

Modern Next.js 16 frontend for **Job Aggregator**. Features a sleek, responsive dashboard for browsing Sri Lankan software engineering job listings, managing job application statuses, triggering live scraping pipelines, and configuring Gemini AI relevance settings.

---

## Tech Stack & Architecture

- **Framework**: Next.js 16 (App Router)
- **UI & Logic**: React 19, TypeScript
- **Design System**: Vanilla CSS tokens in `globals.css` with dark glassmorphism aesthetic, sleek gradients, and micro-animations.
- **Static Export**: Built with `output: "export"` (`trailingSlash: true`) generating static HTML/CSS/JS in `frontend/out` for bundling into the PyWebview desktop app.
- **Dual API Origin Resolution**: `getApiBaseUrl()` in `lib/api.ts` automatically routes requests to `http://localhost:8000` during Next.js web dev mode (port 3000/3001), and falls back to `window.location.origin` in PyWebview desktop mode.

---

## Page Routes & Core Components

### App Routes (`src/app/`)
- `/` - **Dashboard Page**: Search filters, role dropdowns, live stats HUD, job cards, and pagination.
- `/admin` - **Admin Portal**: Executive control center with sections for *Sources & Scrape Control*, *Gemini AI Credentials*, *Target Keywords*, *Locations*, and *Scrape Run History*.

### Components (`src/components/`)
- `Nav.tsx`: Glassmorphic top navigation bar with brand logo mark and active step pills.
- `JobCard.tsx`: Job listing card with company initials, platform badge, role tags, and application state dropdown.
- `FilterBar.tsx`: Search query, role selector, platform source chips, and date range inputs.
- `ScrapeControlPanel.tsx`: Live fetch operations HUD displaying real-time elapsed timer, estimated remaining duration, animated progress bar, site execution chips, and AI classification stats.
- `SettingsPanel.tsx`: Sleek Gemini API key card with status liveness pill, password mask view toggle, and Google AI Studio guide link.
- `KeywordEditor.tsx`: Target job title keyword management and negative exclusion terms.
- `SearchLocationEditor.tsx`: Target district geographic location preferences.
- `RunHistoryTable.tsx`: Detailed audit log table of past scrape executions.

---

## Quick Start & Setup

### Prerequisites
- Node.js 18+

### 1. Installation

```bash
cd frontend
npm install
```

### 2. Development Mode

```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser. (Ensure backend server is running on port 8000).

### 3. Production Static Build

```bash
npm run build
```
Generates production static export files in `frontend/out`, ready for deployment or desktop bundling.

---

## Integration with Sub-projects

- **[Backend Engine](../backend/README.md)**: FastAPI REST service powering job aggregation and LLM filtering.
- **[Desktop App](../desktop/README.md)**: PyWebview native container embedding the static frontend export.
- **[Root Documentation](../README.md)**: Master repository architecture overview.
