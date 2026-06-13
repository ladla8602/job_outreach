# Job Outreach

A personal job-search automation tool that scrapes **7 remote job boards in parallel**, discovers hiring contact emails, drafts tailored cold-outreach emails with GPT-4o-mini, and surfaces everything in a clean Flask web UI — where you review, edit, and send with one click.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat&logo=flask)
![OpenAI](https://img.shields.io/badge/GPT--4o--mini-OpenAI-412991?style=flat&logo=openai)
![Tests](https://img.shields.io/badge/tests-31%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## How it works

```
┌─────────────────────────────────────────────────────────┐
│                     pipeline.py                         │
│                                                         │
│  collect_jobs()          find_email()     compose()     │
│  ┌─────────────┐        ┌───────────┐   ┌───────────┐  │
│  │ RemoteOK    │──┐     │ 1. Parse  │   │ GPT-4o    │  │
│  │ Remotive    │  │     │    desc   │   │   mini    │  │
│  │ Arbeitnow   │  ├────▶│ 2. Scrape │──▶│           │  │
│  │ WeWorkRemo  │  │     │    page   │   │ tailored  │  │
│  │ HN Hiring   │  │     │ 3. DDG    │   │  draft    │  │
│  │ Jobicy      │  │     │    search │   └───────────┘  │
│  │ LinkedIn    │──┘     └───────────┘         │        │
│  └─────────────┘                              ▼        │
│  ThreadPoolExecutor                      jobs.json      │
│  (~1-2s wall-clock)                                     │
└──────────────────────────────┬──────────────────────────┘
                               │
                               ▼
                ┌──────────────────────────┐
                │        app.py (Flask)    │
                │                          │
                │  ┌────────────────────┐  │
                │  │   Job review card  │  │
                │  │  ┌──────────────┐  │  │
                │  │  │ AI draft     │  │  │
                │  │  │ (editable)   │  │  │
                │  │  └──────────────┘  │  │
                │  │  [Send] [Apply]    │  │
                │  │           [Skip]   │  │
                │  └────────────────────┘  │
                └──────────────────────────┘
```

---

## Features

- **7 job sources scraped in parallel** — RemoteOK, Remotive, Arbeitnow, We Work Remotely, Hacker News "Who is hiring?", Jobicy, LinkedIn public search
- **3-step email discovery** — extracts emails from job description → scrapes the apply page → falls back to DuckDuckGo search
- **AI-drafted cold outreach** — GPT-4o-mini writes a concise 3-sentence email matched to the job description and your tech profile
- **Smart deduplication** — `seen_jobs.json` ensures only genuinely new listings are processed on each run
- **Keyword filtering** — title-level and description-level filters keep only relevant software engineering roles; exclusions drop stacks outside your profile
- **Flask web UI** — review cards with editable draft, one-click send (attaches your PDF resume), skip button, live background refresh with status polling
- **Headless pipeline** — run `pipeline.py` from cron or CI without a browser
- **31 tests** — full pytest coverage across all modules

---

## Tech stack

| Layer | Tech |
|-------|------|
| Job scraping | `requests`, `BeautifulSoup4`, `xml.etree`, concurrent `ThreadPoolExecutor` |
| Email discovery | regex, BeautifulSoup4 page scrape, `ddgs` (DuckDuckGo) |
| AI composition | OpenAI `gpt-4o-mini` via `openai` SDK |
| Web UI | Flask, Jinja2, Tailwind CSS (CDN) |
| Config | `python-dotenv` |
| Tests | `pytest` |

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/your-username/job-outreach.git
cd job-outreach
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
RESUME_PATH=/absolute/path/to/your_resume.pdf
OPENAI_API_KEY=sk-...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=you@gmail.com
SMTP_PASS=xxxx-xxxx-xxxx-xxxx   # Gmail App Password (16 chars)
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App passwords → create one for "Mail".

### 4. Customize your profile

Open [composer.py](composer.py) and replace `_PROFILE` with your own experience, tech stack, and key metrics. This is what GPT-4o-mini uses to write your cold emails — specificity here directly improves output quality.

Also review the keyword lists in [job_finder.py](job_finder.py):

```python
_TECH_KEYWORDS   # stacks you work with — positive signal
_EXCLUDE_KEYWORDS # stacks you don't work with — exclusion filter
ROLE_KEYWORDS    # job titles that qualify
FREELANCE_ONLY   # set True to keep only contract/part-time roles
```

---

## Usage

### Web UI (recommended)

```bash
python app.py
# Open http://localhost:8000
```

On first run the job list will be empty. Click **Fetch Jobs** — the pipeline runs in the background (~30s) and the page auto-refreshes when done.

For each job card you can:
- **Edit** the AI-drafted email inline
- **Send** — delivers via SMTP with your resume attached
- **Apply** — opens the original listing in a new tab
- **Skip** — removes the card and marks it as seen

### Pipeline (headless / cron)

```bash
python pipeline.py
```

Fetches, enriches, and writes to `jobs.json`. Useful for scheduled runs without a browser open.

### Legacy digest emailer

```bash
python job_finder.py
```

Emails you an HTML digest of new jobs (no GPT drafts, no web UI). Good for cron-only setups.

---

## Running tests

```bash
pytest           # 31 tests
pytest -v        # with output
```

---

## Scheduling (run twice a day)

**GitHub Actions (recommended — free, nothing to keep running)**

Push to a private repo, then add these secrets under *Settings → Secrets → Actions*:

| Secret | Value |
|--------|-------|
| `OPENAI_API_KEY` | your OpenAI key |
| `SMTP_USER` | your Gmail address |
| `SMTP_PASS` | your Gmail App Password |
| `RESUME_PATH` | path on the runner (or skip for draft-only) |

The included [`.github/workflows/job-finder.yml`](.github/workflows/job-finder.yml) runs at 06:00 & 18:00 UTC — adjust the cron lines to your timezone.

**cron (local machine)**

```cron
0 9,21 * * * cd /path/to/job-outreach && venv/bin/python pipeline.py >> run.log 2>&1
```

---

## Project structure

```
job-outreach/
├── app.py            # Flask web UI + REST endpoints
├── pipeline.py       # Orchestrator: fetch → find email → compose → save
├── job_finder.py     # Job board scrapers + legacy digest emailer
├── email_finder.py   # 3-step hiring email discovery
├── composer.py       # GPT-4o-mini cold outreach composer
├── config.py         # Env var loading
├── templates/
│   └── index.html    # Tailwind job review UI
├── tests/            # pytest suite (31 tests)
├── .github/
│   └── workflows/
│       └── job-finder.yml   # GitHub Actions scheduled runner
├── .env.example
└── requirements.txt
```

---

## License

MIT
